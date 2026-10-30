# OWNER: P1
"""API router for Participant Reconciliation, Waterfall, and Duplicate Resolution."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.reconciliation.service import (
    compare_participants,
    get_flags,
    get_merge_history,
    get_waterfall,
    keep_separate,
    list_duplicates,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


class MergeRequestBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class UndoMergeBody(BaseModel):
    reason: Optional[str] = None
    dry_run: bool = False


class KeepSeparateBody(BaseModel):
    candidate_id: str
    reason: str


def _get_actor(x_actor_role: Optional[str] = Header("FESTIVAL_DIRECTOR"), x_actor_id: Optional[str] = Header("usr_reconciler")) -> Actor:
    return Actor(id=x_actor_id or "usr_reconciler", role=x_actor_role or "FESTIVAL_DIRECTOR", name="Reconciliation Actor")


@router.get("/waterfall", response_model=Envelope[Dict[str, Any]])
def get_reconciliation_waterfall(
    session: Session = Depends(get_session),
):
    """Returns the comprehensive counts panel and reconciliation waterfall explaining numbers."""
    data = get_waterfall(session)
    warnings = data.pop("warnings", [])
    return Envelope(data=data, warnings=warnings)


@router.get("/duplicates", response_model=Envelope[Dict[str, Any]])
def get_duplicate_candidates(
    classification: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """List duplicate candidates filtered by confidence classification or status."""
    res = list_duplicates(
        session=session,
        classification=classification,
        status=status,
        page=page,
        page_size=page_size,
    )
    return Envelope(data=res)


@router.get("/compare", response_model=Envelope[Dict[str, Any]])
def get_duplicate_comparison(
    id1: str = Query(...),
    id2: str = Query(...),
    session: Session = Depends(get_session),
):
    """Side-by-side comparison of two participant records including registrations and claims."""
    comp = compare_participants(session, id1, id2)
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"One or both participants ({id1}, {id2}) not found.",
        )
    return Envelope(data=comp)


@router.post("/merge", response_model=Envelope[Any])
def merge_duplicate_participants(
    body: MergeRequestBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Merge duplicate participant into canonical participant via ChangeService.
    Blocks if both records hold conflicting merchandise claims.
    """
    canonical_id = body.payload.get("canonical_id")
    if not canonical_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="canonical_id is required in payload.")

    req = ChangeRequest(
        action="participant.merge",
        entity_type="participant",
        entity_id=canonical_id,
        payload=body.payload,
        reason=body.reason or f"Merged {body.payload.get('merged_id')} into {canonical_id}",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Merge rejected", "violations": [v.model_dump() for v in result.violations]},
        )
    resp_data = {
        "change_set_id": result.change_set_id,
        "status": result.status,
        **(result.data or {}),
    }
    return Envelope(data=resp_data, warnings=result.warnings)


@router.post("/undo-merge/{merge_id}", response_model=Envelope[Any])
def undo_merge_operation(
    merge_id: str,
    body: UndoMergeBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Reverts a merge operation, restoring byte-identical pre-merge state to both records."""
    req = ChangeRequest(
        action="participant.undo_merge",
        entity_type="merge_record",
        entity_id=merge_id,
        payload={"merge_id": merge_id},
        reason=body.reason or f"Reverted merge {merge_id}",
        actor=actor,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Undo merge rejected", "violations": [v.model_dump() for v in result.violations]},
        )
    resp_data = {
        "change_set_id": result.change_set_id,
        "status": "REVERTED" if result.status == "APPLIED" else result.status,
        **(result.data or {}),
    }
    return Envelope(data=resp_data, warnings=result.warnings)


@router.post("/keep-separate", response_model=Envelope[Dict[str, Any]])
def keep_separate_decision(
    body: KeepSeparateBody,
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Dismiss a candidate pair with a recorded reason not to merge."""
    try:
        res = keep_separate(session, body.candidate_id, body.reason, actor.id)
        return Envelope(data=res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/history", response_model=Envelope[Dict[str, Any]])
def get_merge_audit_history(
    session: Session = Depends(get_session),
):
    """Retrieve chronological merge and revert history."""
    records = get_merge_history(session)
    return Envelope(data={"merges": records})


@router.get("/flags", response_model=Envelope[Dict[str, Any]])
def get_operational_edge_case_flags(
    session: Session = Depends(get_session),
):
    """Returns operational edge-case flags (same name different people, leaders competing, staff as participants)."""
    flags = get_flags(session)
    return Envelope(data=flags)
