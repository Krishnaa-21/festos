# OWNER: P3
from typing import Any, Dict, Optional

import app.core.approvals as approvals_core
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.errors import NotFoundError
from app.models.audit import Approval
from app.models.change import ChangeSet
from app.schemas.common import Actor, Envelope, Page
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select

router = APIRouter(prefix="/approvals", tags=["Approvals"])


class DecisionRequest(BaseModel):
    reason: str = Field(..., description="Mandatory operational justification")


@router.get("", response_model=Envelope[Page[Dict[str, Any]]])
def list_approvals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    required_role: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """List operational approvals inbox with filtering and pagination."""
    query = select(Approval)

    if status:
        query = query.where(Approval.status == status)
    if entity_type:
        query = query.where(Approval.entity_type == entity_type)
    if required_role:
        query = query.where(Approval.required_role == required_role)

    total = session.exec(select(func.count()).select_from(Approval).where(*query._where_criteria)).one()

    items = session.exec(
        query.order_by(Approval.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    formatted_items = []
    for item in items:
        # Load change set summary if present
        payload_preview = None
        if item.change_set_id:
            cs = session.get(ChangeSet, item.change_set_id)
            if cs:
                payload_preview = cs.payload

        formatted_items.append({
            "id": item.id,
            "change_set_id": item.change_set_id,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "status": item.status,
            "required_role": item.required_role,
            "requested_by": item.requested_by,
            "reason": item.reason,
            "risk_kind": item.risk_kind,
            "approved_by": item.approved_by,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
            "rejection_reason": item.rejection_reason,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "payload_preview": payload_preview
        })

    page_data = Page.create(
        items=formatted_items,
        total=total,
        page=page,
        page_size=page_size
    )

    return Envelope(data=page_data)


@router.get("/policies", response_model=Envelope[Dict[str, Any]])
def get_approval_policies(
    actor: Actor = Depends(get_actor)
):
    """Retrieve risk-to-role operational approval policy definitions."""
    return Envelope(
        data={
            "policies": [
                {
                    "risk_kind": k,
                    "description": v["description"],
                    "required_roles": v["required_roles"],
                    "reason_mandatory": v["reason_mandatory"]
                }
                for k, v in approvals_core.APPROVAL_POLICIES.items()
            ]
        }
    )


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_approval_detail(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """Retrieve complete approval details including stored ChangeSet payload."""
    approval = session.get(Approval, id)
    if not approval:
        raise NotFoundError(f"Approval request '{id}' not found")

    payload = None
    if approval.change_set_id:
        cs = session.get(ChangeSet, approval.change_set_id)
        if cs:
            payload = cs.payload

    return Envelope(
        data={
            "id": approval.id,
            "change_set_id": approval.change_set_id,
            "entity_type": approval.entity_type,
            "entity_id": approval.entity_id,
            "status": approval.status,
            "required_role": approval.required_role,
            "requested_by": approval.requested_by,
            "reason": approval.reason,
            "risk_kind": approval.risk_kind,
            "approved_by": approval.approved_by,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "rejection_reason": approval.rejection_reason,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
            "payload": payload
        }
    )


@router.post("/{id}/approve", response_model=Envelope[Dict[str, Any]])
def post_approve(
    id: str,
    body: DecisionRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """Approve a pending operational change and execute the stored mutation."""
    result = approvals_core.approve_request(
        session=session,
        approval_id=id,
        actor=actor,
        reason=body.reason
    )
    return Envelope(
        data=result,
        warnings=["Approval signed off. ChangeSet successfully executed and audited."]
    )


@router.post("/{id}/reject", response_model=Envelope[Dict[str, Any]])
def post_reject(
    id: str,
    body: DecisionRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor)
):
    """Reject a pending operational change with a mandatory recorded explanation."""
    result = approvals_core.reject_request(
        session=session,
        approval_id=id,
        actor=actor,
        reason=body.reason
    )
    return Envelope(
        data=result,
        warnings=["Change rejected and logged in immutable audit register."]
    )
