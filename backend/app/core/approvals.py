# OWNER: P3
import uuid
from typing import Any, Dict

from sqlmodel import Session

import app.core.audit as audit_module
from app.core.clock import now
from app.core.errors import FestOSError, ForbiddenError, NotFoundError
from app.core.registry import get_change_handler
from app.models.audit import Approval
from app.models.change import ChangeSet
from app.schemas.common import Actor, Role

APPROVAL_POLICIES = {
    "HIGH_RISK_OVERRIDE": {
        "required_roles": [Role.FESTIVAL_DIRECTOR.value],
        "reason_mandatory": True,
        "description": "Hard constraint relaxation (accessibility, safety, privacy)"
    },
    "FINANCIAL_THRESHOLD": {
        "required_roles": [Role.FINANCE_MANAGER.value, Role.FESTIVAL_DIRECTOR.value],
        "reason_mandatory": True,
        "description": "Operational expenditures exceeding threshold"
    },
    "LATE_ARRIVAL_WAVE": {
        "required_roles": [Role.FESTIVAL_DIRECTOR.value],
        "reason_mandatory": True,
        "description": "Admitting off-window contingent arrivals"
    },
    "DEFAULT_HIGH_RISK": {
        "required_roles": [Role.FESTIVAL_DIRECTOR.value],
        "reason_mandatory": True,
        "description": "Standard high-risk change requiring operational sign-off"
    }
}


def require(
    session: Session,
    change_req: Any,
    change_set_id: str,
    risk_kind: str = "DEFAULT_HIGH_RISK"
) -> Approval:
    """Create an Approval record linked to a pending ChangeSet."""
    policy = APPROVAL_POLICIES.get(risk_kind, APPROVAL_POLICIES["DEFAULT_HIGH_RISK"])
    required_role = policy["required_roles"][0]

    approval_id = f"app_{uuid.uuid4().hex[:8]}"
    approval = Approval(
        id=approval_id,
        change_set_id=change_set_id,
        entity_type=change_req.entity_type,
        entity_id=change_req.entity_id,
        status="PENDING",
        required_role=required_role,
        requested_by=getattr(change_req.actor, "id", str(change_req.actor)),
        reason=change_req.reason,
        risk_kind=risk_kind,
        created_at=now()
    )
    session.add(approval)
    session.flush()

    audit_module.record(
        session=session,
        actor=change_req.actor,
        action="approval.requested",
        entity_type=change_req.entity_type,
        entity_id=change_req.entity_id,
        before={},
        after={
            "approval_id": approval_id,
            "change_set_id": change_set_id,
            "required_role": required_role,
            "risk_kind": risk_kind
        },
        reason=change_req.reason,
        status="SUCCESS",
        approval_id=approval_id
    )

    return approval


def approve_request(
    session: Session,
    approval_id: str,
    actor: Actor,
    reason: str
) -> Dict[str, Any]:
    """Approve a pending request, executing the stored ChangeSet mutation and auditing the event."""
    if not reason or not reason.strip():
        raise FestOSError(
            message="Approval requires a mandatory recorded reason.",
            code="VALIDATION_ERROR",
            status_code=422
        )

    approval = session.get(Approval, approval_id)
    if not approval:
        raise NotFoundError(f"Approval request '{approval_id}' not found")

    if approval.status != "PENDING":
        raise FestOSError(
            message=f"Approval request is already {approval.status}",
            code="VERSION_CONFLICT",
            status_code=409
        )

    # Validate approver role
    policy = APPROVAL_POLICIES.get(approval.risk_kind or "DEFAULT_HIGH_RISK", APPROVAL_POLICIES["DEFAULT_HIGH_RISK"])
    allowed_roles = policy["required_roles"]
    if actor.role not in allowed_roles and actor.role not in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]:
        raise ForbiddenError(
            f"Role '{actor.role}' cannot approve this change. Required roles: {allowed_roles}"
        )

    # Fetch and execute stored change
    execution_result = {}
    if approval.change_set_id:
        change_set = session.get(ChangeSet, approval.change_set_id)
        if change_set:
            handler = get_change_handler(change_set.action)
            if handler:
                handler_instance = handler() if isinstance(handler, type) else handler
                from app.core.change_service import ChangeRequest
                exec_req = ChangeRequest(
                    action=change_set.action,
                    entity_type=change_set.entity_type,
                    entity_id=change_set.entity_id,
                    payload=change_set.payload,
                    reason=reason.strip(),
                    actor=actor
                )
                execution_result = handler_instance.apply(exec_req, session)
            change_set.status = "APPLIED"
            session.add(change_set)

    approval.status = "APPROVED"
    approval.approved_by = actor.name or actor.id
    approval.approved_at = now()
    session.add(approval)
    session.flush()

    # Record in audit trail
    audit_id = audit_module.record(
        session=session,
        actor=actor,
        action="approval.approved",
        entity_type=approval.entity_type,
        entity_id=approval.entity_id,
        before={"status": "PENDING"},
        after={
            "status": "APPROVED",
            "approval_id": approval.id,
            "change_set_id": approval.change_set_id,
            "execution_result": execution_result
        },
        reason=reason.strip(),
        status="SUCCESS",
        approval_id=approval.id
    )

    session.commit()

    return {
        "approval_id": approval.id,
        "change_set_id": approval.change_set_id,
        "status": "APPROVED",
        "approved_by": approval.approved_by,
        "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
        "audit_event_id": audit_id,
        "execution_result": execution_result
    }


def reject_request(
    session: Session,
    approval_id: str,
    actor: Actor,
    reason: str
) -> Dict[str, Any]:
    """Reject a pending approval request with a mandatory rationale."""
    if not reason or not reason.strip():
        raise FestOSError(
            message="Rejection requires a mandatory recorded reason.",
            code="VALIDATION_ERROR",
            status_code=422
        )

    approval = session.get(Approval, approval_id)
    if not approval:
        raise NotFoundError(f"Approval request '{approval_id}' not found")

    if approval.status != "PENDING":
        raise FestOSError(
            message=f"Approval request is already {approval.status}",
            code="VERSION_CONFLICT",
            status_code=409
        )

    # Validate role
    policy = APPROVAL_POLICIES.get(approval.risk_kind or "DEFAULT_HIGH_RISK", APPROVAL_POLICIES["DEFAULT_HIGH_RISK"])
    allowed_roles = policy["required_roles"]
    if actor.role not in allowed_roles and actor.role not in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]:
        raise ForbiddenError(
            f"Role '{actor.role}' cannot reject this change. Required roles: {allowed_roles}"
        )

    if approval.change_set_id:
        change_set = session.get(ChangeSet, approval.change_set_id)
        if change_set:
            change_set.status = "REJECTED"
            session.add(change_set)

    approval.status = "REJECTED"
    approval.rejection_reason = reason.strip()
    session.add(approval)
    session.flush()

    audit_module.record(
        session=session,
        actor=actor,
        action="approval.rejected",
        entity_type=approval.entity_type,
        entity_id=approval.entity_id,
        before={"status": "PENDING"},
        after={
            "status": "REJECTED",
            "approval_id": approval.id,
            "rejection_reason": reason.strip()
        },
        reason=reason.strip(),
        status="SUCCESS",
        approval_id=approval.id
    )

    session.commit()

    return {
        "approval_id": approval.id,
        "change_set_id": approval.change_set_id,
        "status": "REJECTED",
        "rejection_reason": approval.rejection_reason,
        "rejected_by": actor.name or actor.id
    }
