# OWNER: P3
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.audit import Override
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return overrides KPI summary as of `now`."""
    try:
        all_ovr = session.exec(select(Override)).all()
        total = len(all_ovr)
        active = sum(1 for o in all_ovr if o.status == "ACTIVE")
        high_risk = sum(1 for o in all_ovr if o.risk_level in ["HIGH", "CRITICAL"] and o.status == "ACTIVE")
    except Exception:
        total, active, high_risk = 0, 0, 0

    return {
        "module": "overrides",
        "total_overrides": total,
        "active_overrides": active,
        "high_risk_active": high_risk,
        "status": "OPERATIONAL"
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active high-risk constraint overrides evaluated as of `now`."""
    items: List[RiskItem] = []
    try:
        active_high = session.exec(
            select(Override).where(Override.status == "ACTIVE", Override.risk_level.in_(["HIGH", "CRITICAL"]))
        ).all()
        for o in active_high:
            items.append(
                RiskItem(
                    id=f"risk_override_{o.id}",
                    module="overrides",
                    kind="ACTIVE_HIGH_RISK_OVERRIDE",
                    title=f"Active Override: {o.constraint_code} on {o.entity_type}",
                    severity=Severity.HIGH if o.risk_level == "HIGH" else Severity.CRITICAL,
                    hours_to_impact=1.0,
                    people_affected=15,
                    uncertainty=0.05,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type=o.entity_type, id=o.entity_id, label=f"{o.entity_type}:{o.entity_id}")],
                    action=ActionRef(label="View Override Register", route="/audit", api=f"/api/v1/overrides/{o.id}"),
                    explanation=f"Constraint relaxation authorized by {o.approved_by}: {o.reason}"
                )
            )
    except Exception:
        pass
    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    try:
        ovrs = session.exec(
            select(Override).where(Override.entity_type == entity_type, Override.entity_id == entity_id)
        ).all()
        return [
            EntityRef(type="override", id=o.id, label=f"Override: {o.constraint_code}")
            for o in ovrs
        ]
    except Exception:
        return []
