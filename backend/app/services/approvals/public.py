# OWNER: P3
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.audit import Approval
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return approvals KPI summary as of `now`."""
    try:
        all_appr = session.exec(select(Approval)).all()
        pending = sum(1 for a in all_appr if a.status == "PENDING")
        approved = sum(1 for a in all_appr if a.status == "APPROVED")
        rejected = sum(1 for a in all_appr if a.status == "REJECTED")
    except Exception:
        pending, approved, rejected = 0, 0, 0

    return {
        "module": "approvals",
        "pending_count": pending,
        "approved_count": approved,
        "rejected_count": rejected,
        "status": "OPERATIONAL"
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return approvals bottlenecks evaluated as of `now`."""
    items: List[RiskItem] = []
    try:
        pending_list = session.exec(select(Approval).where(Approval.status == "PENDING")).all()
        for a in pending_list:
            age_hours = (now - a.created_at).total_seconds() / 3600.0 if a.created_at else 0.0
            if age_hours > 2.0:
                items.append(
                    RiskItem(
                        id=f"risk_approval_{a.id}",
                        module="approvals",
                        kind="PENDING_APPROVAL_BOTTLENECK",
                        title=f"Unresolved {a.risk_kind or 'High-Risk'} Approval ({a.entity_type})",
                        severity=Severity.HIGH,
                        hours_to_impact=max(0.5, 4.0 - age_hours),
                        people_affected=10,
                        uncertainty=0.1,
                        resource_criticality=4,
                        entity_refs=[EntityRef(type=a.entity_type, id=a.entity_id, label=f"{a.entity_type}:{a.entity_id}")],
                        action=ActionRef(label="Review Approval", route="/audit", api=f"/api/v1/approvals/{a.id}"),
                        explanation=f"Awaiting sign-off by {a.required_role} for {age_hours:.1f} hours: {a.reason or 'No reason specified'}"
                    )
                )
    except Exception:
        pass
    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    try:
        apprs = session.exec(
            select(Approval).where(Approval.entity_type == entity_type, Approval.entity_id == entity_id)
        ).all()
        return [
            EntityRef(type="approval", id=a.id, label=f"Approval: {a.status}")
            for a in apprs
        ]
    except Exception:
        return []
