# OWNER: P2 (P1 implementing field-verification parts)
"""API router for Unknown field verification queue, owner assignment, and token confirmation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.schemas.common import Actor, Envelope
from app.services.unknowns.service import (
    confirm_token_submission,
    generate_confirmation_token,
    get_field_history,
    get_unknown_queue,
    list_unknown_items,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/unknowns", tags=["Unknowns"])


class VerifyFieldBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class GenerateTokenBody(BaseModel):
    entity_type: str = "participant"
    entity_id: str
    field: str
    expires_in_minutes: int = 1440
    recipient_role: str = "LEADER"


class TokenConfirmBody(BaseModel):
    value: str
    source: str = "LEADER_TOKEN_SUBMISSION"
    comment: Optional[str] = None


def _get_actor(x_actor_role: Optional[str] = Header("VOLUNTEER"), x_actor_id: Optional[str] = Header("usr_anon")) -> Actor:
    return Actor(id=x_actor_id or "usr_anon", role=x_actor_role or "VOLUNTEER", name="API Actor")


@router.get("/queue", response_model=Envelope[Dict[str, Any]])
def get_verification_queue(
    session: Session = Depends(get_session),
):
    """Retrieve the operational unknown fields queue ranked by Count x Criticality."""
    res = get_unknown_queue(session)
    return Envelope(data=res)


@router.get("/items", response_model=Envelope[Dict[str, Any]])
def get_unknown_field_items(
    field: str = Query(...),
    contingent_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Query individual participant records that have an UNKNOWN value for a specific field."""
    try:
        res = list_unknown_items(
            session=session,
            field=field,
            contingent_id=contingent_id,
            page=page,
            page_size=page_size,
        )
        return Envelope(data=res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify", response_model=Envelope[Any])
def verify_field_value(
    body: VerifyFieldBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    actor: Actor = Depends(_get_actor),
    session: Session = Depends(get_session),
):
    """Record a verified field value through ChangeService."""
    req = ChangeRequest(
        action="unknowns.verify_field",
        entity_type=body.payload.get("entity_type", "participant"),
        entity_id=body.payload.get("entity_id", ""),
        payload=body.payload,
        reason=body.reason or f"Verified field {body.payload.get('field')}",
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Verification rejected", "violations": [v.model_dump() for v in result.violations]},
        )
    return Envelope(data=result.model_dump(), warnings=result.warnings)


@router.post("/token", response_model=Envelope[Dict[str, Any]])
def create_field_confirmation_token(
    body: GenerateTokenBody,
):
    """Issue a cryptographically signed, field-scoped expiring confirmation token."""
    res = generate_confirmation_token(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        field=body.field,
        expires_in_minutes=body.expires_in_minutes,
        role=body.recipient_role,
    )
    return Envelope(data=res)


@router.post("/confirm/{token}", response_model=Envelope[Dict[str, Any]])
def submit_token_confirmation(
    token: str,
    body: TokenConfirmBody,
    session: Session = Depends(get_session),
):
    """Public / semi-public endpoint to submit verified field value using signed token."""
    try:
        res = confirm_token_submission(
            session=session,
            token=token,
            value=body.value,
            source=body.source,
            comment=body.comment,
        )
        return Envelope(data=res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history/{entity_type}/{entity_id}/{field}", response_model=Envelope[Dict[str, Any]])
def get_verification_history_for_field(
    entity_type: str,
    entity_id: str,
    field: str,
    session: Session = Depends(get_session),
):
    """Retrieve chronological field verification history for an entity."""
    history = get_field_history(session, entity_type, entity_id, field)
    return Envelope(data={"entity_type": entity_type, "entity_id": entity_id, "field": field, "verifications": history})


class BatchConfirmationRequestBody(BaseModel):
    target_type: str = "CONTINGENT_LEADER"
    contingent_id: Optional[str] = None
    group_id: Optional[str] = "housing_gender"
    expires_in_minutes: int = 1440


@router.get("/ranking", response_model=Envelope[Dict[str, Any]])
def get_value_of_information_ranking(
    session: Session = Depends(get_session),
):
    """Value-of-Information (VOI) ranking across unknown field groups.
    Simulates sandbox outcomes and ranks groups by operational improvement per confirmation.
    """
    from app.services.unknowns.service import get_voi_ranking
    res = get_voi_ranking(session)
    return Envelope(data=res)


@router.post("/confirmation-requests", response_model=Envelope[Dict[str, Any]])
def create_batched_confirmation_request(
    body: BatchConfirmationRequestBody,
    session: Session = Depends(get_session),
):
    """Generate minimal confirmation requests batched by contingent leader or desk volunteer."""
    from app.services.unknowns.service import generate_batch_confirmation_request
    res = generate_batch_confirmation_request(
        session=session,
        target_type=body.target_type,
        contingent_id=body.contingent_id,
        group_id=body.group_id,
        expires_in_minutes=body.expires_in_minutes,
    )
    return Envelope(data=res)


@router.get("/why-not/{participant_id}", response_model=Envelope[Dict[str, Any]])
def get_participant_why_not_explanation(
    participant_id: str,
    session: Session = Depends(get_session),
):
    """Diagnostic explanation extending Why-Not with simulated counterfactual predictions:
    'What confirming field X would change for this participant'.
    """
    from app.services.unknowns.service import get_why_not_counterfactuals
    try:
        res = get_why_not_counterfactuals(session, participant_id)
        return Envelope(data=res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
