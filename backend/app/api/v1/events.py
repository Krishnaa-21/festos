# OWNER: P1
"""API router for Events, registrations, provisional teams, and judge registry."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import app.services.events.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.events.service import (
    get_event_profile,
    get_event_registrations,
    get_provisional_teams,
    list_events,
    list_judges_and_slots,
    register_judge,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session

router = APIRouter(prefix="/events", tags=["Events"])


class EventMutationBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)


class JudgeCreateBody(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    college_affiliation: Optional[str] = None
    expert_events: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


def _get_actor(
    x_actor_role: Optional[str] = Header("EVENT_LEAD"),
    x_actor_id: Optional[str] = Header("usr_event_lead"),
) -> Actor:
    return Actor(id=x_actor_id or "usr_event_lead", role=x_actor_role or "EVENT_LEAD", name="Event Lead")


@router.get("", response_model=Envelope[Dict[str, Any]])
def get_all_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    solo_team: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = list_events(session=session, page=page, page_size=page_size, solo_team=solo_team, q=q)
    return Envelope(data=result)


@router.get("/teams/provisional", response_model=Envelope[Dict[str, Any]])
def get_provisional_team_reconciliation(
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_provisional_teams(session=session)
    return Envelope(
        data=result,
        warnings=["1,810 team registrations lack team IDs in source data. Provisional groupings are ASSUMED and editable."],
    )


@router.get("/judges", response_model=Envelope[Dict[str, Any]])
def get_judges(
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = list_judges_and_slots(session=session)
    return Envelope(
        data=result,
        warnings=["Source pack provides zero judge data. Unassigned judge slots are shown as explicit gaps."],
    )


@router.post("/judges", response_model=Envelope[Dict[str, Any]])
def create_judge(
    body: JudgeCreateBody,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    judge_data = register_judge(
        session=session,
        name=body.name,
        email=body.email,
        phone=body.phone,
        college_affiliation=body.college_affiliation,
        expert_events=body.expert_events,
        notes=body.notes,
    )
    return Envelope(data=judge_data)


@router.get("/{event_id}", response_model=Envelope[Dict[str, Any]])
def get_event(
    event_id: str,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    profile = get_event_profile(session=session, event_id=event_id)
    return Envelope(data=profile)


@router.get("/{event_id}/registrations", response_model=Envelope[Dict[str, Any]])
def get_registrations(
    event_id: str,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    regs = get_event_registrations(session=session, event_id=event_id)
    return Envelope(data=regs)


@router.post("", response_model=Envelope[Dict[str, Any]])
def create_event(
    body: EventMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    event_id = body.payload.get("id") or f"E{uuid.uuid4().hex[:4].upper()}"
    req = ChangeRequest(
        action="event.create",
        entity_type="event",
        entity_id=event_id,
        payload=body.payload,
        reason=body.reason or "Create event",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.put("/{event_id}", response_model=Envelope[Dict[str, Any]])
def update_event(
    event_id: str,
    body: EventMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="event.update",
        entity_type="event",
        entity_id=event_id,
        payload=body.payload,
        reason=body.reason or "Update event",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.post("/{event_id}/cancel", response_model=Envelope[Dict[str, Any]])
def cancel_event(
    event_id: str,
    body: EventMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="event.cancel",
        entity_type="event",
        entity_id=event_id,
        payload=body.payload,
        reason=body.reason or "Cancel event",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.post("/{event_id}/merge", response_model=Envelope[Dict[str, Any]])
def merge_event(
    event_id: str,
    body: EventMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="event.merge",
        entity_type="event",
        entity_id=event_id,
        payload=body.payload,
        reason=body.reason or "Merge events",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.post("/{event_id}/extend-duration", response_model=Envelope[Dict[str, Any]])
def extend_event_duration(
    event_id: str,
    body: EventMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="event.extend_duration",
        entity_type="event",
        entity_id=event_id,
        payload=body.payload,
        reason=body.reason or "Extend event duration",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())
