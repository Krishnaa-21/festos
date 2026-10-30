# OWNER: P3
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, col, select

from app.models.audit import BreakGlassGrant, User
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return auth module KPI summary as of `now`."""
    try:
        users = session.exec(select(User)).all()
        total_users = len(users)
        active_users = sum(1 for u in users if u.is_active)
        locked_users = sum(1 for u in users if u.locked_until and u.locked_until > now)

        grants = session.exec(
            select(BreakGlassGrant).where(BreakGlassGrant.expires_at > now, col(BreakGlassGrant.is_revoked).is_(False))
        ).all()
        active_break_glass = len(grants)
    except Exception:
        total_users, active_users, locked_users, active_break_glass = 0, 0, 0, 0

    return {
        "module": "auth",
        "total_users": total_users,
        "active_users": active_users,
        "locked_users": locked_users,
        "active_break_glass": active_break_glass,
        "status": "OPERATIONAL"
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active authentication & access elevation risks evaluated as of `now`."""
    items: List[RiskItem] = []
    try:
        active_grants = session.exec(
            select(BreakGlassGrant).where(BreakGlassGrant.expires_at > now, col(BreakGlassGrant.is_revoked).is_(False))
        ).all()

        for g in active_grants:
            items.append(
                RiskItem(
                    id=f"risk_bgg_{g.id}",
                    module="auth",
                    kind="ELEVATED_BREAK_GLASS",
                    title=f"Active Emergency Elevation on {g.entity}",
                    severity=Severity.HIGH,
                    hours_to_impact=max(0.1, (g.expires_at - now).total_seconds() / 3600.0),
                    people_affected=1,
                    uncertainty=0.0,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="break_glass_grant", id=g.id, label=f"{g.entity}.{g.field}")],
                    action=ActionRef(label="View Audit Trail", route="/audit", api="/api/v1/auth/break-glass"),
                    explanation=f"Emergency unmasking active for user {g.user_id}: {g.reason}"
                )
            )
    except Exception:
        pass
    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
