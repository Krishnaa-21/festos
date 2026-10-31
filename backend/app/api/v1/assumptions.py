# OWNER: P2
from typing import List, Optional

from app.core.change_service import ChangeRequest, ChangeResult, execute_change
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.assumptions import (
    AssumptionDependentsResponse,
    AssumptionHistoryResponse,
    AssumptionItem,
    AssumptionUpdateRequest,
)
from app.schemas.common import Actor, Envelope
from app.services.assumptions.service import (
    get_assumption_dependents,
    get_assumption_detail,
    get_assumption_history,
    list_assumptions,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session

router = APIRouter(prefix="/assumptions", tags=["Assumptions"])


@router.get("", response_model=Envelope[List[AssumptionItem]])
def get_assumptions(
    owner: Optional[str] = Query(None, description="Filter by owner (P1, P2)"),
    q: Optional[str] = Query(None, description="Search term for key, reason or impact"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Lists all system operational assumptions, sources, reasons, and typed values."""
    items = list_assumptions(session=session, owner=owner, q=q)
    return Envelope(data=items, meta={"total": len(items)})


@router.put("", response_model=Envelope[ChangeResult])
def put_update_assumption(
    body: AssumptionUpdateRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Mutates an assumption through ChangeService handler assumptions.update.
    Audited, validates typed value, and invalidates in-memory cache.
    """
    req = ChangeRequest(
        action="assumptions.update",
        entity_type="assumption",
        entity_id=body.key or "unknown",
        payload={"key": body.key, "value": body.value, "new_value": body.value},
        reason=body.reason,
        actor=actor,
        dry_run=body.dry_run,
        expected_version=body.expected_version,
    )
    result = execute_change(req, session)
    return Envelope(
        data=result,
        meta={"key": body.key, "idempotency_key": idempotency_key},
        warnings=result.warnings,
    )


@router.get("/{key}", response_model=Envelope[AssumptionItem])
def get_assumption_by_key(
    key: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Fetches details of a specific assumption key."""
    item = get_assumption_detail(session=session, key=key)
    if not item:
        raise HTTPException(status_code=404, detail=f"Assumption '{key}' not found")
    return Envelope(data=item)


@router.put("/{key}", response_model=Envelope[ChangeResult])
@router.patch("/{key}", response_model=Envelope[ChangeResult])
def put_update_assumption_by_key(
    key: str,
    body: AssumptionUpdateRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Mutates a specific assumption through ChangeService handler assumptions.update."""
    req = ChangeRequest(
        action="assumptions.update",
        entity_type="assumption",
        entity_id=key,
        payload={"key": key, "value": body.value, "new_value": body.value},
        reason=body.reason,
        actor=actor,
        dry_run=body.dry_run,
        expected_version=body.expected_version,
    )
    result = execute_change(req, session)
    return Envelope(
        data=result,
        meta={"key": key, "idempotency_key": idempotency_key},
        warnings=result.warnings,
    )


@router.get("/{key}/history", response_model=Envelope[AssumptionHistoryResponse])
def get_assumption_change_history(
    key: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Fetches audit history and prior values for a specific assumption key."""
    history = get_assumption_history(session=session, key=key)

    return Envelope(data=AssumptionHistoryResponse(key=key, history=history))


@router.get("/{key}/dependents", response_model=Envelope[AssumptionDependentsResponse])
def get_assumption_module_dependents(
    key: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Previews which system modules and planning engines read this assumption key."""
    dependents_data = get_assumption_dependents(session=session, key=key)
    return Envelope(data=dependents_data)
