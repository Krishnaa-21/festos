# OWNER: P1
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from sqlmodel import Session

import app.core.audit as audit_module
from app.core.bus import publish
from app.core.clock import now
from app.core.errors import FestOSError, VersionConflictError
from app.core.registry import get_change_handler, get_impact_hooks
from app.schemas.common import Actor, Role, Violation


class ChangeRequest(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None
    actor: Actor
    related_incident_id: Optional[str] = None
    expected_version: Optional[int] = None
    dry_run: bool = False
    idempotency_key: Optional[str] = None

class ChangeResult(BaseModel):
    change_set_id: Optional[str] = None
    status: Literal["APPLIED", "PENDING_APPROVAL", "REJECTED", "DRY_RUN"]
    violations: List[Violation] = Field(default_factory=list)
    audit_event_ids: List[str] = Field(default_factory=list)
    impact: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ChangeHandler:
    """Base class/interface for action handlers."""
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        return "LOW"

    def revert(self, change_set: Any, session: Session) -> None:
        pass

def _stubbed_approvals_require(session: Session, req: ChangeRequest, change_set_id: str) -> None:
    """Stubbed interface for P3 approvals requirement."""
    try:
        from app.models.audit import Approval
        approval = Approval(
            id=f"appr_{uuid.uuid4().hex[:12]}",
            change_set_id=change_set_id,
            entity_type=req.entity_type,
            entity_id=req.entity_id,
            status="PENDING",
            required_role="FESTIVAL_DIRECTOR"
        )
        session.add(approval)
    except Exception:
        pass

def execute_change(req: ChangeRequest, session: Session) -> ChangeResult:
    """Executes a mutation following the standard FestOS pipeline:
    validate -> check constraints -> snapshot -> apply in ONE transaction
    -> audit_event + change_set -> impact hook -> recommendations -> approval gate.
    """
    handler = get_change_handler(req.action)
    if not handler:
        raise FestOSError(f"No registered change handler for action: {req.action}", code="NOT_FOUND", status_code=404)

    # Instantiate if class passed
    if isinstance(handler, type):
        handler_instance = handler()
    else:
        handler_instance = handler

    # 1. Optimistic Concurrency / Expected Version Check
    if req.expected_version is not None:
        # Check against snapshot version if available
        current_snapshot = handler_instance.snapshot(req, session)
        actual_version = current_snapshot.get("version")
        if actual_version is not None and actual_version != req.expected_version:
            raise VersionConflictError(
                f"Version conflict on {req.entity_type} {req.entity_id}: expected {req.expected_version}, got {actual_version}"
            )

    # 2. Validate & Constraint checks
    violations: List[Violation] = handler_instance.validate(req, session)
    hard_violations = [v for v in violations if v.hard]
    if hard_violations:
        return ChangeResult(
            status="REJECTED",
            violations=violations,
            recommendations=["Resolve hard constraint violations before proceeding"]
        )

    # 3. Snapshot previous state
    previous_state = handler_instance.snapshot(req, session)

    # 4. Risk assessment & Approval gate
    risk_level = handler_instance.risk(req)
    if risk_level == "HIGH":
        # Check if actor is allowed to approve directly and provided a reason
        can_approve = (
            req.actor.role in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]
            and bool(req.reason and req.reason.strip())
        )
        if not can_approve:
            change_set_id = f"cs_{uuid.uuid4().hex[:12]}"
            _stubbed_approvals_require(session, req, change_set_id)
            return ChangeResult(
                change_set_id=change_set_id,
                status="PENDING_APPROVAL",
                violations=violations,
                recommendations=["Requires Festival Director review and recorded rationale"],
                warnings=["High-risk change queued for approval gate"]
            )

    # 5. Dry Run
    if req.dry_run:
        impact_summary = {"preview": True, "affected_entity": f"{req.entity_type}:{req.entity_id}"}
        return ChangeResult(
            status="DRY_RUN",
            violations=violations,
            impact=impact_summary,
            recommendations=["Dry run verified successfully. Ready to apply."]
        )

    # 6. Apply inside a Savepoint Transaction
    change_set_id = f"cs_{uuid.uuid4().hex[:12]}"
    audit_event_ids: List[str] = []

    try:
        with session.begin_nested():
            # Apply changes
            apply_result = handler_instance.apply(req, session)

            # Record ChangeSet in DB
            from app.models.change import ChangeSet
            change_set = ChangeSet(
                id=change_set_id,
                action=req.action,
                entity_type=req.entity_type,
                entity_id=req.entity_id,
                actor_id=req.actor.id,
                actor_role=req.actor.role,
                payload=req.payload,
                previous_state=previous_state,
                status="APPLIED",
                reason=req.reason,
                applied_at=now()
            )
            session.add(change_set)

            # Record Audit Event
            aud_id = audit_module.record(
                session=session,
                actor=req.actor,
                action=req.action,
                entity_type=req.entity_type,
                entity_id=req.entity_id,
                before=previous_state,
                after=apply_result,
                change_set_id=change_set_id,
                reason=req.reason,
                status="SUCCESS"
            )
            audit_event_ids.append(aud_id)

            # Impact Hooks (defaulting to no-op)
            impact_data = {}
            for hook in get_impact_hooks():
                try:
                    res = hook(req, apply_result, session)
                    if isinstance(res, dict):
                        impact_data.update(res)
                except Exception:
                    pass

        # Commit transaction
        session.commit()

        # In-process domain event publication
        publish(req.action, {
            "change_set_id": change_set_id,
            "entity_type": req.entity_type,
            "entity_id": req.entity_id,
            "result": apply_result
        })

        return ChangeResult(
            change_set_id=change_set_id,
            status="APPLIED",
            violations=violations,
            audit_event_ids=audit_event_ids,
            impact=impact_data or None
        )

    except Exception as e:
        session.rollback()
        raise e
