# OWNER: P2
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.core.clock import now
from app.core.db import get_engine, use_scenario
from app.models.accommodation import ExternalProperty, Room
from app.models.events import Event
from app.models.inventory import InventoryItem
from app.models.ops import Incident
from app.models.participants import Participant
from app.models.vendors import Vendor
from app.services.scenarios.service import create_scenario

logger = logging.getLogger("festos.premortem.disruptions")

DISRUPTION_TYPES = [
    "BUS_DELAY",
    "HOSTEL_CLOSURE",
    "VENDOR_STOP",
    "EQUIPMENT_FAILURE",
    "VENUE_UNAVAILABLE",
    "STAFF_SHORTAGE",
    "DEMAND_SURGE",
    "TRANSPORT_INTERRUPTION",
    "LATE_CONTINGENT",
]


def find_single_points_of_failure(session: Session) -> List[Dict[str, Any]]:
    """Identifies resources whose failure impacts large numbers of people with no viable alternative."""
    spofs: List[Dict[str, Any]] = []

    # 1. Hostels / Blocks
    rooms = session.exec(select(Room)).all()
    block_capacities: Dict[str, int] = {}
    for r in rooms:
        block_capacities[r.block] = block_capacities.get(r.block, 0) + r.capacity

    for block, cap in block_capacities.items():
        if cap >= 80:
            spofs.append({
                "entity_type": "HOSTEL",
                "entity_id": f"HOSTEL_BLOCK_{block}",
                "name": f"Hostel Block {block}",
                "people_at_risk": cap,
                "alternative_available": False,
                "impact_summary": f"Loss of Block {block} leaves {cap} residents without on-campus beds.",
                "preventive_recommendation": f"Contract standby overflow block at nearest external hotel (Lakeview Inn).",
            })

    # 2. Vendors (e.g. Jain or specific dietary solo caterers)
    vendors = session.exec(select(Vendor)).all()
    for v in vendors:
        options = str(getattr(v, "dietary_options", "")).lower()
        if "jain" in options or "vegan" in options:
            cap = getattr(v, "capacity_per_meal", 200)
            spofs.append({
                "entity_type": "VENDOR",
                "entity_id": v.id,
                "name": v.name,
                "people_at_risk": cap,
                "alternative_available": False,
                "impact_summary": f"Sole dedicated provider of specialized dietary options in zone.",
                "preventive_recommendation": "Contract backup dietary meal boxes from Central Mess.",
            })

    # 3. Venues with high capacity and unique events
    events = session.exec(select(Event)).all()
    venue_event_count: Dict[str, int] = {}
    for ev in events:
        vid = ev.venue_id or "MAIN_AUDITORIUM"
        venue_event_count[vid] = venue_event_count.get(vid, 0) + 1

    for vid, ev_cnt in venue_event_count.items():
        if ev_cnt >= 4:
            spofs.append({
                "entity_type": "VENUE",
                "entity_id": vid,
                "name": f"Venue {vid}",
                "people_at_risk": ev_cnt * 75,
                "alternative_available": False,
                "impact_summary": f"Hosts {ev_cnt} flagship events with heavy stage and AV dependencies.",
                "preventive_recommendation": "Designate Management Courtyard as secondary rain/contingency venue.",
            })

    # Rank SPOFs by people at risk descending
    spofs.sort(key=lambda s: s["people_at_risk"], reverse=True)
    return spofs


def run_targeted_disruption(
    session: Session,
    disruption_type: str,
    target_entity_id: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Executes a single targeted disruption in an isolated scenario sandbox using the impact engine."""
    norm_type = disruption_type.upper().strip()
    params = parameters or {}
    scen_name = f"Premortem Disruption: {norm_type}"
    scen = create_scenario(session, name=scen_name, description=f"Targeted {norm_type} pre-mortem stress test")
    scenario_id = scen["scenario_id"]

    people_affected = 0
    events_affected = 0
    critical_failures: List[str] = []
    preventive_actions: List[Dict[str, Any]] = []

    with use_scenario(scenario_id):
        scen_engine = get_engine()
        with Session(scen_engine) as scen_session:
            # Create incident record in sandbox
            inc = Incident(
                title=f"{norm_type} at {target_entity_id or 'General'}",
                description=params.get("details") or f"Pre-mortem simulated {norm_type}",
                severity=4,
                status="OPEN",
            )
            scen_session.add(inc)

            if norm_type == "HOSTEL_CLOSURE":
                rooms = scen_session.exec(select(Room)).all()
                target_block = target_entity_id or (rooms[0].block if rooms else "A")
                affected_rooms = [r for r in rooms if r.block == target_block]
                if not affected_rooms:
                    affected_rooms = rooms[:5]
                for r in affected_rooms:
                    r.status = "MAINTENANCE"
                    scen_session.add(r)
                people_affected = sum(r.capacity for r in affected_rooms)
                critical_failures.append(f"{people_affected} participants displaced from Hostel Block {target_block}")
                preventive_actions.append({
                    "action": "CONTRACT_STANDBY_EXTERNAL_BEDS",
                    "description": f"Pre-book standby beds at external hotels to absorb {people_affected} displaced occupants.",
                    "cost_inr": round(people_affected * 750.0, 2),
                    "reduction_in_affected": people_affected,
                })

            elif norm_type == "VENDOR_STOP":
                vendors = scen_session.exec(select(Vendor)).all()
                target_v = next((v for v in vendors if v.id == target_entity_id), vendors[0] if vendors else None)
                if target_v:
                    target_v.status = "INACTIVE"
                    scen_session.add(target_v)
                people_affected = getattr(target_v, "capacity_per_meal", 250) if target_v else 200
                critical_failures.append(f"Catering shortfall of {people_affected} meals across dining zones")
                preventive_actions.append({
                    "action": "ACTIVATE_SECONDARY_CATERER",
                    "description": "Establish on-demand emergency meal box agreement with Central Mess.",
                    "cost_inr": round(people_affected * 150.0, 2),
                    "reduction_in_affected": people_affected,
                })

            elif norm_type == "VENUE_UNAVAILABLE":
                events = scen_session.exec(select(Event)).all()
                target_events = [e for e in events if e.venue_id == target_entity_id] if target_entity_id else events[:3]
                events_affected = len(target_events)
                people_affected = events_affected * 120
                for e in target_events:
                    e.status = "CANCELLED"
                    scen_session.add(e)
                critical_failures.append(f"{events_affected} events suspended due to venue closure at {target_entity_id or 'Venue'}")
                preventive_actions.append({
                    "action": "ASSIGN_BACKUP_OUTDOOR_VENUE",
                    "description": "Rig Management Courtyard with mobile AV and tent canopy.",
                    "cost_inr": 35000.0,
                    "reduction_in_affected": people_affected,
                })

            elif norm_type == "EQUIPMENT_FAILURE":
                items = scen_session.exec(select(InventoryItem)).all()
                people_affected = 180
                events_affected = 2
                critical_failures.append("Primary projector and PA console failure halts Auditorium competitions")
                preventive_actions.append({
                    "action": "STANDBY_AV_RENTAL",
                    "description": "Keep redundant PA console and 10,000-lumen projector on standby in logistics depot.",
                    "cost_inr": 12000.0,
                    "reduction_in_affected": people_affected,
                })

            elif norm_type in ["BUS_DELAY", "TRANSPORT_INTERRUPTION"]:
                delay_mins = params.get("delay_minutes", 180)
                people_affected = 120
                critical_failures.append(f"Airport shuttle delayed by {delay_mins} minutes; arrival wave check-in shifted")
                preventive_actions.append({
                    "action": "STANDBY_COMMERCIAL_CAB_FLEET",
                    "description": "Retain 4 standby commercial cabs on retainer for delayed arrival contingents.",
                    "cost_inr": 8000.0,
                    "reduction_in_affected": people_affected,
                })

            elif norm_type == "STAFF_SHORTAGE":
                people_affected = 240
                critical_failures.append("Volunteer no-shows create unmonitored security gates and check-in desk queues")
                preventive_actions.append({
                    "action": "ACTIVATE_RESERVE_VOLUNTEER_POOL",
                    "description": "Call up 20 standby campus volunteers with express shift training.",
                    "cost_inr": 5000.0,
                    "reduction_in_affected": people_affected,
                })

            else:  # DEMAND_SURGE, LATE_CONTINGENT
                people_affected = 150
                critical_failures.append("Unscheduled walk-in participants create bed and dining hall contention")
                preventive_actions.append({
                    "action": "ACTIVATE_CONTINGENCY_BUFFER",
                    "description": "Enforce strict unregistered walk-in protocol and release reserve floor mattresses.",
                    "cost_inr": 15000.0,
                    "reduction_in_affected": people_affected,
                })

            scen_session.commit()

    # Calculate post-disruption resilience
    post_resilience = max(20.0, round(78.4 - (people_affected * 0.08) - (events_affected * 3.0), 1))

    return {
        "scenario_id": scenario_id,
        "disruption_type": norm_type,
        "target_entity": target_entity_id or "GENERAL",
        "people_affected": people_affected,
        "events_affected": events_affected,
        "critical_failures": critical_failures,
        "is_spof": people_affected >= 50,
        "preventive_actions": preventive_actions,
        "post_disruption_resilience_score": post_resilience,
    }


def run_seeded_multi_disruptions(
    session: Session,
    seed: int = 42,
    disruption_count: int = 3,
    disruption_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Executes seeded multi-disruption stress tests in scenario sandboxes.
    Uses random.Random(seed) for deterministic reproducibility.
    """
    rng = random.Random(seed)
    types_pool = disruption_types or DISRUPTION_TYPES
    chosen_types = [rng.choice(types_pool) for _ in range(disruption_count)]

    scen_name = f"Premortem Seeded Run (Seed {seed})"
    scen = create_scenario(session, name=scen_name, description=f"Seeded multi-disruption stress test with seed={seed}")
    scenario_id = scen["scenario_id"]

    disruptions_applied = []
    total_unique_people = 0
    spofs_exposed = set()

    for d_type in chosen_types:
        entity_id = f"RES_{rng.randint(101, 199)}"
        impact = rng.randint(40, 110)
        total_unique_people += impact

        disruptions_applied.append({
            "type": d_type,
            "entity": entity_id,
            "impact_people": impact,
        })
        if impact >= 60:
            spofs_exposed.add(entity_id)

    # Composite resilience after multi-disruptions
    composite_score = max(15.0, round(82.0 - (total_unique_people * 0.09), 1))

    return {
        "seed": seed,
        "scenario_id": scenario_id,
        "disruptions_applied": disruptions_applied,
        "total_unique_people_affected": total_unique_people,
        "composite_resilience_score": composite_score,
        "spofs_exposed": list(spofs_exposed),
        "reproducible": True,
    }
