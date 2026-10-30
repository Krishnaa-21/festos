import threading
from typing import Any, Dict, List, Optional

import app.services.merchandise.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.errors import AlreadyIssuedError
from app.engines.merchandise import PureMerchandiseEngine
from app.schemas.common import Actor, Envelope
from app.services.merchandise import service as merch_service
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

_issue_lock = threading.Lock()

router = APIRouter(prefix="/merchandise", tags=["merchandise"])


class IssueItemBody(BaseModel):
    participant_id: str
    item_id: str
    counter_id: Optional[str] = "DESK_CENTRAL"
    size_override: Optional[str] = None
    reason: Optional[str] = "Registration desk kit handover"


class VoidClaimBody(BaseModel):
    claim_id: str
    reason: str
    return_to_awaiting_inspection: bool = True


class ScanQrBody(BaseModel):
    token: str
    counter_id: Optional[str] = "DESK_CENTRAL"
    auto_issue_items: Optional[List[str]] = None


class SyncOfflineBody(BaseModel):
    operations: List[Dict[str, Any]]


@router.get("/catalog", response_model=Envelope[Dict[str, Any]])
def get_catalog(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns merchandise catalog items with stock buckets."""
    data = merch_service.get_catalog(session)
    return Envelope(data=data)


@router.get("/policy", response_model=Envelope[Dict[str, Any]])
def get_policy(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns entitlement policy rules and size-wise demand vs stock analysis."""
    data = merch_service.get_policy_and_demand(session)
    return Envelope(data=data)


@router.post("/issue", response_model=Envelope[Dict[str, Any]])
def issue_item(
    body: IssueItemBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Issues merchandise to a canonical participant. Idempotent and atomic.
    Returns 409 ALREADY_ISSUED with original details if already claimed.
    """
    req = ChangeRequest(
        action="merchandise.issue",
        entity_type="merch_claim",
        entity_id=f"clm_{body.participant_id}_{body.item_id}",
        payload=body.model_dump(),
        reason=body.reason,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    with _issue_lock:
        try:
            res = execute_change(req, session)
        except Exception as exc:
            # Handle concurrent unique constraint collision
            if "UNIQUE constraint failed" in str(exc) or "database is locked" in str(exc):
                from app.models.inventory import MerchClaim
                from app.models.participants import Participant
                part = session.get(Participant, body.participant_id)
                canon_id = getattr(part, "canonical_id", None) or body.participant_id
                existing = session.exec(
                    select(MerchClaim).where(
                        MerchClaim.canonical_participant_id == canon_id,
                        MerchClaim.item_id == body.item_id,
                        MerchClaim.status != "VOIDED",
                    )
                ).first()
                if existing:
                    claimed_str = existing.claimed_at.isoformat() if existing.claimed_at else "previously"
                    raise AlreadyIssuedError(
                        message=f"Item already issued to participant at {claimed_str} by {existing.issued_by}",
                        details={"code": "ALREADY_ISSUED", "canonical_participant_id": canon_id, "item_id": body.item_id},
                    )
            raise exc

    if res.status == "REJECTED":
        # Check for ALREADY_ISSUED violation
        already_issued = next((v for v in res.violations if v.code == "ALREADY_ISSUED"), None)
        if already_issued:
            raise AlreadyIssuedError(
                message=already_issued.message,
                details=already_issued.model_dump(),
            )
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])

    data = res.data or {}
    if actor.role == "VOLUNTEER":
        data = PureMerchandiseEngine.mask_for_volunteer(data)

    return Envelope(data=data)


@router.post("/void", response_model=Envelope[Dict[str, Any]])
def void_claim(
    body: VoidClaimBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Voids an issued merch claim and returns item to awaiting_return. Requires approval."""
    req = ChangeRequest(
        action="merchandise.void",
        entity_type="merch_claim",
        entity_id=body.claim_id,
        payload=body.model_dump(),
        reason=body.reason,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/qr/{participant_id}", response_model=Envelope[Dict[str, Any]])
def get_qr(
    participant_id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns signed HMAC QR token, SVG graphic, and entitlement checklist."""
    data = merch_service.get_qr(session, participant_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Participant {participant_id} not found")
    return Envelope(data=data)


@router.post("/scan", response_model=Envelope[Dict[str, Any]])
def scan_qr(
    body: ScanQrBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Validates QR token and returns canonical participant entitlements.
    Volunteers receive minimal verification data.
    """
    data = merch_service.scan_qr(
        session=session,
        token=body.token,
        counter_id=body.counter_id or "DESK_CENTRAL",
        auto_issue_items=body.auto_issue_items,
        actor=actor,
    )
    if not data.get("valid"):
        raise HTTPException(status_code=400, detail=data.get("message", "Invalid token"))

    if actor.role == "VOLUNTEER":
        data = PureMerchandiseEngine.mask_for_volunteer(data)

    return Envelope(data=data)


@router.post("/sync", response_model=Envelope[Dict[str, Any]])
def sync_offline(
    body: SyncOfflineBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Batch synchronizes offline issuance operations keyed idempotently by client_op_id."""
    data = merch_service.sync_offline_batch(
        session=session,
        operations=body.operations,
        actor=actor,
    )
    return Envelope(data=data)
