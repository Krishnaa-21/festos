# OWNER: P3
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from app.core.clock import now
from app.models.audit import AuditEvent

GENESIS_HASH = "0" * 64


def compute_audit_hash(
    prev_hash: str,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: str,
    timestamp: datetime,
    before: Dict[str, Any],
    after: Dict[str, Any],
    reason: Optional[str] = None,
    status: str = "SUCCESS"
) -> str:
    """Deterministic cryptographic hash computation for an audit event."""
    before_str = json.dumps(before or {}, sort_keys=True)
    after_str = json.dumps(after or {}, sort_keys=True)
    content = (
        f"{prev_hash}|{action}|{entity_type}|{entity_id}|{actor_id}|"
        f"{timestamp.isoformat()}|{before_str}|{after_str}|"
        f"{reason or ''}|{status}"
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def record(
    session: Session,
    actor: Any,
    action: str,
    entity_type: str,
    entity_id: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    change_set_id: Optional[str] = None,
    reason: Optional[str] = None,
    status: str = "SUCCESS",
    approval_id: Optional[str] = None,
    related_incident_id: Optional[str] = None
) -> str:
    """Append-only writer for audit events.
    Computes cryptographic hash chained to previous event and returns the audit event ID.
    """
    event_id = f"aud_{uuid.uuid4().hex[:12]}"
    actor_id = getattr(actor, "id", str(actor)) if actor else "SYSTEM"
    actor_name = getattr(actor, "name", "System") if actor else "System"
    actor_role = getattr(actor, "role", "SYSTEM") if actor else "SYSTEM"
    event_time = now()

    # Determine previous hash in chain
    prev_hash = GENESIS_HASH
    try:
        last_event = session.exec(
            select(AuditEvent).order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
        ).first()
        if last_event and last_event.current_hash:
            prev_hash = last_event.current_hash
    except Exception:
        pass

    curr_hash = compute_audit_hash(
        prev_hash=prev_hash,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        timestamp=event_time,
        before=before or {},
        after=after or {},
        reason=reason,
        status=status
    )

    try:
        event = AuditEvent(
            id=event_id,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before or {},
            after_state=after or {},
            change_set_id=change_set_id,
            reason=reason,
            approval_id=approval_id,
            related_incident_id=related_incident_id,
            status=status,
            prev_hash=prev_hash,
            current_hash=curr_hash,
            timestamp=event_time
        )
        session.add(event)
        session.flush()
    except Exception:
        # Fallback if DB table not yet created
        pass

    return event_id


def verify_chain(session: Session) -> Dict[str, Any]:
    """Cryptographically verifies the entire audit log hash chain from genesis.
    Returns whether the chain is integral and the ID of any corrupted event.
    """
    events = session.exec(
        select(AuditEvent).order_by(AuditEvent.timestamp.asc(), AuditEvent.id.asc())
    ).all()

    if not events:
        return {
            "valid": True,
            "verified_count": 0,
            "genesis_hash": GENESIS_HASH,
            "latest_hash": GENESIS_HASH,
            "broken_event_id": None
        }

    expected_prev = GENESIS_HASH
    for i, event in enumerate(events):
        if event.prev_hash != expected_prev:
            return {
                "valid": False,
                "verified_count": i,
                "broken_event_id": event.id,
                "message": f"Link broken at event {event.id}: expected prev_hash {expected_prev}, got {event.prev_hash}"
            }

        recalculated = compute_audit_hash(
            prev_hash=event.prev_hash,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            actor_id=event.actor_id,
            timestamp=event.timestamp,
            before=event.before_state,
            after=event.after_state,
            reason=event.reason,
            status=event.status
        )

        if recalculated != event.current_hash:
            return {
                "valid": False,
                "verified_count": i,
                "broken_event_id": event.id,
                "message": f"Hash divergence at event {event.id}: recalculated {recalculated}, stored {event.current_hash}"
            }

        expected_prev = event.current_hash

    return {
        "valid": True,
        "verified_count": len(events),
        "genesis_hash": GENESIS_HASH,
        "latest_hash": expected_prev,
        "broken_event_id": None
    }
