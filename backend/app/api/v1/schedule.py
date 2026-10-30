# OWNER: P1
"""API router for Schedule generation, versioning, sessions, conflict detection, resolutions, and Gantt timeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import app.services.schedule.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.schedule.service import (
    generate_schedule,
    get_conflict_resolutions,
    get_schedule_version,
    get_timeline,
    get_unscheduled_report,
    list_conflicts,
    list_schedule_versions,
    list_sessions,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/schedule", tags=["Schedule"])


class ScheduleGenerateBody(BaseModel):
    plan_name: str = "Plan Alpha - ASSUMED"
    solver: str = "greedy"
    include_late_wave: bool = True
    wildcard_finals: bool = False
    reason: Optional[str] = "Generated schedule plan"


class ScheduleRestoreBody(BaseModel):
    reason: Optional[str] = "Restored schedule version"


class SessionMoveBody(BaseModel):
    new_start_at: str
    reason: Optional[str] = "Moved session time"
    expected_version: Optional[int] = None


class SessionChangeVenueBody(BaseModel):
    new_venue_id: str
    reason: Optional[str] = "Changed session venue"
    expected_version: Optional[int] = None


class ConflictResolutionApplyBody(BaseModel):
    action: str  # schedule.move_session | schedule.change_venue | event.cancel
    payload: Dict[str, Any]
    reason: Optional[str] = "Applied ranked resolution"


def _get_actor(
    x_actor_role: Optional[str] = Header("EVENT_LEAD"),
    x_actor_id: Optional[str] = Header("usr_scheduler"),
) -> Actor:
    return Actor(id=x_actor_id or "usr_scheduler", role=x_actor_role or "EVENT_LEAD", name="Schedule Manager")


@router.post("/generate", response_model=Envelope[Dict[str, Any]])
def post_generate_schedule(
    body: ScheduleGenerateBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = generate_schedule(
        session=session,
        plan_name=body.plan_name,
        solver=body.solver,
        include_late_wave=body.include_late_wave,
        wildcard_finals=body.wildcard_finals,
        actor_id=actor.id,
    )
    return Envelope(
        data=result,
        warnings=[
            "Schedule is labelled ASSUMED. Raw data contains no event times or venue assignments.",
            f"{result['unscheduled_registrations']} entrants unscheduled due to arrival window limits or personal clashes.",
        ],
    )


@router.get("/versions", response_model=Envelope[Dict[str, Any]])
def get_versions(
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = list_schedule_versions(session=session)
    return Envelope(data=result)


@router.get("/versions/{version_id}", response_model=Envelope[Dict[str, Any]])
def get_version(
    version_id: str,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_schedule_version(session=session, version_id=version_id)
    return Envelope(data=result)


@router.post("/versions/{version_id}/restore", response_model=Envelope[Dict[str, Any]])
def restore_version(
    version_id: str,
    body: ScheduleRestoreBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="schedule.restore_version",
        entity_type="schedule_version",
        entity_id=version_id,
        payload={},
        reason=body.reason or f"Restored version {version_id}",
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.get("/sessions", response_model=Envelope[Dict[str, Any]])
def get_sessions(
    event_id: Optional[str] = Query(None),
    venue_id: Optional[str] = Query(None),
    round: Optional[str] = Query(None, alias="round"),
    wave: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = list_sessions(session=session, event_id=event_id, venue_id=venue_id, round_name=round, wave=wave)
    return Envelope(data=result)


@router.post("/sessions/{session_id}/move", response_model=Envelope[Dict[str, Any]])
def move_session(
    session_id: str,
    body: SessionMoveBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="schedule.move_session",
        entity_type="event_session",
        entity_id=session_id,
        payload={"new_start_at": body.new_start_at},
        reason=body.reason or "Move session",
        actor=actor,
        expected_version=body.expected_version,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.post("/sessions/{session_id}/change-venue", response_model=Envelope[Dict[str, Any]])
def change_session_venue(
    session_id: str,
    body: SessionChangeVenueBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    req = ChangeRequest(
        action="schedule.change_venue",
        entity_type="event_session",
        entity_id=session_id,
        payload={"new_venue_id": body.new_venue_id},
        reason=body.reason or "Change venue",
        actor=actor,
        expected_version=body.expected_version,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.get("/conflicts", response_model=Envelope[Dict[str, Any]])
def get_conflicts(
    conflict_type: Optional[str] = Query(None),
    severity: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = list_conflicts(session=session, conflict_type=conflict_type, severity=severity, status=status)
    return Envelope(
        data=result,
        warnings=["Zero venue overlaps does not mean zero conflicts: all 10 types are checked."],
    )


@router.get("/conflicts/{conflict_id}/resolutions", response_model=Envelope[Dict[str, Any]])
def get_resolutions_for_conflict(
    conflict_id: str,
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_conflict_resolutions(session=session, conflict_id=conflict_id)
    return Envelope(data=result)


@router.post("/conflicts/{conflict_id}/apply-resolution", response_model=Envelope[Dict[str, Any]])
def apply_resolution(
    conflict_id: str,
    body: ConflictResolutionApplyBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    entity_id = body.payload.get("session_id") or body.payload.get("event_id") or conflict_id
    req = ChangeRequest(
        action=body.action,
        entity_type="event_session" if "session" in body.action else "event",
        entity_id=entity_id,
        payload=body.payload,
        reason=body.reason or f"Apply resolution for conflict {conflict_id}",
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONSTRAINT_VIOLATION", "violations": [v.model_dump() for v in res.violations]},
        )
    return Envelope(data=res.model_dump())


@router.get("/unscheduled", response_model=Envelope[Dict[str, Any]])
def get_unscheduled_entrants_endpoint(
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_unscheduled_report(session=session)
    return Envelope(
        data=result,
        warnings=["Never silently drop participants: all unscheduled registrations are tracked with explanations."],
    )


@router.get("/timeline", response_model=Envelope[Dict[str, Any]])
def get_gantt_timeline(
    from_time: Optional[datetime] = Query(None, alias="from"),
    to_time: Optional[datetime] = Query(None, alias="to"),
    session: Session = Depends(get_session),
) -> Envelope[Dict[str, Any]]:
    result = get_timeline(session=session, from_dt=from_time, to_dt=to_time)
    return Envelope(data=result)
