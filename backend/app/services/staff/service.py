# OWNER: P1
import csv
import io
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlmodel import Session, col, select

from app.core.clock import now
from app.engines.staff import PureStaffEngine
from app.models.events import EventSession
from app.models.ops import TravelTime
from app.models.participants import Contingent, Participant
from app.models.staff import Shift, Staff


def list_staff(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    role: Optional[str] = None,
    shift: Optional[str] = None,
    skill: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists staff members with workload summary and pagination."""
    query = select(Staff)
    if role:
        query = query.where(Staff.role == role)
    if shift:
        query = query.where(Staff.shift == shift)
    if q:
        query = query.where(
            (col(Staff.name).ilike(f"%{q}%")) | (col(Staff.id).ilike(f"%{q}%"))
        )

    all_staff = session.exec(query).all()
    if skill:
        skill_clean = skill.lower()
        all_staff = [
            s for s in all_staff
            if any(skill_clean in sk.lower() for sk in (s.skills or []))
        ]

    total = len(all_staff)
    start_idx = (page - 1) * page_size
    paged = all_staff[start_idx : start_idx + page_size]

    # Pre-fetch shifts to calculate scheduled hours today
    today_str = now().strftime("%Y-%m-%d")
    staff_ids = [s.id for s in paged]
    shifts = session.exec(select(Shift).where(col(Shift.staff_id).in_(staff_ids))).all() if staff_ids else []

    hours_map: Dict[str, float] = {}
    for sh in shifts:
        if sh.start_at and sh.end_at and sh.status != "CANCELLED":
            d_key = sh.start_at.strftime("%Y-%m-%d")
            if d_key == today_str:
                dur = (sh.end_at - sh.start_at).total_seconds() / 3600.0
                hours_map[sh.staff_id] = hours_map.get(sh.staff_id, 0.0) + dur

    items = []
    for s in paged:
        items.append({
            "id": s.id,
            "name": s.name,
            "role": s.role,
            "shift": s.shift,
            "phone": s.phone,
            "skills": s.skills or [],
            "status": s.status,
            "hours_scheduled_today": round(hours_map.get(s.id, 0.0), 1),
            "is_participant": s.is_participant,
            "contingent_id": s.contingent_id,
            "conflict_flags": [],
        })

    return {
        "staff": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_staff(session: Session, staff_id: str) -> Optional[Dict[str, Any]]:
    """Returns detailed staff profile, active assignments, and workload metrics."""
    staff = session.get(Staff, staff_id)
    if not staff:
        return None

    shifts = session.exec(
        select(Shift).where(Shift.staff_id == staff_id).order_by(Shift.start_at)
    ).all()

    total_hours = 0.0
    active_shifts = []
    for sh in shifts:
        if sh.start_at and sh.end_at and sh.status != "CANCELLED":
            dur = (sh.end_at - sh.start_at).total_seconds() / 3600.0
            total_hours += dur
        active_shifts.append({
            "id": sh.id,
            "session_id": sh.session_id,
            "venue_id": sh.venue_id,
            "role_required": sh.role_required,
            "start_at": sh.start_at.isoformat() if sh.start_at else None,
            "end_at": sh.end_at.isoformat() if sh.end_at else None,
            "status": sh.status,
            "handover_notes": sh.handover_notes,
        })

    is_overloaded = total_hours > 10.0
    return {
        "id": staff.id,
        "name": staff.name,
        "role": staff.role,
        "shift": staff.shift,
        "phone": staff.phone,
        "skills": staff.skills or [],
        "status": staff.status,
        "active_shifts": active_shifts,
        "workload": {
            "total_hours": round(total_hours, 1),
            "consecutive_hours": round(min(total_hours, 8.0), 1),
            "is_overloaded": is_overloaded,
        },
    }


def list_shifts(
    session: Session,
    staff_id: Optional[str] = None,
    session_id: Optional[str] = None,
    venue_id: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists shifts with filter options."""
    query = select(Shift)
    if staff_id:
        query = query.where(Shift.staff_id == staff_id)
    if session_id:
        query = query.where(Shift.session_id == session_id)
    if venue_id:
        query = query.where(Shift.venue_id == venue_id)
    if status:
        query = query.where(Shift.status == status)

    all_shifts = session.exec(query).all()
    if date:
        all_shifts = [
            s for s in all_shifts
            if s.start_at and s.start_at.strftime("%Y-%m-%d") == date
        ]

    # Pre-fetch staff names
    staff_map = {s.id: s.name for s in session.exec(select(Staff)).all()}

    shift_items = []
    for sh in all_shifts:
        shift_items.append({
            "id": sh.id,
            "staff_id": sh.staff_id,
            "staff_name": staff_map.get(sh.staff_id, sh.staff_id),
            "role_required": sh.role_required,
            "location": sh.location,
            "venue_id": sh.venue_id,
            "session_id": sh.session_id,
            "start_at": sh.start_at.isoformat() if sh.start_at else None,
            "end_at": sh.end_at.isoformat() if sh.end_at else None,
            "handover_notes": sh.handover_notes,
            "status": sh.status,
        })

    return {
        "shifts": shift_items,
        "total": len(shift_items),
    }


def get_demand_report(session: Session) -> Dict[str, Any]:
    """Calculates volunteer requirement demand over time vs staff on shift."""
    event_sessions = [
        s.model_dump() for s in session.exec(select(EventSession)).all()
    ]
    shifts = [
        s.model_dump() for s in session.exec(select(Shift)).all()
    ]
    return PureStaffEngine.calculate_demand_and_gaps(event_sessions, shifts)


def get_overloaded_report(session: Session) -> Dict[str, Any]:
    """Detects staff exceeding daily or consecutive hour limits."""
    shifts = session.exec(select(Shift)).all()
    staff_map = {s.id: s.name for s in session.exec(select(Staff)).all()}

    shift_dicts = []
    for sh in shifts:
        sd = sh.model_dump()
        sd["staff_name"] = staff_map.get(sh.staff_id, sh.staff_id)
        shift_dicts.append(sd)

    overloaded = PureStaffEngine.detect_overloaded_staff(shift_dicts)
    return {"overloaded_staff": overloaded}


def get_conflicts_report(session: Session) -> Dict[str, Any]:
    """Surfaces dual roles, self-escort conflicts, and shift overlaps."""
    staff_list = [s.model_dump() for s in session.exec(select(Staff)).all()]
    shifts = [s.model_dump() for s in session.exec(select(Shift)).all()]
    participants = [p.model_dump() for p in session.exec(select(Participant)).all()]
    contingents = [c.model_dump() for c in session.exec(select(Contingent)).all()]

    # Load travel matrix
    travel_times = session.exec(select(TravelTime)).all()
    travel_mat: Dict[Tuple[str, str], int] = {}
    for tt in travel_times:
        travel_mat[(tt.from_venue_id, tt.to_venue_id)] = tt.travel_time_min

    conflicts = PureStaffEngine.detect_conflicts(
        staff_list=staff_list,
        shifts=shifts,
        travel_matrix=travel_mat,
        participants=participants,
        contingents=contingents,
    )
    return {"conflicts": conflicts}


def suggest_replacements(
    session: Session,
    venue_id: str,
    start_at: str,
    end_at: str,
    role_required: Optional[str] = None,
    shift_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Suggests ranked replacement candidates for a shift window."""
    if shift_id:
        sh = session.get(Shift, shift_id)
        if sh:
            venue_id = venue_id or sh.venue_id or "V01"
            start_at = start_at or (sh.start_at.isoformat() if sh.start_at else "")
            end_at = end_at or (sh.end_at.isoformat() if sh.end_at else "")
            role_required = role_required or sh.role_required

    st_dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
    et_dt = datetime.fromisoformat(end_at.replace("Z", "+00:00"))

    staff_list = [s.model_dump() for s in session.exec(select(Staff)).all()]
    shifts = [s.model_dump() for s in session.exec(select(Shift)).all()]

    travel_times = session.exec(select(TravelTime)).all()
    travel_mat: Dict[Tuple[str, str], int] = {}
    for tt in travel_times:
        travel_mat[(tt.from_venue_id, tt.to_venue_id)] = tt.travel_time_min

    suggestions = PureStaffEngine.suggest_replacements(
        window_start=st_dt,
        window_end=et_dt,
        venue_id=venue_id,
        role_required=role_required,
        staff_list=staff_list,
        shifts=shifts,
        travel_matrix=travel_mat,
    )
    return {"suggestions": suggestions}


def generate_staff_coverage_csv(session: Session) -> str:
    """Exports CSV of hourly timeline demand and gaps."""
    demand = get_demand_report(session)
    timeline = demand.get("demand_timeline", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "time_window_start",
        "time_window_end",
        "volunteers_required",
        "staff_on_shift",
        "gap",
        "is_understaffed",
    ])
    for row in timeline:
        writer.writerow([
            row.get("time_window_start"),
            row.get("time_window_end"),
            row.get("volunteers_required"),
            row.get("staff_on_shift"),
            row.get("gap"),
            row.get("is_understaffed"),
        ])
    return output.getvalue()
