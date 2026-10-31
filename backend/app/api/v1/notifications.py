# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.db import get_session
from app.core.deps import require_permission
from app.schemas.common import Actor, Envelope
from app.schemas.notifications import (
    DeliveryLogSchema,
    EditDraftRequest,
    GenerateDraftsRequest,
    NotificationDraftSchema,
    TemplateSchema,
)
from app.services.notifications.service import (
    approve_draft,
    generate_drafts,
    get_delivery_logs,
    get_draft,
    list_drafts,
    list_templates,
    send_draft,
    update_draft,
)
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

router = APIRouter(prefix="/notifications", tags=["Notification Engine"])


@router.get("/drafts", response_model=Envelope[Dict[str, Any]])
def list_drafts_endpoint(
    audience: Optional[str] = Query(None, description="Filter by audience (contingent_leaders, volunteers, vendors, accommodation_coordinators, event_organisers)"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PENDING_APPROVAL, APPROVED, SENT, REJECTED)"),
    channel: Optional[str] = Query(None, description="Filter by channel (SMS, APP, EMAIL, WHATSAPP)"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:read")),
):
    """List notification drafts with audience and approval status."""
    drafts = list_drafts(session=session, audience=audience, status=status, channel=channel)
    items = [
        NotificationDraftSchema(
            id=d.id,
            audience=d.audience,
            channel=d.channel,
            recipient=d.recipient,
            subject=d.subject,
            body=d.body,
            status=d.status,
            requires_approval=d.requires_approval,
            template_key=d.template_key,
            related_change_set_id=d.related_change_set_id,
            related_incident_id=d.related_incident_id,
            created_at=d.created_at.isoformat(),
        )
        for d in drafts
    ]
    return Envelope(data={"items": items, "total": len(items)})


@router.get("/drafts/{id}", response_model=Envelope[NotificationDraftSchema])
def get_draft_endpoint(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:read")),
):
    """Get single notification draft details."""
    d = get_draft(session, id)
    return Envelope(
        data=NotificationDraftSchema(
            id=d.id,
            audience=d.audience,
            channel=d.channel,
            recipient=d.recipient,
            subject=d.subject,
            body=d.body,
            status=d.status,
            requires_approval=d.requires_approval,
            template_key=d.template_key,
            related_change_set_id=d.related_change_set_id,
            related_incident_id=d.related_incident_id,
            created_at=d.created_at.isoformat(),
        )
    )


@router.post("/drafts/generate", response_model=Envelope[Dict[str, Any]])
def generate_drafts_endpoint(
    body: GenerateDraftsRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:write")),
):
    """Generate audience-targeted notification drafts from structured change data."""
    drafts = generate_drafts(
        event_type=body.event_type,
        context=body.context,
        change_set_id=body.change_set_id,
        incident_id=body.incident_id,
        session=session,
    )
    return Envelope(
        data={
            "drafts_generated": len(drafts),
            "draft_ids": [d.id for d in drafts],
            "audiences": [d.audience for d in drafts],
        }
    )


@router.put("/drafts/{id}", response_model=Envelope[NotificationDraftSchema])
@router.patch("/drafts/{id}", response_model=Envelope[NotificationDraftSchema])
@router.post("/drafts/{id}/edit", response_model=Envelope[NotificationDraftSchema])
def update_draft_endpoint(
    id: str,
    body: EditDraftRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:write")),
):
    """Edit notification draft subject, body, or recipient before dispatch."""
    d = update_draft(session=session, draft_id=id, req=body, actor=actor)
    return Envelope(
        data=NotificationDraftSchema(
            id=d.id,
            audience=d.audience,
            channel=d.channel,
            recipient=d.recipient,
            subject=d.subject,
            body=d.body,
            status=d.status,
            requires_approval=d.requires_approval,
            template_key=d.template_key,
            related_change_set_id=d.related_change_set_id,
            related_incident_id=d.related_incident_id,
            created_at=d.created_at.isoformat(),
        )
    )


@router.post("/drafts/{id}/approve", response_model=Envelope[Dict[str, Any]])
def approve_draft_endpoint(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:approve")),
):
    """Approve a notification draft for sending."""
    d = approve_draft(session=session, draft_id=id, actor=actor)
    return Envelope(
        data={
            "id": d.id,
            "status": d.status,
            "approved_by": d.approved_by,
            "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        }
    )


@router.post("/drafts/{id}/send", response_model=Envelope[DeliveryLogSchema])
def send_draft_endpoint(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:write")),
):
    """Mock-send a notification draft. Strictly requires prior approval."""
    log = send_draft(session=session, draft_id=id, actor=actor)
    return Envelope(
        data=DeliveryLogSchema(
            id=log.id,
            draft_id=log.draft_id,
            audience=log.audience,
            recipient=log.recipient,
            channel=log.channel,
            subject=log.subject,
            body=log.body,
            sent_at=log.sent_at.isoformat(),
            status=log.status,
            provider=log.provider,
        )
    )


@router.get("/log", response_model=Envelope[Dict[str, Any]])
def get_log_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:read")),
):
    """Return the complete delivery audit log of dispatched notifications."""
    logs = get_delivery_logs(session)
    items = [
        DeliveryLogSchema(
            id=log_item.id,
            draft_id=log_item.draft_id,
            audience=log_item.audience,
            recipient=log_item.recipient,
            channel=log_item.channel,
            subject=log_item.subject,
            body=log_item.body,
            sent_at=log_item.sent_at.isoformat(),
            status=log_item.status,
            provider=log_item.provider,
        )
        for log_item in logs
    ]

    return Envelope(data={"logs": items, "total": len(items)})


@router.get("/templates", response_model=Envelope[List[TemplateSchema]])
def list_templates_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("notifications:read")),
):
    """List available notification templates across the 5 audiences."""
    templates = list_templates()
    items = [TemplateSchema(**t) for t in templates]
    return Envelope(data=items)
