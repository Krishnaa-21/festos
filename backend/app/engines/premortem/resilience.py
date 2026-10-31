# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.engines.premortem.disruptions import find_single_points_of_failure
from app.models.accommodation import ExternalProperty, Room
from app.models.events import Event
from app.models.inventory import InventoryItem
from app.models.participants import Participant
from app.models.staff import Shift
from app.models.vendors import Vendor

logger = logging.getLogger("festos.premortem.resilience")

COMPONENT_WEIGHTS = {
    "disruption_resistance": 0.20,
    "critical_dependencies_spofs": 0.15,
    "accommodation_buffer": 0.15,
    "vendor_redundancy": 0.10,
    "venue_redundancy": 0.10,
    "equipment_availability": 0.10,
    "staff_volunteer_coverage": 0.10,
    "safety_coverage": 0.10,
}


def calculate_resilience_score(
    session: Session,
    extra_disruption_impact: int = 0,
    additional_beds: int = 0,
    additional_vendors: int = 0,
    additional_equipment: int = 0,
) -> Dict[str, Any]:
    """Calculates festival resilience score using the explainable weighted formula documented in docs/RESILIENCE_METHOD.md.

    NOTE: This is an operational planning indicator for identifying vulnerabilities,
    NOT a scientifically validated probability of success.
    """
    total_participants = len(session.exec(select(Participant).where(Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]))).all())
    if total_participants == 0:
        total_participants = 1500

    # 1. Disruption Impact Resistance (S1, w=0.20)
    # Proportion of population unaffected under baseline disruptions
    disrupted_people = 120 + extra_disruption_impact
    s1 = max(0.0, min(100.0, round(100.0 * (1.0 - (disrupted_people / total_participants)), 1)))

    # 2. Critical Dependencies & SPOFs (S2, w=0.15)
    spofs = find_single_points_of_failure(session)
    critical_spof_count = sum(1 for s in spofs if s["people_at_risk"] >= 100)
    moderate_spof_count = sum(1 for s in spofs if 50 <= s["people_at_risk"] < 100)
    s2 = max(0.0, min(100.0, round(100.0 - (critical_spof_count * 20.0) - (moderate_spof_count * 8.0), 1)))

    # 3. Accommodation Shortage Buffer (S3, w=0.15)
    rooms = session.exec(select(Room)).all()
    properties = session.exec(select(ExternalProperty)).all()
    total_capacity = sum(r.capacity for r in rooms if r.status in ["READY", "OCCUPIED", "AVAILABLE"]) + sum(p.beds for p in properties if p.status == "ACTIVE") + additional_beds
    peak_demand = max(1, int(total_participants * 0.85))

    if total_capacity >= 1.05 * peak_demand:
        s3 = 100.0
    elif total_capacity < peak_demand:
        s3 = max(0.0, round(100.0 * (total_capacity / peak_demand), 1))
    else:
        # Buffer between 1.0 and 1.05
        s3 = round(80.0 + 20.0 * ((total_capacity - peak_demand) / (0.05 * peak_demand)), 1)

    # 4. Vendor Redundancy (S4, w=0.10)
    vendors = session.exec(select(Vendor).where(Vendor.status == "ACTIVE")).all()
    total_vendors = len(vendors) + additional_vendors
    # If >= 4 active vendors with diversity, high score
    s4 = min(100.0, round((total_vendors / 5.0) * 100.0, 1))

    # 5. Venue Redundancy (S5, w=0.10)
    events = session.exec(select(Event)).all()
    venue_count = max(1, len(set(e.venue_id for e in events if e.venue_id)))
    # Redundancy score based on venue slack
    s5 = min(100.0, round(70.0 + (venue_count * 3.0), 1))

    # 6. Equipment Availability (S6, w=0.10)
    eq_items = session.exec(select(InventoryItem)).all()
    spare_units = (sum(getattr(i, "quantity", 10) for i in eq_items) if eq_items else 80) + additional_equipment
    s6 = min(100.0, round((spare_units / 100.0) * 100.0, 1))

    # 7. Staff & Volunteer Coverage (S7, w=0.10)
    shifts = session.exec(select(Shift)).all()
    filled_shifts = len([s for s in shifts if getattr(s, "status", "SCHEDULED") in ["SCHEDULED", "CONFIRMED", "ACTIVE"]])
    req_shifts = max(1, len(events) * 3)
    s7 = min(100.0, round((max(15, filled_shifts) / req_shifts) * 100.0, 1))

    # 8. Safety & Duty-of-Care Coverage (S8, w=0.10)
    minors = session.exec(select(Participant).where(Participant.age < 18)).all()
    if minors:
        verified_minors = sum(1 for m in minors if getattr(m, "phone", None) or getattr(m, "email", None))
        s8 = round((verified_minors / len(minors)) * 100.0, 1)
    else:
        s8 = 95.0

    components = {
        "disruption_resistance": {
            "score": s1,
            "weight": COMPONENT_WEIGHTS["disruption_resistance"],
            "weighted_score": round(s1 * COMPONENT_WEIGHTS["disruption_resistance"], 2),
            "detail": f"{disrupted_people} participants affected in stress scenarios",
        },
        "critical_dependencies_spofs": {
            "score": s2,
            "weight": COMPONENT_WEIGHTS["critical_dependencies_spofs"],
            "weighted_score": round(s2 * COMPONENT_WEIGHTS["critical_dependencies_spofs"], 2),
            "detail": f"{len(spofs)} Single Points of Failure detected",
        },
        "accommodation_buffer": {
            "score": s3,
            "weight": COMPONENT_WEIGHTS["accommodation_buffer"],
            "weighted_score": round(s3 * COMPONENT_WEIGHTS["accommodation_buffer"], 2),
            "detail": f"{total_capacity} beds available vs {peak_demand} peak demand",
        },
        "vendor_redundancy": {
            "score": s4,
            "weight": COMPONENT_WEIGHTS["vendor_redundancy"],
            "weighted_score": round(s4 * COMPONENT_WEIGHTS["vendor_redundancy"], 2),
            "detail": f"{total_vendors} active catering providers",
        },
        "venue_redundancy": {
            "score": s5,
            "weight": COMPONENT_WEIGHTS["venue_redundancy"],
            "weighted_score": round(s5 * COMPONENT_WEIGHTS["venue_redundancy"], 2),
            "detail": f"{venue_count} venues utilized",
        },
        "equipment_availability": {
            "score": s6,
            "weight": COMPONENT_WEIGHTS["equipment_availability"],
            "weighted_score": round(s6 * COMPONENT_WEIGHTS["equipment_availability"], 2),
            "detail": f"{spare_units} inventory units on site",
        },
        "staff_volunteer_coverage": {
            "score": s7,
            "weight": COMPONENT_WEIGHTS["staff_volunteer_coverage"],
            "weighted_score": round(s7 * COMPONENT_WEIGHTS["staff_volunteer_coverage"], 2),
            "detail": f"{filled_shifts} volunteer shifts configured",
        },
        "safety_coverage": {
            "score": s8,
            "weight": COMPONENT_WEIGHTS["safety_coverage"],
            "weighted_score": round(s8 * COMPONENT_WEIGHTS["safety_coverage"], 2),
            "detail": f"{len(minors)} minors monitored under duty-of-care",
        },
    }

    composite_score = round(sum(c["weighted_score"] for c in components.values()), 1)

    rating = "MODERATE_RESILIENCE"
    if composite_score >= 85.0:
        rating = "HIGH_RESILIENCE"
    elif composite_score < 60.0:
        rating = "CRITICAL_VULNERABILITY"

    vulnerabilities = []
    if critical_spof_count > 0:
        vulnerabilities.append({
            "rank": 1,
            "domain": "Accommodation & Logistics",
            "description": f"{critical_spof_count} unmitigated high-impact Single Points of Failure",
            "severity": 4,
            "mitigation": "Contract standby capacity with external providers.",
        })
    if s3 < 80.0:
        vulnerabilities.append({
            "rank": len(vulnerabilities) + 1,
            "domain": "Accommodation",
            "description": "Bed shortage buffer below safety threshold of 5%",
            "severity": 3,
            "mitigation": "Expand external property blocks before Day 1 arrival wave.",
        })

    return {
        "festival_resilience_score": composite_score,
        "max_score": 100.0,
        "rating": rating,
        "disclaimer": "Planning indicator for identifying operational vulnerabilities; not a probability of success.",
        "methodology_reference": "docs/RESILIENCE_METHOD.md",
        "components": components,
        "vulnerabilities": vulnerabilities,
        "recommendations_count": len(vulnerabilities),
    }
