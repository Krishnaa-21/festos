# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest, execute_change
from app.core.clock import now
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.registry import register_change_handler
from app.models.ops import NotificationDraft
from app.schemas.common import Actor, Envelope, Violation

router = APIRouter(prefix="/notifications", tags=["notifications"])


class DraftNotificationBody(BaseModel):
    channel: str = "SMS"
    recipient: str
    subject: Optional[str] = None
    body: str
    reason: Optional[str] = None


@register_change_handler("notification.draft")
class NotificationDraftHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        payload = req.payload
        draft = NotificationDraft(
            channel=payload.get("channel", "SMS"),
            recipient=payload.get("recipient", "ALL_PARTICIPANTS"),
            subject=payload.get("subject"),
            body=payload.get("body", ""),
            status="DRAFT",
            created_at=now(),
        )
        session.add(draft)
        session.flush()
        return {"notification_id": draft.id, "recipient": draft.recipient, "status": draft.status}


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/drafts", response_model=Envelope[Dict[str, Any]])
def list_notifications(
    channel: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List operational notification drafts."""
    query = select(NotificationDraft).order_by(NotificationDraft.created_at.desc())
    if channel:
        query = query.where(NotificationDraft.channel == channel.upper())
    if status_filter:
        query = query.where(NotificationDraft.status == status_filter.upper())

    all_items = session.exec(query).all()
    total = len(all_items)
    start = (page - 1) * page_size
    items = all_items[start : start + page_size]

    return Envelope(
        data={
            "items": [
                {
                    "id": d.id,
                    "channel": d.channel,
                    "recipient": d.recipient,
                    "subject": d.subject,
                    "body": d.body,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/drafts", response_model=Envelope[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
def draft_notification(
    body: DraftNotificationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Draft an operational notification via ChangeService."""
    req = ChangeRequest(
        action="notification.draft",
        entity_type="notification_draft",
        entity_id=f"notif_{now().strftime('%Y%m%d%H%M%S')}",
        payload=body.model_dump(),
        reason=body.reason or f"Drafted broadcast notification for {body.recipient}",
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())
