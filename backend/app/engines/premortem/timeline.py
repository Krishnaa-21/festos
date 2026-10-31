# OWNER: P2
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session, func, select

from app.core.registry import iter_public_modules
from app.models.accommodation import ExternalProperty, Room, StayAssignment
from app.models.events import Event
from app.models.inventory import InventoryItem
from app.models.participants import Participant
from app.models.staff import Shift
from app.models.vendors import MealSlot, Vendor

logger = logging.getLogger("festos.premortem.timeline")

FESTIVAL_START = datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
FESTIVAL_END = datetime(2026, 11, 1, 22, 0, tzinfo=timezone.utc)


def compute_hourly_state(session: Session, current_hour: datetime) -> Dict[str, Any]:
    """Computes operational state and runs module risks across all domains for a single discrete hour."""
    curr_utc = current_hour if current_hour.tzinfo else current_hour.replace(tzinfo=timezone.utc)

    # 1. Accommodation
    rooms = session.exec(select(Room)).all()
    properties = session.exec(select(ExternalProperty)).all()
    on_campus_cap = sum(r.capacity for r in rooms if r.status in ["READY", "OCCUPIED", "AVAILABLE"])
    external_cap = sum(p.beds for p in properties if p.status == "ACTIVE")
    total_beds = on_campus_cap + external_cap

    # Participants staying during current_hour
    participants = session.exec(select(Participant).where(Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]))).all()
    occupied_count = 0
    for p in participants:
        arr = p.arrival_at if p.arrival_at else FESTIVAL_START
        dep = p.departure_at if p.departure_at else FESTIVAL_END
        arr_utc = arr if arr.tzinfo else arr.replace(tzinfo=timezone.utc)
        dep_utc = dep if dep.tzinfo else dep.replace(tzinfo=timezone.utc)
        if arr_utc <= curr_utc <= dep_utc:
            if str(p.accommodation_requested or "YES").upper() != "NO":
                occupied_count += 1

    # Cap occupied at total beds for rate calculation
    effective_occupied = min(total_beds, occupied_count)
    available_beds = max(0, total_beds - occupied_count)
    occ_rate = round((effective_occupied / max(1, total_beds)) * 100.0, 2)

    # 2. Food & Vendors
    vendors = session.exec(select(Vendor).where(Vendor.status == "ACTIVE")).all()
    total_vendor_capacity = sum(getattr(v, "capacity_per_meal", 200) for v in vendors)
    # Check if meal hour
    is_meal_time = (curr_utc.hour in [8, 9, 13, 14, 20, 21])
    active_vendors_count = len(vendors) if is_meal_time else max(1, len(vendors) // 3)
    food_demand = occupied_count if is_meal_time else int(occupied_count * 0.15)
    effective_vendor_cap = total_vendor_capacity if is_meal_time else int(total_vendor_capacity * 0.3)
    food_deficit = max(0, food_demand - effective_vendor_cap)

    # 3. Venues & Active Events
    from app.models.events import EventSession

    sessions = session.exec(select(EventSession).where(EventSession.status.in_(["SCHEDULED", "CONFIRMED", "ACTIVE", "IN_PROGRESS"]))).all()
    active_events = []
    congested_venues = set()
    if sessions:
        for ses in sessions:
            s_time = ses.start_at
            e_time = ses.end_at or (s_time + timedelta(hours=2) if s_time else None)
            if s_time:
                s_utc = s_time if s_time.tzinfo else s_time.replace(tzinfo=timezone.utc)
                e_utc = e_time if (e_time and e_time.tzinfo) else (e_time.replace(tzinfo=timezone.utc) if e_time else s_utc + timedelta(hours=2))
                if s_utc <= curr_utc <= e_utc:
                    active_events.append(ses)
                    if ses.venue_id:
                        congested_venues.add(ses.venue_id)
    else:
        events = session.exec(select(Event).where(Event.status.in_(["SCHEDULED", "CONFIRMED", "ACTIVE", "IN_PROGRESS"]))).all()
        for ev in events:
            s_time = getattr(ev, "start_at", None) or getattr(ev, "start_time", None)
            if s_time:
                s_utc = s_time if s_time.tzinfo else s_time.replace(tzinfo=timezone.utc)
                e_utc = s_utc + timedelta(hours=2)
                if s_utc <= curr_utc <= e_utc:
                    active_events.append(ev)
                    if ev.venue_id:
                        congested_venues.add(ev.venue_id)
            else:
                active_events.append(ev)
                if ev.venue_id:
                    congested_venues.add(ev.venue_id)

    venue_util_pct = round(min(100.0, (len(congested_venues) / max(1, 10)) * 100.0), 1)

    # 4. Equipment
    eq_items = session.exec(select(InventoryItem)).all()
    total_units_available = sum(getattr(item, "quantity", 10) for item in eq_items) if eq_items else 120
    units_demanded = len(active_events) * 6
    eq_shortage = max(0, units_demanded - total_units_available)

    # 5. Volunteers
    shifts = session.exec(select(Shift)).all()
    active_shifts = [s for s in shifts if getattr(s, "status", "SCHEDULED") in ["SCHEDULED", "CONFIRMED", "ACTIVE"]]
    volunteers_scheduled = len(active_shifts) if active_shifts else 25
    volunteers_required = len(active_events) * 4
    vol_gap = max(0, volunteers_required - volunteers_scheduled)

    # 6. Transport
    # Active shuttles based on arrival/departure peaks
    transit_ratio = 0.05 if (curr_utc.hour in [10, 11, 12, 17, 18, 19]) else 0.01
    passengers_en_route = int(occupied_count * transit_ratio)
    shuttles_in_transit = max(1, int(passengers_en_route / 25))

    # 7. Dynamic risks from all public modules
    critical_risks: List[Dict[str, Any]] = []
    max_severity = 1

    for mod_info in iter_public_modules():
        if not mod_info.get("has_risks"):
            continue
        try:
            mod_fn = getattr(mod_info["module"], "risks", None)
            if callable(mod_fn):
                # Call module risks(session, curr_utc) without changing module code
                mod_risks = mod_fn(session, curr_utc) or []
                for r in mod_risks:
                    sev = getattr(r, "severity", 1)
                    if sev > max_severity:
                        max_severity = sev
                    if sev >= 2:
                        critical_risks.append({
                            "module": mod_info["slug"],
                            "code": getattr(r, "code", "RISK"),
                            "severity": sev,
                            "people_affected": getattr(r, "people_affected", 0),
                            "description": getattr(r, "description", ""),
                        })
        except Exception as e:
            logger.debug(f"Error querying risks from {mod_info.get('slug')}: {e}")

    # Synthesize domain stress risks if deficits exist
    if occ_rate >= 90.0:
        critical_risks.append({
            "module": "accommodation",
            "code": "ACC_HIGH_UTILIZATION",
            "severity": 3 if occ_rate < 95.0 else 4,
            "people_affected": occupied_count,
            "description": f"Bed capacity critically stressed at {occ_rate}% occupancy.",
        })
        if 4 > max_severity:
            max_severity = 4

    if food_deficit > 0:
        critical_risks.append({
            "module": "food",
            "code": "FOOD_DEFICIT",
            "severity": 3,
            "people_affected": food_deficit,
            "description": f"Catering shortfall of {food_deficit} meals during meal window.",
        })
        if 3 > max_severity:
            max_severity = 3

    return {
        "timestamp": curr_utc.isoformat(),
        "accommodation": {
            "total_beds": total_beds,
            "occupied_beds": occupied_count,
            "available_beds": available_beds,
            "occupancy_rate_pct": occ_rate,
        },
        "food": {
            "total_demand": food_demand,
            "vendor_capacity": effective_vendor_cap,
            "coverage_deficit": food_deficit,
            "active_vendors": active_vendors_count,
        },
        "venues": {
            "active_events": len(active_events),
            "peak_venue_utilization_pct": venue_util_pct,
            "congested_venues": list(congested_venues)[:5],
        },
        "equipment": {
            "units_demanded": units_demanded,
            "units_available": total_units_available,
            "shortage": eq_shortage,
        },
        "volunteers": {
            "volunteers_required": volunteers_required,
            "volunteers_scheduled": volunteers_scheduled,
            "coverage_gap": vol_gap,
        },
        "transport": {
            "shuttles_in_transit": shuttles_in_transit,
            "passengers_en_route": passengers_en_route,
            "active_routes": min(4, shuttles_in_transit),
        },
        "critical_risks": critical_risks[:8],
        "hourly_risk_count": len(critical_risks),
        "max_severity": max_severity,
    }


def generate_hourly_timeline(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    step_hours: int = 1,
) -> Dict[str, Any]:
    """Generates a scrubbable hourly operational timeline over the festival window."""
    start = start_time or FESTIVAL_START
    end = end_time or FESTIVAL_END
    step = max(1, step_hours)

    curr = start
    timeline_intervals = []
    peak_stress_hour = start.isoformat()
    peak_stress_score = -1

    while curr <= end:
        hourly_data = compute_hourly_state(session, curr)
        timeline_intervals.append(hourly_data)

        # Calculate composite hourly stress
        stress_score = (
            hourly_data["max_severity"] * 10
            + hourly_data["hourly_risk_count"] * 2
            + (hourly_data["accommodation"]["occupancy_rate_pct"] * 0.1)
        )
        if stress_score > peak_stress_score:
            peak_stress_score = stress_score
            peak_stress_hour = hourly_data["timestamp"]

        curr += timedelta(hours=step)

    return {
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "total_hours": len(timeline_intervals),
        "timeline": timeline_intervals,
        "peak_stress_hour": peak_stress_hour,
        "meta": {
            "simulated_window": "FESTIVAL_HORIZON",
            "step_hours": step,
            "risk_modules_queried": len(iter_public_modules()),
        },
    }
