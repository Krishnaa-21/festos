# OWNER: P3
import uuid

from sqlmodel import Session

import app.core.audit as audit_module
from app.core.clock import now
from app.core.errors import FestOSError
from app.models.audit import Override
from app.schemas.common import Actor


def record(
    session: Session,
    entity_type: str,
    entity_id: str,
    constraint_code: str,
    reason: str,
    actor: Actor,
    risk_level: str = "HIGH"
) -> Override:
    """Record an operational override into the override register with mandatory reason enforcement.
    Appends an immutable audit event.
    """
    if not reason or not reason.strip():
        raise FestOSError(
            message="An override without a mandatory recorded reason is impossible under FestOS product principles.",
            code="VALIDATION_ERROR",
            status_code=422
        )

    override_id = f"ovr_{uuid.uuid4().hex[:8]}"
    override = Override(
        id=override_id,
        entity_type=entity_type,
        entity_id=entity_id,
        constraint_code=constraint_code,
        reason=reason.strip(),
        approved_by=actor.name or actor.id,
        approved_at=now(),
        risk_level=risk_level,
        status="ACTIVE"
    )
    session.add(override)
    session.flush()

    audit_module.record(
        session=session,
        actor=actor,
        action="override.recorded",
        entity_type=entity_type,
        entity_id=entity_id,
        before={},
        after={
            "override_id": override_id,
            "constraint_code": constraint_code,
            "reason": reason.strip(),
            "risk_level": risk_level
        },
        reason=reason.strip(),
        status="SUCCESS"
    )

    return override
