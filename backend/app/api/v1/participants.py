# OWNER: P1
"""API router for Participant management, status state machine, and 360-degree view."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.participants.service import (
    get_participant,
    get_participant_360,
    get_timeline,
    list_participants,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/participants", tags=["Participants"])


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class ParticipantCreateBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class ParticipantUpdateBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class ParticipantStatusBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


def _get_actor(x_actor_role: Optional[str] = Header("VOLUNTEER"), x_actor_id: Optional[str] = Header("usr_anon")) -> Actor:
    return Actor(id=x_actor_id or "usr_anon", role=x_actor_role or "VOLUNTEER", name="API Actor")


# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------
@router.get("", response_model=Envelope[Dict[str, Any]])
def get_participants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("name"),
    q: Optional[str] = Query(None),
    contingent_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    event_id: Optional[str] = Query(None),
    diet: Optional[str] = Query(None),
    accessibility: Optional[str] = Query(None),
    unknown_field: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    arrival_window_start: Optional[datetime] = Query(None),
    arrival_window_end: Optional[datetime] = Query(None),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """List, filter, and fuzzy search canonical participants."""
    res = list_participants(
        session=session,
        page=page,
        page_size=page_size,
        sort=sort,
        q=q,
        contingent_id=contingent_id,
        status=status,
        event_id=event_id,
        diet=diet,
        accessibility=accessibility,
        unknown_field=unknown_field,
        role=role,
        arrival_window_start=arrival_window_start,
        arrival_window_end=arrival_window_end,
        actor_role=actor.role,
    )
    return Envelope(data=res)


@router.post("", response_model=Envelope[Any])
def create_participant(
    body: ParticipantCreateBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Register a new participant through ChangeService."""
    req = ChangeRequest(
        action="participant.create",
        entity_type="participant",
        entity_id=body.payload.get("id", ""),
        payload=body.payload,
        reason=body.reason or "Manual participant registration",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Creation rejected by constraint checks", "violations": [v.model_dump() for v in result.violations]},
        )
    return Envelope(data=result.model_dump(), warnings=result.warnings)


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_participant_by_id(
    id: str,
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Retrieve single participant profile with role-based field masking."""
    p = get_participant(session, id, actor_role=actor.role)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Participant {id} not found.")
    return Envelope(data=p)


@router.patch("/{id}", response_model=Envelope[Any])
def update_participant(
    id: str,
    body: ParticipantUpdateBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Update participant attributes through ChangeService."""
    req = ChangeRequest(
        action="participant.update",
        entity_type="participant",
        entity_id=id,
        payload=body.payload,
        reason=body.reason or "Participant profile update",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Update rejected by constraint checks", "violations": [v.model_dump() for v in result.violations]},
        )
    return Envelope(data=result.model_dump(), warnings=result.warnings)


@router.get("/{id}/360", response_model=Envelope[Dict[str, Any]])
def get_participant_360_view(
    id: str,
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """360-degree operational view aggregating contingent, events, diet, accessibility, merch, and status."""
    res = get_participant_360(session, id, actor_role=actor.role)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Participant {id} not found.")
    warnings = res.pop("warnings", [])
    return Envelope(data=res, warnings=warnings)


@router.post("/{id}/status", response_model=Envelope[Any])
def transition_status(
    id: str,
    body: ParticipantStatusBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Transition participant status through ChangeService (publishes participant.status_changed on bus)."""
    req = ChangeRequest(
        action="participant.change_status",
        entity_type="participant",
        entity_id=id,
        payload=body.payload,
        reason=body.reason or f"Transitioned status to {body.payload.get('status')}",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Status transition rejected", "violations": [v.model_dump() for v in result.violations]},
        )
    return Envelope(data=result.model_dump(), warnings=result.warnings)


@router.get("/{id}/timeline", response_model=Envelope[Dict[str, Any]])
def get_participant_timeline(
    id: str,
    session: Session = Depends(get_session),
):
    """Retrieve chronological audit events and mutation history for participant."""
    events = get_timeline(session, id)
    return Envelope(data={"participant_id": id, "events": events})
