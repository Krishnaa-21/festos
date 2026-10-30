# OWNER: P1
from typing import Any, Dict, List

import pytest
from app.core.change_service import ChangeHandler, ChangeRequest, execute_change
from app.core.errors import VersionConflictError
from app.core.registry import register_change_handler
from app.models.audit import Approval, AuditEvent
from app.models.change import ChangeSet
from app.schemas.common import Actor, Severity, Violation
from sqlmodel import Session, select


# Test change handlers
@register_change_handler("test.standard_mutation")
class StandardMutationHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        if req.payload.get("invalid"):
            return [Violation(code="INVALID_PAYLOAD", severity=Severity.HIGH, hard=True, message="Payload is invalid")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {"version": 1, "value": "old"}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        if req.payload.get("fail_in_apply"):
            raise RuntimeError("Database error during apply step")
        return {"version": 2, "value": req.payload.get("value", "new")}

    def risk(self, req: ChangeRequest) -> str:
        if req.payload.get("high_risk"):
            return "HIGH"
        return "LOW"

def test_change_service_success(session: Session, director_actor: Actor):
    """Verify that valid changes apply, commit change_set and record audit."""
    req = ChangeRequest(
        action="test.standard_mutation",
        entity_type="item",
        entity_id="itm_100",
        payload={"value": "updated_name"},
        actor=director_actor,
        reason="Routine update"
    )
    result = execute_change(req, session)

    assert result.status == "APPLIED"
    assert result.change_set_id is not None
    assert len(result.audit_event_ids) > 0

    # Verify change_set was recorded
    cs = session.exec(select(ChangeSet).where(ChangeSet.id == result.change_set_id)).first()
    assert cs is not None
    assert cs.entity_id == "itm_100"
    assert cs.actor_id == director_actor.id

    # Verify audit event was recorded
    audit = session.exec(select(AuditEvent).where(AuditEvent.change_set_id == result.change_set_id)).first()
    assert audit is not None
    assert audit.action == "test.standard_mutation"

def test_change_service_rollback_leaves_no_partial_state(session: Session, director_actor: Actor):
    """Verify that failure during apply rolls back transaction and leaves no state."""
    req = ChangeRequest(
        action="test.standard_mutation",
        entity_type="item",
        entity_id="itm_101",
        payload={"fail_in_apply": True},
        actor=director_actor
    )

    with pytest.raises(RuntimeError):
        execute_change(req, session)

    # Verify no ChangeSet or AuditEvent remained
    cs = session.exec(select(ChangeSet).where(ChangeSet.entity_id == "itm_101")).first()
    assert cs is None
    aud = session.exec(select(AuditEvent).where(AuditEvent.entity_id == "itm_101")).first()
    assert aud is None

def test_change_service_version_conflict(session: Session, director_actor: Actor):
    """Verify optimistic concurrency detects version mismatches."""
    req = ChangeRequest(
        action="test.standard_mutation",
        entity_type="item",
        entity_id="itm_102",
        expected_version=99,  # Snapshot provides version 1
        payload={"value": "new"},
        actor=director_actor
    )

    with pytest.raises(VersionConflictError):
        execute_change(req, session)

def test_change_service_dry_run_writes_nothing(session: Session, director_actor: Actor):
    """Verify dry_run=True returns preview and writes no rows to DB."""
    req = ChangeRequest(
        action="test.standard_mutation",
        entity_type="item",
        entity_id="itm_103",
        payload={"value": "preview_only"},
        dry_run=True,
        actor=director_actor
    )
    result = execute_change(req, session)

    assert result.status == "DRY_RUN"
    assert result.impact is not None

    # Ensure nothing saved
    cs = session.exec(select(ChangeSet).where(ChangeSet.entity_id == "itm_103")).first()
    assert cs is None

def test_change_service_pending_approval_for_high_risk(session: Session, volunteer_actor: Actor):
    """Verify high risk mutations by non-director without valid reason are held for approval."""
    req = ChangeRequest(
        action="test.standard_mutation",
        entity_type="item",
        entity_id="itm_104",
        payload={"value": "dangerous", "high_risk": True},
        actor=volunteer_actor
    )
    result = execute_change(req, session)

    assert result.status == "PENDING_APPROVAL"
    assert result.change_set_id is not None

    # Check approval record queued
    appr = session.exec(select(Approval).where(Approval.change_set_id == result.change_set_id)).first()
    assert appr is not None
    assert appr.status == "PENDING"
