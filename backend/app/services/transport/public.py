# OWNER: P1
import csv
import io
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.registry import register_participant_section
from app.models.participants import Participant
from app.models.transport import (
    EscortAssignment,
    GuardianApproval,
    ShuttleAssignment,
    ShuttleRun,
)
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity
from app.services.transport import service as transport_service


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Returns module KPI summary as of `now`."""
    cov = transport_service.get_coverage_summary(session)
    return {
        "module": "transport",
        "status": "OPERATIONAL",
        "people_requiring_transport": cov.get("people_requiring_transport", 0),
        "confirmed_shuttle_capacity": cov.get("confirmed_shuttle_capacity", 0),
        "uncovered_transport_requests": cov.get("uncovered_transport_requests", 0),
        "late_night_movements_count": cov.get("late_night_movements", 0),
        "pending_minor_approvals_count": cov.get("pending_minor_approvals", 0),
        "unassigned_escorts_count": cov.get("unassigned_escorts", 0),
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Returns active duty-of-care and transport risks evaluated as of `now`."""
    risk_items: List[RiskItem] = []

    # 1. Unverified late-night movements
    night_roster = transport_service.get_night_roster(session)
    unverified = night_roster.get("total_unverified", 0)
    if unverified > 0:
        risk_items.append(RiskItem(
            id="risk_unverified_night_transit",
            module="transport",
            kind="DUTY_OF_CARE_UNVERIFIED",
            title=f"{unverified} participants in external stays have unverified late-night transit or missing escort",
            severity=Severity.CRITICAL if unverified >= 10 else Severity.HIGH,
            people_affected=unverified,
            hours_to_impact=2.0,
            uncertainty=0.0,
            resource_criticality=5,
            entity_refs=[EntityRef(type="module", id="transport", label="Duty of Care and Transport")],
            action=ActionRef(
                label="Verify Night Roster",
                route="/transport/safety/night-roster",
                api="/api/v1/transport/safety/night-roster",
            ),
            explanation="Late-night movements between external properties and campus without verified shuttles pose critical participant safety risk.",
        ))

    # 2. Minors pending guardian approval
    g_queue = transport_service.get_guardian_queue(session)
    pending_minors = g_queue.get("pending_count", 0)
    if pending_minors > 0:
        risk_items.append(RiskItem(
            id="risk_minor_guardian_pending",
            module="transport",
            kind="MINOR_GUARDIAN_APPROVAL_PENDING",
            title=f"{pending_minors} minor participants in external stays await guardian authorization and escort verification",
            severity=Severity.HIGH,
            people_affected=pending_minors,
            hours_to_impact=12.0,
            uncertainty=0.05,
            resource_criticality=4,
            entity_refs=[EntityRef(type="queue", id="guardian_queue", label="Guardian Approval Queue")],
            action=ActionRef(
                label="Approve Minor Stays",
                route="/transport/guardians/queue",
                api="/api/v1/transport/guardians/queue",
            ),
            explanation="Festival duty of care strictly mandates verified parental/guardian consent and named escort for all minor participants housed off campus.",
        ))

    # 3. Shuttle capacity deficit
    plan = transport_service.get_shuttle_plan(session)
    shortage_runs = plan.get("plan_summary", {}).get("shortage_runs", 0)
    if shortage_runs > 0:
        risk_items.append(RiskItem(
            id="risk_shuttle_capacity_deficit",
            module="transport",
            kind="SHUTTLE_CAPACITY_DEFICIT",
            title=f"External property shuttle shortage: deficit of {shortage_runs} runs",
            severity=Severity.MEDIUM,
            people_affected=shortage_runs * 15,
            hours_to_impact=6.0,
            uncertainty=0.1,
            resource_criticality=3,
            entity_refs=[EntityRef(type="fleet", id="shuttles", label="Shuttle Fleet")],
            action=ActionRef(
                label="Adjust Transport Assumptions",
                route="/transport/assumptions",
                api="/api/v1/transport/assumptions",
            ),
            explanation="External participants exceed currently scheduled shuttle capacity during peak transfer windows.",
        ))

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Returns downstream entities affected by entity_type:entity_id."""
    deps: List[EntityRef] = []
    if entity_type == "external_property":
        runs = session.exec(select(ShuttleRun).where(ShuttleRun.property_id == entity_id)).all()
        for r in runs:
            deps.append(EntityRef(type="shuttle_run", id=r.id, label=f"Run {r.route_name}"))
        approvals = session.exec(select(GuardianApproval).where(GuardianApproval.property_id == entity_id)).all()
        for a in approvals:
            deps.append(EntityRef(type="guardian_approval", id=a.id, label=f"Minor Guardian Approval {a.id}"))
    elif entity_type == "shuttle_run":
        assignments = session.exec(select(ShuttleAssignment).where(ShuttleAssignment.shuttle_run_id == entity_id)).all()
        for sa in assignments:
            deps.append(EntityRef(type="participant", id=sa.participant_id, label=f"Passenger {sa.participant_id}"))

    return deps


def transport_feasible(session: Session, property_id: str, time_val: datetime) -> bool:
    """Exposed for accommodation engine rule 6: returns whether transit is feasible."""
    res = transport_service.check_feasibility(
        session=session,
        property_id=property_id,
        time_str=time_val.isoformat(),
    )
    return bool(res.get("is_feasible", False))


def resource_load_timeline_csv(session: Session) -> str:
    """Generates CSV of hourly shuttle vehicle demand and capacity."""
    plan = transport_service.get_shuttle_plan(session)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "property_id",
        "property_name",
        "window_start",
        "window_end",
        "passengers",
        "required_runs",
        "confirmed_runs",
        "shortage",
        "is_uncovered",
    ])
    for prop in plan.get("property_plans", []):
        pid = prop.get("property_id")
        pname = prop.get("property_name")
        for win in prop.get("windows", []):
            writer.writerow([
                pid,
                pname,
                win.get("window_start"),
                win.get("window_end"),
                win.get("passengers"),
                win.get("required_runs"),
                win.get("confirmed_runs"),
                win.get("shortage"),
                win.get("is_uncovered"),
            ])
    return output.getvalue()


@register_participant_section("transport")
def participant_transport_section(participant_id: str, session: Session) -> Dict[str, Any]:
    """Dynamic participant 360 section showing transport arrangements, safety verification, and guardian status."""
    p = session.get(Participant, participant_id)

    # 1. Shuttle assignments
    assignments = session.exec(
        select(ShuttleAssignment).where(ShuttleAssignment.participant_id == participant_id)
    ).all()

    assigned_shuttles = []
    safety_verified = False
    verified_by = None
    for sa in assignments:
        run = session.get(ShuttleRun, sa.shuttle_run_id) if sa.shuttle_run_id else None
        assigned_shuttles.append({
            "assignment_id": sa.id,
            "route_name": run.route_name if run else "Campus Shuttle",
            "departure_at": sa.departure_at.isoformat() if sa.departure_at else (run.departure_at.isoformat() if run and run.departure_at else None),
            "pickup_location": sa.pickup_location,
            "drop_location": sa.drop_location,
            "status": sa.status,
            "safety_verified": sa.safety_verified,
        })
        if sa.safety_verified:
            safety_verified = True
            verified_by = sa.verified_by_staff_id

    # 2. Escort assignment
    escort_asn = session.exec(
        select(EscortAssignment).where(EscortAssignment.participant_id == participant_id)
    ).first()

    # 3. Guardian approval if minor
    guardian_status = "NOT_REQUIRED"
    approval_id = None
    if p and p.age is not None and p.age < 18:
        appr = session.exec(
            select(GuardianApproval).where(GuardianApproval.participant_id == participant_id)
        ).first()
        if appr:
            guardian_status = appr.approval_status
            approval_id = appr.id
        else:
            guardian_status = "PENDING"

    return {
        "participant_id": participant_id,
        "is_minor": bool(p and p.age is not None and p.age < 18),
        "guardian_approval_status": guardian_status,
        "guardian_approval_id": approval_id,
        "safety_verified": safety_verified,
        "verified_by_staff_id": verified_by,
        "assigned_escort_staff_id": escort_asn.staff_id if escort_asn else None,
        "shuttle_runs": assigned_shuttles,
    }
