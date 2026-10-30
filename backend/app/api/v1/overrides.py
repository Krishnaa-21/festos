# OWNER: P3
from typing import Any, Dict, Optional

import app.core.overrides as overrides_core
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.errors import NotFoundError
from app.models.audit import Override
from app.schemas.common import Actor, Envelope, Page
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

router = APIRouter(prefix="/overrides", tags=["Overrides"])


class CreateOverrideRequest(BaseModel):
    entity_type: str = Field(..., description="Entity being relaxed, e.g., room, event, schedule")
    entity_id: str = Field(..., description="Target entity ID")
    constraint_code: str = Field(..., description="Constraint identifier being bypassed")
    reason: str = Field(..., description="Mandatory rationale under FestOS principles")
    risk_level: str = Field(default="HIGH", description="Risk level: LOW | HIGH | CRITICAL")


@router.get("", response_model=Envelope[Page[Dict[str, Any]]])
def list_overrides(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    entity_type: Optional[str] = Query(default=None),
    constraint_code: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """Query the override register with filtering and pagination."""
    query = select(Override)

    if entity_type:
        query = query.where(Override.entity_type == entity_type)
    if constraint_code:
        query = query.where(Override.constraint_code == constraint_code)
    if risk_level:
        query = query.where(Override.risk_level == risk_level)
    if status:
        query = query.where(Override.status == status)

    all_rows = session.exec(query).all()
    total = len(all_rows)

    items = session.exec(
        query.order_by(Override.approved_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    formatted_items = [
        {
            "id": o.id,
            "entity_type": o.entity_type,
            "entity_id": o.entity_id,
            "constraint_code": o.constraint_code,
            "reason": o.reason,
            "approved_by": o.approved_by,
            "approved_at": o.approved_at.isoformat() if o.approved_at else None,
            "risk_level": o.risk_level,
            "status": o.status
        }
        for o in items
    ]

    page_data = Page.create(
        items=formatted_items,
        total=total,
        page=page,
        page_size=page_size
    )

    return Envelope(data=page_data)


@router.post("", response_model=Envelope[Dict[str, Any]])
def post_create_override(
    body: CreateOverrideRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """Record an operational override directly into the register. Enforces mandatory reason."""
    override = overrides_core.record(
        session=session,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        constraint_code=body.constraint_code,
        reason=body.reason,
        actor=actor,
        risk_level=body.risk_level
    )
    session.commit()

    return Envelope(
        data={
            "id": override.id,
            "entity_type": override.entity_type,
            "entity_id": override.entity_id,
            "constraint_code": override.constraint_code,
            "reason": override.reason,
            "approved_by": override.approved_by,
            "approved_at": override.approved_at.isoformat() if override.approved_at else None,
            "risk_level": override.risk_level,
            "status": override.status
        },
        warnings=["Operational override recorded in register and audit log."]
    )


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_override_detail(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """Retrieve details for a single recorded override."""
    override = session.get(Override, id)
    if not override:
        raise NotFoundError(f"Override '{id}' not found")

    return Envelope(
        data={
            "id": override.id,
            "entity_type": override.entity_type,
            "entity_id": override.entity_id,
            "constraint_code": override.constraint_code,
            "reason": override.reason,
            "approved_by": override.approved_by,
            "approved_at": override.approved_at.isoformat() if override.approved_at else None,
            "risk_level": override.risk_level,
            "status": override.status
        }
    )
