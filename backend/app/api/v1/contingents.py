# OWNER: P1
"""API router for Contingent operations, status views, and profile management."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.contingents.service import (
    get_contingent,
    get_contingent_status,
    list_contingents,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/contingents", tags=["Contingents"])


class ContingentUpdateBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


def _get_actor(x_actor_role: Optional[str] = Header("VOLUNTEER"), x_actor_id: Optional[str] = Header("usr_anon")) -> Actor:
    return Actor(id=x_actor_id or "usr_anon", role=x_actor_role or "VOLUNTEER", name="API Actor")


@router.get("", response_model=Envelope[Dict[str, Any]])
def get_contingents_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    q: Optional[str] = Query(None),
    has_mismatch: Optional[bool] = Query(None),
    session: Session = Depends(get_session),
):
    """List all contingents with declared vs actual strength and leader/escort statuses."""
    res = list_contingents(
        session=session,
        page=page,
        page_size=page_size,
        q=q,
        has_mismatch=has_mismatch,
    )
    meta = res.pop("meta", {})
    return Envelope(data=res, meta=meta)


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_contingent_profile(
    id: str,
    session: Session = Depends(get_session),
):
    """Retrieve basic profile details for a contingent."""
    data = get_contingent(session, id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contingent {id} not found.")
    return Envelope(data=data)


@router.get("/{id}/status", response_model=Envelope[Dict[str, Any]])
def get_contingent_operational_status(
    id: str,
    session: Session = Depends(get_session),
):
    """Retrieve full operational view: attendance, travel windows, events, diet, merchandise, and housing."""
    data = get_contingent_status(session, id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contingent {id} not found.")
    warnings = data.pop("warnings", [])
    return Envelope(data=data, warnings=warnings)


@router.patch("/{id}", response_model=Envelope[Any])
def update_contingent_profile(
    id: str,
    body: ContingentUpdateBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Update contingent attributes through ChangeService."""
    req = ChangeRequest(
        action="contingent.update",
        entity_type="contingent",
        entity_id=id,
        payload=body.payload,
        reason=body.reason or f"Updated contingent {id} preferences/contact",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Contingent update rejected", "violations": [v.model_dump() for v in result.violations]},
        )
    return Envelope(data=result.model_dump(), warnings=result.warnings)
