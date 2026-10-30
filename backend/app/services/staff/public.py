# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.engines.staff import PureStaffEngine
from app.models.events import EventSession
from app.models.staff import Shift, Staff
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity
from app.services.staff.service import generate_staff_coverage_csv


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Returns module KPI summary as of `now`."""
    total_staff = len(session.exec(select(Staff)).all())
    active_shifts = len(session.exec(select(Shift).where(Shift.status != "CANCELLED")).all())

    event_sessions = [s.model_dump() for s in session.exec(select(EventSession)).all()]
    shifts = [s.model_dump() for s in session.exec(select(Shift)).all()]
    demand_rep = PureStaffEngine.calculate_demand_and_gaps(event_sessions, shifts)

    return {
        "module": "staff",
        "status": "OPERATIONAL",
        "total_staff_core_team": total_staff,
        "active_shifts_count": active_shifts,
        "peak_volunteer_demand": demand_rep.get("peak_requirement", 0),
        "peak_available_on_shift": demand_rep.get("peak_available_on_shift", 0),
        "max_staffing_gap": demand_rep.get("max_gap", 0),
        "uncovered_hours_total": demand_rep.get("uncovered_hours_total", 0.0),
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Returns active risks evaluated as of `now`."""
    risk_items: List[RiskItem] = []

    # 1. Staffing gap / volunteer shortage risk
    event_sessions = [s.model_dump() for s in session.exec(select(EventSession)).all()]
    shifts = [s.model_dump() for s in session.exec(select(Shift)).all()]
    demand_rep = PureStaffEngine.calculate_demand_and_gaps(event_sessions, shifts)

    max_gap = demand_rep.get("max_gap", 0)
    uncovered_h = demand_rep.get("uncovered_hours_total", 0.0)
    if max_gap > 0:
        risk_items.append(RiskItem(
            id="risk_staff_shortage",
            module="staff",
            kind="VOLUNTEER_SHORTAGE",
            title=f"Critical volunteer deficit: peak gap of {max_gap} volunteers across {uncovered_h}h",
            severity=Severity.CRITICAL if max_gap >= 30 else Severity.HIGH,
            people_affected=int(max_gap * 10),
            hours_to_impact=4.0,
            uncertainty=0.1,
            resource_criticality=4,
            entity_refs=[EntityRef(type="module", id="staff", label="Staff and Volunteers")],
            action=ActionRef(
                label="View Coverage Gaps",
                route="/staff/demand",
                api="/api/v1/staff/demand",
            ),
            explanation=f"Event sessions require up to {demand_rep.get('peak_requirement')} simultaneous volunteers but peak shift coverage is {demand_rep.get('peak_available_on_shift')}.",
        ))

    # 2. Overloaded staff risk
    overloaded = PureStaffEngine.detect_overloaded_staff(shifts)
    if overloaded:
        risk_items.append(RiskItem(
            id="risk_staff_overload",
            module="staff",
            kind="STAFF_OVERLOAD",
            title=f"{len(overloaded)} staff members exceed daily or consecutive hour thresholds",
            severity=Severity.HIGH,
            people_affected=len(overloaded),
            hours_to_impact=8.0,
            uncertainty=0.0,
            resource_criticality=3,
            entity_refs=[EntityRef(type="staff", id=o["staff_id"], label=o["name"]) for o in overloaded[:5]],
            action=ActionRef(
                label="Suggest Replacements",
                route="/staff/overloaded",
                api="/api/v1/staff/overloaded",
            ),
            explanation="Staff fatigue violates festival labor standards and risks critical ops failure.",
        ))

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Returns downstream entities affected by entity_type:entity_id."""
    deps: List[EntityRef] = []
    if entity_type == "staff":
        shifts = session.exec(select(Shift).where(Shift.staff_id == entity_id)).all()
        for sh in shifts:
            deps.append(EntityRef(type="shift", id=sh.id, label=f"Shift {sh.role_required} at {sh.location}"))
            if sh.session_id:
                deps.append(EntityRef(type="event_session", id=sh.session_id, label=f"Event Session {sh.session_id}"))
    elif entity_type == "event_session":
        shifts = session.exec(select(Shift).where(Shift.session_id == entity_id)).all()
        for sh in shifts:
            deps.append(EntityRef(type="shift", id=sh.id, label=f"Staff Shift {sh.id}"))
            if sh.staff_id:
                deps.append(EntityRef(type="staff", id=sh.staff_id, label=f"Assigned Staff {sh.staff_id}"))

    return deps


def staff_coverage_csv(session: Session) -> str:
    """Downloadable CSV for staff coverage analysis."""
    return generate_staff_coverage_csv(session)
