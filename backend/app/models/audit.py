# OWNER: P3
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class AuditEvent(SQLModel, table=True):
    """Append-only immutable record of all system operations."""
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
    status: str = Field(default="SUCCESS")
    timestamp: datetime = Field(default_factory=now, index=True)

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:8]}", primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: str = Field(default="VOLUNTEER")
    contingent_id: Optional[str] = Field(default=None, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=now)

class BreakGlassGrant(SQLModel, table=True):
    __tablename__ = "break_glass_grant"

    id: str = Field(default_factory=lambda: f"bgg_{uuid.uuid4().hex[:8]}", primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    granted_by: str = Field(default="FESTIVAL_DIRECTOR")
    reason: str
    expires_at: datetime
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
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
    rejection_reason: Optional[str] = Field(default=None)

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
