# OWNER: P3
import csv
import io
from datetime import datetime
from typing import Any, Dict, Optional

from app.core import clock
from app.core.audit import verify_chain
from app.core.db import get_session
from app.core.deps import require_permission
from app.core.masking import mask_fields
from app.models.audit import AuditEvent
from app.schemas.common import Actor, Envelope, Page
from app.services.reports.csv_sanitizer import sanitize_csv_value
from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session, select

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events", response_model=Envelope[Page[Dict[str, Any]]])
def list_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    from_time: Optional[datetime] = Query(default=None),
    to_time: Optional[datetime] = Query(default=None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("audit:read"))
):
    """Query immutable audit events with pagination, filtering, and role-based masking."""
    query = select(AuditEvent)

    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if from_time:
        query = query.where(AuditEvent.timestamp >= from_time)
    if to_time:
        query = query.where(AuditEvent.timestamp <= to_time)

    # Get total count
    all_rows = session.exec(query).all()
    total = len(all_rows)

    # Paged query
    query = query.order_by(AuditEvent.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    items = session.exec(query).all()

    # Format items and apply field-level masking
    masked_items = []
    for item in items:
        item_dict = {
            "id": item.id,
            "actor_id": item.actor_id,
            "actor_name": item.actor_name,
            "actor_role": item.actor_role,
            "action": item.action,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "before_state": mask_fields(item.before_state, actor, f"{item.entity_type}:{item.entity_id}", session),
            "after_state": mask_fields(item.after_state, actor, f"{item.entity_type}:{item.entity_id}", session),
            "change_set_id": item.change_set_id,
            "reason": item.reason,
            "approval_id": item.approval_id,
            "related_incident_id": item.related_incident_id,
            "status": item.status,
            "prev_hash": item.prev_hash,
            "current_hash": item.current_hash,
            "timestamp": item.timestamp.isoformat()
        }
        masked_items.append(item_dict)

    page_result = Page.create(
        items=masked_items,
        total=total,
        page=page,
        page_size=page_size
    )

    return Envelope(data=page_result)


@router.get("/timeline/{entity_type}/{entity_id}", response_model=Envelope[Dict[str, Any]])
def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("audit:read"))
):
    """Retrieve chronological timeline of mutations for a specific entity."""
    query = (
        select(AuditEvent)
        .where(AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.timestamp.asc())
    )
    events = session.exec(query).all()

    timeline = []
    for ev in events:
        timeline.append({
            "id": ev.id,
            "action": ev.action,
            "actor_id": ev.actor_id,
            "actor_name": ev.actor_name,
            "actor_role": ev.actor_role,
            "reason": ev.reason,
            "status": ev.status,
            "timestamp": ev.timestamp.isoformat(),
            "before_state": mask_fields(ev.before_state, actor, f"{entity_type}:{entity_id}", session),
            "after_state": mask_fields(ev.after_state, actor, f"{entity_type}:{entity_id}", session),
            "prev_hash": ev.prev_hash,
            "current_hash": ev.current_hash
        })

    return Envelope(
        data={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timeline": timeline,
            "total_events": len(timeline)
        }
    )


@router.get("/verify", response_model=Envelope[Dict[str, Any]])
def verify_audit_hash_chain(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("audit:read"))
):
    """Cryptographically verify the integrity of the audit log hash chain."""
    result = verify_chain(session)
    warnings = []
    if not result.get("valid"):
        warnings.append("CRITICAL: Audit log integrity failure detected! An event hash divergence was found.")
    return Envelope(
        data=result,
        warnings=warnings
    )


@router.get("/export/csv")
def export_audit_csv(
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    from_time: Optional[datetime] = Query(default=None),
    to_time: Optional[datetime] = Query(default=None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("audit:export"))
):
    """Export audit events as CSV respecting role-based masking and export permissions."""
    query = select(AuditEvent)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if action:
        query = query.where(AuditEvent.action == action)
    if from_time:
        query = query.where(AuditEvent.timestamp >= from_time)
    if to_time:
        query = query.where(AuditEvent.timestamp <= to_time)

    events = session.exec(query.order_by(AuditEvent.timestamp.desc())).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "timestamp", "action", "entity_type", "entity_id",
        "actor_id", "actor_name", "actor_role", "reason", "status",
        "prev_hash", "current_hash"
    ])

    for ev in events:
        writer.writerow([
            sanitize_csv_value(ev.id),
            sanitize_csv_value(ev.timestamp.isoformat()),
            sanitize_csv_value(ev.action),
            sanitize_csv_value(ev.entity_type),
            sanitize_csv_value(ev.entity_id),
            sanitize_csv_value(ev.actor_id),
            sanitize_csv_value(ev.actor_name),
            sanitize_csv_value(ev.actor_role),
            sanitize_csv_value(ev.reason or ""),
            sanitize_csv_value(ev.status),
            sanitize_csv_value(ev.prev_hash),
            sanitize_csv_value(ev.current_hash),
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=festos_audit_export_{clock.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )
