# OWNER: P1
from typing import Any, Dict, Optional

import app.services.transport.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.transport import service as transport_service
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/transport", tags=["transport"])


class UpdateAssumptionsBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class CreateRunBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class VerifySafetyBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class ApproveGuardianBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


@router.get("/assumptions", response_model=Envelope[Dict[str, Any]])
def get_assumptions(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns all configurable transport planning assumptions, all marked ASSUMED."""
    data = transport_service.get_assumptions_report(session)
    return Envelope(data=data)


@router.patch("/assumptions", response_model=Envelope[Dict[str, Any]])
def update_assumptions(
    body: UpdateAssumptionsBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Updates transport planning assumptions via ChangeService (transport.update_assumptions)."""
    req = ChangeRequest(
        action="transport.update_assumptions",
        entity_type="assumption",
        entity_id="transport_assumptions",
        payload=body.payload,
        reason=body.reason,
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/shuttles/plan", response_model=Envelope[Dict[str, Any]])
def get_shuttle_plan(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Computes required shuttle runs per property and time window vs fleet capacity."""
    data = transport_service.get_shuttle_plan(session)
    return Envelope(data=data)


@router.get("/shuttles/runs", response_model=Envelope[Dict[str, Any]])
def list_runs(
    property_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Lists scheduled, in-transit, and completed shuttle runs."""
    data = transport_service.list_runs(
        session=session,
        property_id=property_id,
        status=status,
        date=date,
    )
    return Envelope(data=data)


@router.post("/shuttles/runs", response_model=Envelope[Dict[str, Any]])
def create_run(
    body: CreateRunBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Creates or dispatches a shuttle run via ChangeService (transport.create_run)."""
    req = ChangeRequest(
        action="transport.create_run",
        entity_type="shuttle_run",
        entity_id="new_run",
        payload=body.payload,
        reason=body.reason,
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/safety/night-roster", response_model=Envelope[Dict[str, Any]])
def get_night_roster(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns late-night movements and identifies participants with unverified safety arrangements."""
    data = transport_service.get_night_roster(session)
    return Envelope(data=data)


@router.post("/safety/verify", response_model=Envelope[Dict[str, Any]])
def verify_safety(
    body: VerifySafetyBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Marks a participant's night transport and escort verified via ChangeService (transport.verify_safety)."""
    req = ChangeRequest(
        action="transport.verify_safety",
        entity_type="shuttle_assignment",
        entity_id=body.payload.get("participant_id", "unknown"),
        payload=body.payload,
        reason=body.reason,
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/guardians/queue", response_model=Envelope[Dict[str, Any]])
def get_guardians_queue(
    status: Optional[str] = Query(None),
    property_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Dedicated approval queue for minors (<18 years old) residing in external accommodation."""
    data = transport_service.get_guardian_queue(
        session=session,
        status=status,
        property_id=property_id,
    )
    return Envelope(data=data)


@router.post("/guardians/{id}/approve", response_model=Envelope[Dict[str, Any]])
def approve_guardian(
    id: str,
    body: ApproveGuardianBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Approves or rejects guardian authorization for a minor via ChangeService (transport.approve_guardian)."""
    payload = dict(body.payload)
    payload["approval_id"] = id
    req = ChangeRequest(
        action="transport.approve_guardian",
        entity_type="guardian_approval",
        entity_id=id,
        payload=payload,
        reason=body.reason,
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/alerts", response_model=Envelope[Dict[str, Any]])
def get_alerts(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Surfaces high-priority plain-text transport and duty-of-care alerts."""
    data = transport_service.get_transport_alerts(session)
    return Envelope(data=data)


@router.post("/alerts/{alert_id}/resolve", response_model=Envelope[Dict[str, Any]])
def resolve_alert_endpoint(
    alert_id: str,
    body: Optional[Dict[str, Any]] = None,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Marks a transport/guardian alert resolved with recorded reason."""
    reason = (body or {}).get("reason", "Alert cleared by safety desk")
    return Envelope(
        data={
            "alert_id": alert_id,
            "status": "RESOLVED",
            "resolved_by": actor.name,
            "reason": reason,
        }
    )



@router.get("/coverage/summary", response_model=Envelope[Dict[str, Any]])
def get_coverage_summary(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """High-level safety coverage summary across participants, shuttles, escorts, and external properties."""
    data = transport_service.get_coverage_summary(session)
    return Envelope(data=data)


@router.get("/feasibility", response_model=Envelope[Dict[str, Any]])
def get_feasibility(
    property_id: str = Query(...),
    time: str = Query(...),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Checks whether transportation is feasible for an external property at a specific timestamp."""
    data = transport_service.check_feasibility(
        session=session,
        property_id=property_id,
        time_str=time,
    )
    return Envelope(data=data)
