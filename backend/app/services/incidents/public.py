# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.engines.impact.graph import _normalize_type
from app.models.ops import Incident
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return incidents module KPI summary as of `now`."""
    all_incidents = session.exec(select(Incident)).all()
    open_incidents = [i for i in all_incidents if i.status in ["OPEN", "ANALYSING", "PLAN_PROPOSED", "APPROVED", "EXECUTING"]]
    stalled_approvals = [i for i in all_incidents if i.status == "PLAN_PROPOSED"]
    closed_incidents = [i for i in all_incidents if i.status in ["VERIFIED", "CLOSED"]]
    total_people = sum(i.people_affected for i in open_incidents)

    return {
        "module": "incidents",
        "status": "OPERATIONAL" if not open_incidents else "DEGRADED",
        "total_incidents": len(all_incidents),
        "open_incidents_count": len(open_incidents),
        "stalled_approvals_count": len(stalled_approvals),
        "closed_incidents_count": len(closed_incidents),
        "total_people_affected": total_people,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`: open incidents and stalled approvals (Task 7)."""
    risk_items: List[RiskItem] = []

    all_incidents = session.exec(select(Incident)).all()

    # 1. Open Unresolved Incidents
    for inc in all_incidents:
        if inc.status in ["OPEN", "ANALYSING", "EXECUTING"]:
            sev = Severity.CRITICAL if inc.severity >= 4 else Severity.HIGH if inc.severity == 3 else Severity.MEDIUM
            risk_items.append(
                RiskItem(
                    id=f"risk_incident_{inc.id}",
                    module="incidents",
                    kind="INCIDENT_ACTIVE",
                    title=f"Active Incident: {inc.title}",
                    severity=sev,
                    hours_to_impact=2.0,
                    people_affected=inc.people_affected,
                    uncertainty=0.1,
                    resource_criticality=inc.severity,
                    entity_refs=[EntityRef(type="incident", id=inc.id, label=inc.title)],
                    action=ActionRef(
                        label="Review Incident & Blast Radius",
                        route=f"/incidents/{inc.id}",
                        api=f"/api/v1/incidents/{inc.id}",
                    ),
                    explanation=inc.description or f"Operational disruption {inc.scenario_type} is active.",
                )
            )

    # 2. Stalled Recovery Plan Approvals
    for inc in all_incidents:
        if inc.status == "PLAN_PROPOSED":
            risk_items.append(
                RiskItem(
                    id=f"risk_stalled_approval_{inc.id}",
                    module="incidents",
                    kind="STALLED_APPROVAL",
                    title=f"Stalled Approval: {inc.title} awaiting recovery plan decision",
                    severity=Severity.HIGH,
                    hours_to_impact=1.0,
                    people_affected=inc.people_affected,
                    uncertainty=0.0,
                    resource_criticality=3,
                    entity_refs=[EntityRef(type="incident", id=inc.id, label=inc.title)],
                    action=ActionRef(
                        label="Approve Recovery Plan",
                        route=f"/incidents/{inc.id}/plans",
                        api=f"/api/v1/incidents/{inc.id}/approve",
                    ),
                    explanation=f"Incident {inc.id} has {len(inc.plans)} recovery plans waiting for human review and sign-off.",
                )
            )

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    norm_type = _normalize_type(entity_type)
    incidents = session.exec(
        select(Incident).where(
            Incident.entity_id == entity_id,
            Incident.status.in_(["OPEN", "ANALYSING", "PLAN_PROPOSED", "APPROVED", "EXECUTING"]),
        )
    ).all()

    refs: List[EntityRef] = []
    for inc in incidents:
        if inc.entity_type and _normalize_type(inc.entity_type) == norm_type:
            refs.append(EntityRef(type="incident", id=inc.id, label=inc.title))
    return refs
