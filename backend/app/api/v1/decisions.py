# OWNER: P1
from typing import Any, Dict, List, Optional

from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.decisions import service as decisions_service
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/decisions", tags=["decisions"])


class CreateDecisionBody(BaseModel):
    module: str
    decision_type: str
    title: str
    summary: str
    why: str
    hard_constraints_satisfied: Optional[List[str]] = None
    soft_constraints_relaxed: Optional[List[Dict[str, Any]]] = None
    alternatives_rejected: Optional[List[Dict[str, Any]]] = None
    cost_impact_inr: float = 0.0
    people_affected: int = 0
    override_id: Optional[str] = None
    entity_refs: Optional[List[Dict[str, Any]]] = None


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_decisions(
    module: Optional[str] = Query(None),
    approver: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Lists recorded decision cards with filters by module, approver, and date range."""
    data = decisions_service.list_decisions(
        session=session,
        module=module,
        approver=approver,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return Envelope(data=data)


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_decision(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns complete details of a specific decision card."""
    data = decisions_service.get_decision(session, id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Decision card '{id}' not found")
    return Envelope(data=data)


@router.get("/{id}/why", response_model=Envelope[Dict[str, Any]])
def get_why_explanation(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """One-click explainability breakdown for a decision."""
    data = decisions_service.get_why_explanation(session, id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Decision card '{id}' not found")
    return Envelope(data=data)


@router.post("", response_model=Envelope[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
def create_decision(
    body: CreateDecisionBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Creates and persists a new decision card."""
    card = decisions_service.create_decision(
        session=session,
        payload=body.model_dump(),
        actor_id=actor.id,
    )
    session.commit()
    return Envelope(data={"id": card.id, "status": "RECORDED"})
