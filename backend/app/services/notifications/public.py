# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now as clock_now
from app.models.ops import NotificationDeliveryLog, NotificationDraft
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return notification engine summary as of `now`."""
    if now is None:
        now = clock_now()
    drafts = session.exec(select(NotificationDraft)).all()
    pending = [d for d in drafts if d.status == "PENDING_APPROVAL"]
    approved = [d for d in drafts if d.status == "APPROVED"]
    sent = session.exec(select(NotificationDeliveryLog)).all()

    return {
        "module": "notifications",
        "status": "OPERATIONAL",
        "total_drafts": len(drafts),
        "pending_approval": len(pending),
        "approved_ready_to_send": len(approved),
        "total_delivered": len(sent),
    }


def risks(session: Session, now: Optional[datetime] = None) -> List[RiskItem]:
    """Return notification delivery risks as of `now`."""
    if now is None:
        now = clock_now()
    risk_list: List[RiskItem] = []
    drafts = session.exec(
        select(NotificationDraft).where(NotificationDraft.status == "PENDING_APPROVAL")
    ).all()

    for d in drafts:
        if d.related_incident_id or "URGENT" in (d.subject or "").upper():
            risk_list.append(
                RiskItem(
                    id=f"rsk_not_pending_{d.id}",
                    module="notifications",
                    kind="UNAPPROVED_CRITICAL_NOTIFICATION",
                    title=f"Pending Notification Approval: {d.audience}",
                    severity=3,
                    hours_to_impact=1.0,
                    people_affected=100,
                    uncertainty=0.0,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="notification_draft", id=d.id, label=d.id)],
                    action={"label": "Approve Draft", "route": "/notifications", "api": f"/api/v1/notifications/drafts/{d.id}/approve"},
                    explanation=f"Critical dispatch pending Director/Lead approval: '{d.subject}'",
                )
            )

    return risk_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by notification draft."""
    deps: List[EntityRef] = []
    if entity_type == "notification_draft":
        d = session.get(NotificationDraft, entity_id)
        if d:
            if d.related_change_set_id:
                deps.append(EntityRef(type="change_set", id=d.related_change_set_id, label="Related ChangeSet"))
            if d.related_incident_id:
                deps.append(EntityRef(type="incident", id=d.related_incident_id, label="Related Incident"))
            deps.append(EntityRef(type="audience", id=d.audience, label=f"Audience {d.audience}"))
    return deps
