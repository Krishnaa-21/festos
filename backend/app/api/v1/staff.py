# OWNER: P1
from typing import Any, Dict, List, Optional

import app.services.staff.handlers  # noqa: F401
from app.core.clock import now
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.staff import service as staff_service
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/staff", tags=["staff"])


class AssignShiftBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class ReplaceShiftBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_staff(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    role: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    skill: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List staff profiles with roles, shift bands, skills, and status."""
    data = staff_service.list_staff(
        session=session,
        page=page,
        page_size=page_size,
        role=role,
        shift=shift,
        skill=skill,
        q=q,
    )
    return Envelope(data=data)


@router.get("/shifts", response_model=Envelope[Dict[str, Any]])
def list_shifts(
    staff_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    venue_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List scheduled shifts and venue assignments."""
    data = staff_service.list_shifts(
        session=session,
        staff_id=staff_id,
        session_id=session_id,
        venue_id=venue_id,
        date=date,
        status=status,
    )
    return Envelope(data=data)


@router.post("/shifts/assign", response_model=Envelope[Dict[str, Any]])
def assign_shift(
    body: AssignShiftBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Assign a staff member to a shift or session via ChangeService (staff.assign)."""
    req = ChangeRequest(
        action="staff.assign",
        entity_type="shift",
        entity_id=body.payload.get("staff_id", "new"),
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


@router.post("/shifts/{id}/replace", response_model=Envelope[Dict[str, Any]])
def replace_shift(
    id: str,
    body: ReplaceShiftBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Emergency replacement of an assigned staff member via ChangeService (staff.replace).

    A handover note is strictly enforced.
    """
    payload = dict(body.payload)
    payload["shift_id"] = id
    req = ChangeRequest(
        action="staff.replace",
        entity_type="shift",
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


@router.get("/demand", response_model=Envelope[Dict[str, Any]])
def get_demand(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Calculates volunteer requirement demand over time and uncovered gaps."""
    data = staff_service.get_demand_report(session)
    return Envelope(data=data)


@router.get("/overloaded", response_model=Envelope[Dict[str, Any]])
def get_overloaded(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns staff members exceeding daily maximum or consecutive hours."""
    data = staff_service.get_overloaded_report(session)
    return Envelope(data=data)


@router.get("/conflicts", response_model=Envelope[Dict[str, Any]])
def get_conflicts(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Surfaces dual roles, self-escort conflicts, and shift overlaps."""
    data = staff_service.get_conflicts_report(session)
    return Envelope(data=data)


@router.get("/replacements/suggest", response_model=Envelope[Dict[str, Any]])
def suggest_replacements(
    venue_id: str = Query(...),
    start_at: str = Query(...),
    end_at: str = Query(...),
    role_required: Optional[str] = Query(None),
    shift_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Suggests ranked replacement candidates for a shift window."""
    data = staff_service.suggest_replacements(
        session=session,
        venue_id=venue_id,
        start_at=start_at,
        end_at=end_at,
        role_required=role_required,
        shift_id=shift_id,
    )
    return Envelope(data=data)


@router.get("/reports/staff-coverage")
def get_staff_coverage_report(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Generates downloadable CSV report for staff coverage and gap analysis."""
    csv_content = staff_service.generate_staff_coverage_csv(session)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=staff_coverage.csv"},
    )


_HANDOVER_NOTES: List[Dict[str, Any]] = [
    {
        "id": "hnd_001",
        "venueId": "VEN-001",
        "venueName": "Main Auditorium",
        "hour": "14:00",
        "outgoingStaffName": "Aarav Sharma",
        "incomingStaffName": "Neha Verma",
        "notes": "Stage lighting tested. Backup cordless mic on lectern B.",
        "timestamp": "2026-10-31T14:05:00Z",
        "isMissing": False,
        "acknowledgedByIncoming": True,
    },
    {
        "id": "hnd_002",
        "venueId": "VEN-002",
        "venueName": "Management Courtyard",
        "hour": "16:00",
        "outgoingStaffName": "Rohan Das",
        "incomingStaffName": "Pooja Patel",
        "notes": "Crowd flow brisk. First aid kit replenished at security desk.",
        "timestamp": "2026-10-31T16:02:00Z",
        "isMissing": False,
        "acknowledgedByIncoming": True,
    },
]


@router.get("/handovers", response_model=Envelope[Dict[str, Any]])
def get_handovers_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List shift handover records between outgoing and incoming duty staff."""
    missing = sum(1 for h in _HANDOVER_NOTES if h.get("isMissing"))
    return Envelope(
        data={
            "items": _HANDOVER_NOTES,
            "total": len(_HANDOVER_NOTES),
            "missing_count": missing,
        }
    )


@router.post("/handovers", response_model=Envelope[Dict[str, Any]])
def create_handover_endpoint(
    body: Dict[str, Any],
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Record a shift handover note and transfer operational custody."""
    new_note = {
        "id": f"hnd_{len(_HANDOVER_NOTES) + 1:03d}",
        "venueId": body.get("venue_id", "VEN-001"),
        "venueName": "Designated Venue",
        "hour": body.get("hour", "Now"),
        "outgoingStaffName": actor.name or "On-Duty Volunteer",
        "incomingStaffName": "Incoming Relief",
        "notes": body.get("notes", ""),
        "timestamp": now().isoformat(),
        "isMissing": False,
        "acknowledgedByIncoming": True,
    }
    _HANDOVER_NOTES.insert(0, new_note)
    return Envelope(data=new_note)


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_staff(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns detailed staff profile, active assignments, and workload metrics."""
    data = staff_service.get_staff(session, id)
    if not data:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return Envelope(data=data)
