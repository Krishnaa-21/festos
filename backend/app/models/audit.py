# OWNER: P3
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DDL, JSON, Column, event
from sqlmodel import Field, SQLModel

from app.core.clock import now


class AuditEvent(SQLModel, table=True):
    """Append-only immutable record of all system operations with cryptographic hash chaining."""
    __tablename__ = "audit_event"

    id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}", primary_key=True)
    actor_id: str = Field(index=True)
    actor_name: str
    actor_role: str
    action: str = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    before_state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    after_state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    change_set_id: Optional[str] = Field(default=None, index=True)
    reason: Optional[str] = Field(default=None)
    approval_id: Optional[str] = Field(default=None, index=True)
    related_incident_id: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="SUCCESS")
    prev_hash: str = Field(default="0" * 64, index=True)
    current_hash: str = Field(default="", index=True)
    timestamp: datetime = Field(default_factory=now, index=True)


# Application-level immutability enforcement
@event.listens_for(AuditEvent, "before_update")
def _prevent_audit_update(mapper, connection, target):
    raise PermissionError("Audit log is append-only: UPDATE operations are strictly prohibited")


@event.listens_for(AuditEvent, "before_delete")
def _prevent_audit_delete(mapper, connection, target):
    raise PermissionError("Audit log is append-only: DELETE operations are strictly prohibited")


# SQLite Database Triggers for DB-level immutability
_sqlite_trigger_no_update = DDL("""
CREATE TRIGGER IF NOT EXISTS audit_event_no_update
BEFORE UPDATE ON audit_event
BEGIN
    SELECT RAISE(ABORT, 'Audit log is append-only: UPDATE prohibited');
END;
""")

_sqlite_trigger_no_delete = DDL("""
CREATE TRIGGER IF NOT EXISTS audit_event_no_delete
BEFORE DELETE ON audit_event
BEGIN
    SELECT RAISE(ABORT, 'Audit log is append-only: DELETE prohibited');
END;
""")

event.listen(AuditEvent.__table__, "after_create", _sqlite_trigger_no_update.execute_if(dialect="sqlite"))
event.listen(AuditEvent.__table__, "after_create", _sqlite_trigger_no_delete.execute_if(dialect="sqlite"))


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:8]}", primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: str = Field(default="VOLUNTEER")
    contingent_id: Optional[str] = Field(default=None, index=True)
    is_active: bool = Field(default=True)
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=now)


class BreakGlassGrant(SQLModel, table=True):
    __tablename__ = "break_glass_grant"

    id: str = Field(default_factory=lambda: f"bgg_{uuid.uuid4().hex[:8]}", primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    entity: str = Field(index=True)  # e.g. "participant:P10023"
    field: str = Field(index=True)   # e.g. "medical_notes"
    reason: str
    granted_by: str = Field(default="FESTIVAL_DIRECTOR")
    expires_at: datetime = Field(index=True)
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now)


class Approval(SQLModel, table=True):
    __tablename__ = "approval"

    id: str = Field(default_factory=lambda: f"app_{uuid.uuid4().hex[:8]}", primary_key=True)
    change_set_id: Optional[str] = Field(default=None, index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    status: str = Field(default="PENDING", index=True)  # PENDING|APPROVED|REJECTED
    required_role: str = Field(default="FESTIVAL_DIRECTOR")
    requested_by: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    risk_kind: Optional[str] = Field(default=None)
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
    rejection_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now)


class Override(SQLModel, table=True):
    __tablename__ = "override"

    id: str = Field(default_factory=lambda: f"ovr_{uuid.uuid4().hex[:8]}", primary_key=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    constraint_code: str = Field(index=True)
    reason: str
    approved_by: str = Field(default="FESTIVAL_DIRECTOR")
    approved_at: datetime = Field(default_factory=now)
    risk_level: str = Field(default="HIGH")
    status: str = Field(default="ACTIVE")
