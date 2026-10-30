# OWNER: P1
"""API router for Venues, travel times, and venue-event compatibility mapping."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import app.services.venues.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.venues.service import (
    get_compatibility_mapping,
    get_travel_times,
    get_venue_profile,
    list_venues,
    set_travel_time,
    update_compatibility_mapping,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session

router = APIRouter(prefix="/venues", tags=["Venues"])


class VenueMutationBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)


class TravelTimeUpdateBody(BaseModel):
    from_venue_id: str
    to_venue_id: str
    travel_time_min: int


class CompatibilityUpdateBody(BaseModel):
    requirement_key: str
    venue_ids: List[str]
    reason: Optional[str] = None


def _get_actor(
    x_actor_role: Optional[str] = Header("LOGISTICS_MANAGER"),
    x_actor_id: Optional[str] = Header("usr_logistics"),
) -> Actor:
    return Actor(id=x_actor_id or "usr_logistics", role=x_actor_role or "LOGISTICS_MANAGER", name="Logistics Manager")


@router.get("", response_model=Envelope[Dict[str, Any]])
def get_all_venues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    indoor_outdoor: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = list_venues(session=session, page=page, page_size=page_size, indoor_outdoor=indoor_outdoor)
    return Envelope(data=result)


@router.get("/travel-times", response_model=Envelope[Dict[str, Any]])
def get_all_travel_times(
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_travel_times(session=session)
    return Envelope(data=result)


@router.put("/travel-times", response_model=Envelope[Dict[str, Any]])
def update_travel_time(
    body: TravelTimeUpdateBody,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = set_travel_time(
        session=session,
        from_venue_id=body.from_venue_id,
        to_venue_id=body.to_venue_id,
        travel_time_min=body.travel_time_min,
    )
    return Envelope(data=result)


@router.get("/compatibility", response_model=Envelope[Dict[str, Any]])
def get_venue_event_compatibility() -> Envelope[Dict[str, Any]]:
    result = get_compatibility_mapping()
    return Envelope(
        data=result,
        warnings=["Venue-event compatibility is ASSUMED because raw dataset contains no explicit venue assignments."],
    )


@router.put("/compatibility", response_model=Envelope[Dict[str, Any]])
def set_venue_event_compatibility(
    body: CompatibilityUpdateBody,
) -> Envelope[Dict[str, Any]]:
    result = update_compatibility_mapping(
        requirement_key=body.requirement_key,
        venue_ids=body.venue_ids,
    )
    return Envelope(data=result)


@router.get("/{venue_id}", response_model=Envelope[Dict[str, Any]])
def get_venue(
    venue_id: str,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_venue_profile(session=session, venue_id=venue_id)
    return Envelope(data=result)


@router.post("", response_model=Envelope[Dict[str, Any]])
def create_venue(
    body: VenueMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    venue_id = body.payload.get("id") or f"V{uuid.uuid4().hex[:4].upper()}"
    req = ChangeRequest(
        action="venue.create",
        entity_type="venue",
        entity_id=venue_id,
        payload=body.payload,
        reason=body.reason or "Create venue",
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


@router.put("/{venue_id}", response_model=Envelope[Dict[str, Any]])
def update_venue(
    venue_id: str,
    body: VenueMutationBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="venue.update",
        entity_type="venue",
        entity_id=venue_id,
        payload=body.payload,
        reason=body.reason or "Update venue",
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
