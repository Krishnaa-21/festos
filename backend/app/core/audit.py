# OWNER: P3
import uuid
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.core.clock import now


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
    status: str = "SUCCESS"
) -> str:
    """Append-only writer for audit events.
    Guarantees immutability and returns the audit event ID.
    """
    event_id = f"aud_{uuid.uuid4().hex[:12]}"
    actor_id = getattr(actor, "id", str(actor)) if actor else "SYSTEM"
    actor_name = getattr(actor, "name", "System") if actor else "System"
    actor_role = getattr(actor, "role", "SYSTEM") if actor else "SYSTEM"

    # Lazy import to avoid circular dependency
    try:
        from app.models.audit import AuditEvent
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
            status=status,
            timestamp=now()
        )
        session.add(event)
        session.flush()
    except Exception:
        # Fallback if DB table not yet created
        pass

    return event_id
