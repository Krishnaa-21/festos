# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.audit import Approval, AuditEvent
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    total_parsed = session.exec(
        select(func.count(AuditEvent.id)).where(AuditEvent.action == "command.parsed")
    ).one() or 0

    total_executed = session.exec(
        select(func.count(AuditEvent.id)).where(AuditEvent.action == "command.executed")
    ).one() or 0

    pending_proposals = session.exec(
        select(func.count(Approval.id)).where(
            Approval.status == "PENDING",
            Approval.entity_type == "accommodation"
        )
    ).one() or 0

    return {
        "module": "commands",
        "status": "OPERATIONAL",
        "total_commands_parsed": total_parsed,
        "total_commands_executed": total_executed,
        "pending_command_proposals": pending_proposals,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    pending_proposals = session.exec(
        select(Approval).where(
            Approval.status == "PENDING",
            Approval.entity_type == "accommodation"
        )
    ).all()

    items: List[RiskItem] = []
    if pending_proposals:
        items.append(
            RiskItem(
                id="rsk_commands_pending_proposals",
                module="commands",
                kind="PROPOSALS_PENDING_APPROVAL",
                title=f"{len(pending_proposals)} command-bar housing proposals awaiting approval",
                severity=2,
                hours_to_impact=6.0,
                people_affected=len(pending_proposals) * 48,
                uncertainty=0.1,
                resource_criticality=3,
                entity_refs=[EntityRef(type="approval", id=p.id, label=p.reason or "Command proposal") for p in pending_proposals[:5]],
                action={"label": "Review Proposals", "route": "/approvals", "api": "/api/v1/approvals"},
                explanation="Command bar allocation proposals require Festival Director sign-off before beds can be locked in."
            )
        )
    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
