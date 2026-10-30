# OWNER: P1
"""Service layer for Contingents operational coordination and status views."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, func, select

from app.models.events import Event
from app.models.inventory import MerchClaim
from app.models.participants import Contingent, Participant, Registration


def list_contingents(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    q: Optional[str] = None,
    has_mismatch: Optional[bool] = None,
) -> Dict[str, Any]:
    """Lists all contingents with declared vs actual strength and leadership status."""
    query = select(Contingent)

    if q:
        q_term = f"%{q.strip().lower()}%"
        query = query.where(
            func.lower(Contingent.college).like(q_term)
            | func.lower(Contingent.name).like(q_term)
            | func.lower(Contingent.code).like(q_term)
        )

    contingents = session.exec(query.order_by(Contingent.code.asc())).all()

    # Pre-fetch participant counts and leaders/escorts per contingent
    act_counts_raw = session.exec(
        select(Participant.contingent_id, func.count(Participant.id))
        .where(Participant.status != "MERGED")
        .group_by(Participant.contingent_id)
    ).all()
    actual_map = {cid: cnt for cid, cnt in act_counts_raw if cid}

    # Pre-fetch participant names per contingent
    names_raw = session.exec(
        select(Participant.contingent_id, Participant.name)
        .where(Participant.status != "MERGED")
    ).all()
    names_by_cont: Dict[str, List[str]] = {}
    for cid, name in names_raw:
        if cid:
            names_by_cont.setdefault(cid, []).append(name.strip().lower() if name else "")

    items = []
    total_declared = 0
    total_actual = 0
    contingents_with_mismatch = 0

    for c in contingents:
        declared = c.strength_declared or 0
        actual = actual_map.get(c.id, 0)
        gap = actual - declared

        total_declared += declared
        total_actual += actual
        if gap != 0:
            contingents_with_mismatch += 1

        if has_mismatch is True and gap == 0:
            continue
        if has_mismatch is False and gap != 0:
            continue

        c_names = names_by_cont.get(c.id, [])
        l_name = (c.leader or "").strip().lower()
        e_name = (c.escort or "").strip().lower()
        leader_found = l_name in c_names if l_name else False
        escort_found = e_name in c_names if e_name else False

        items.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "college": c.college,
            "leader": c.leader,
            "escort": c.escort,
            "strength_declared": declared,
            "strength_actual": actual,
            "gap": gap,
            "leader_status": "FOUND" if leader_found else "MISSING",
            "escort_status": "FOUND" if escort_found else "MISSING",
            "preferences": c.preferences,
            "status": c.status,
        })

    # Pagination
    total = len(items)
    offset = (page - 1) * page_size
    paginated_items = items[offset: offset + page_size]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": paginated_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "meta": {
            "total_declared": total_declared,
            "total_actual": total_actual,
            "contingents_with_mismatch": contingents_with_mismatch,
        },
    }


def get_contingent(session: Session, contingent_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve basic profile details for a contingent."""
    c = session.get(Contingent, contingent_id)
    if not c:
        return None
    actual_count = session.exec(
        select(func.count(Participant.id)).where(
            Participant.contingent_id == c.id,
            Participant.status != "MERGED",
        )
    ).one()
    data = c.model_dump()
    data["strength_actual"] = actual_count
    return data


def get_contingent_status(session: Session, contingent_id: str) -> Optional[Dict[str, Any]]:
    """Returns the full 360-degree operational view of a contingent."""
    c = session.get(Contingent, contingent_id)
    if not c:
        return None

    participants = session.exec(
        select(Participant).where(
            Participant.contingent_id == c.id,
            Participant.status != "MERGED",
        )
    ).all()

    declared = c.strength_declared or 0
    actual = len(participants)
    gap = actual - declared

    # Leadership matching
    leader_match = None
    escort_match = None
    for p in participants:
        if c.leader and p.name.strip().lower() == c.leader.strip().lower():
            leader_match = p
        if c.escort and p.name.strip().lower() == c.escort.strip().lower():
            escort_match = p

    leadership = {
        "leader": {
            "name": c.leader,
            "participant_id": leader_match.id if leader_match else None,
            "status": "FOUND" if leader_match else "MISSING",
            "role": leader_match.role if leader_match else None,
            "attendance": leader_match.status if leader_match else None,
            "note": None if leader_match else "Leader missing from participant roster",
        },
        "escort": {
            "name": c.escort,
            "participant_id": escort_match.id if escort_match else None,
            "status": "FOUND" if escort_match else "MISSING",
            "role": escort_match.role if escort_match else None,
            "attendance": escort_match.status if escort_match else None,
            "note": None if escort_match else "Escort is declared in contingent master but missing from participant rosters",
        },
    }

    # Member attendance counts
    attendance: Dict[str, int] = {
        "EXPECTED": 0, "ARRIVED": 0, "CHECKED_IN": 0, "CHECKED_OUT": 0,
        "CANCELLED": 0, "NO_SHOW": 0, "WITHDRAWN": 0, "INVALID": 0, "MERGED": 0,
    }
    diet_counts: Dict[str, int] = {}
    tshirt_counts: Dict[str, int] = {}
    arrivals: List[datetime] = []
    departures: List[datetime] = []

    for p in participants:
        st = p.status
        attendance[st] = attendance.get(st, 0) + 1
        diet_counts[p.diet] = diet_counts.get(p.diet, 0) + 1
        sz = p.tshirt_size or "UNKNOWN"
        tshirt_counts[sz] = tshirt_counts.get(sz, 0) + 1
        if p.arrival_at:
            arrivals.append(p.arrival_at)
        if p.departure_at:
            departures.append(p.departure_at)

    earliest_arrival = min(arrivals).isoformat() if arrivals else None
    latest_departure = max(departures).isoformat() if departures else None

    # Arrival windows histogram
    arrival_windows = []
    if arrivals:
        window_counts: Dict[str, int] = {}
        for dt in arrivals:
            label = f"{dt.strftime('%Y-%m-%d')} {'Morning' if dt.hour < 12 else ('Afternoon' if dt.hour < 18 else 'Evening')}"
            window_counts[label] = window_counts.get(label, 0) + 1
        for win, cnt in sorted(window_counts.items()):
            arrival_windows.append({"window": win, "count": cnt})

    # Event participation
    p_ids = [p.id for p in participants]
    regs = session.exec(select(Registration).where(Registration.participant_id.in_(p_ids))).all() if p_ids else []
    event_counts: Dict[str, int] = {}
    for r in regs:
        event_counts[r.event_id] = event_counts.get(r.event_id, 0) + 1

    event_list = []
    for eid, cnt in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        ev = session.get(Event, eid)
        event_list.append({
            "event_id": eid,
            "name": ev.name if ev else eid,
            "participants_count": cnt,
        })

    # Merchandise
    claims_count = session.exec(
        select(func.count(MerchClaim.id)).where(MerchClaim.canonical_participant_id.in_(p_ids))
    ).one() if p_ids else 0

    merchandise_summary = {
        "eligible": actual,
        "claimed": claims_count,
        "pending": max(0, actual - claims_count),
        "size_breakdown": tshirt_counts,
    }

    # Group alerts
    alerts = []
    if gap != 0:
        alerts.append({
            "code": "STRENGTH_MISMATCH",
            "severity": 2,
            "message": f"Declared strength {declared} differs from actual rosters {actual} (gap: {gap:+d}).",
        })
    if not escort_match and c.escort:
        alerts.append({
            "code": "ESCORT_MISSING",
            "severity": 3,
            "message": f"Escort {c.escort} not found in participant roster.",
        })
    if not leader_match and c.leader:
        alerts.append({
            "code": "LEADER_MISSING",
            "severity": 3,
            "message": f"Leader {c.leader} not found in participant roster.",
        })

    # Housing fragmentation & leader proximity:
    # Safely query accommodation.public if available
    housing_fragmentation = {
        "status": "UNAVAILABLE",
        "properties_count": 0,
        "buildings_count": 0,
        "leader_proximity_meters": None,
        "warning": "Accommodation plan not yet live or accommodation.public unavailable",
    }
    try:
        from app.services.accommodation.public import get_contingent_housing  # type: ignore
        housing_data = get_contingent_housing(session, c.id)
        if housing_data:
            housing_fragmentation = housing_data
    except (ImportError, AttributeError):
        pass

    warnings = [a["message"] for a in alerts]

    return {
        "contingent_id": c.id,
        "code": c.code,
        "college": c.college,
        "strength": {
            "declared": declared,
            "actual": actual,
            "gap": gap,
            "status": "MATCH" if gap == 0 else ("DISCREPANCY_UNDER" if gap < 0 else "DISCREPANCY_OVER"),
        },
        "leadership": leadership,
        "attendance": attendance,
        "travel_coordination": {
            "earliest_arrival": earliest_arrival,
            "latest_departure": latest_departure,
            "arrival_windows": arrival_windows,
        },
        "event_participation": {
            "total_registrations": len(regs),
            "unique_events": len(event_counts),
            "events": event_list,
        },
        "dietary_summary": diet_counts,
        "merchandise_summary": merchandise_summary,
        "alerts": alerts,
        "housing_fragmentation": housing_fragmentation,
        "warnings": warnings,
    }
