# OWNER: P1
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class ChangeSet(SQLModel, table=True):
    __tablename__ = "change_set"

    id: str = Field(default_factory=lambda: f"cs_{uuid.uuid4().hex[:12]}", primary_key=True)
    action: str = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    actor_id: str = Field(index=True)
    actor_role: str
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    previous_state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="APPLIED")  # APPLIED|PENDING_APPROVAL|REJECTED|DRY_RUN
    reason: Optional[str] = Field(default=None)
    applied_at: datetime = Field(default_factory=now)

class IdempotencyKey(SQLModel, table=True):
    __tablename__ = "idempotency_key"

    id: str = Field(default_factory=lambda: f"idk_{uuid.uuid4().hex[:10]}", primary_key=True)
    key: str = Field(index=True, unique=True)
    request_hash: str
    response_code: Optional[int] = Field(default=200)
    response_body: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
    expires_at: Optional[datetime] = Field(default=None)

class Scenario(SQLModel, table=True):
    __tablename__ = "scenario"

    id: str = Field(default_factory=lambda: f"scn_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    base_scenario_id: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now)
    created_by: str = Field(default="SYSTEM")
    status: str = Field(default="DRAFT")  # DRAFT|COMMITTED|DISCARDED
    forked_at: datetime = Field(default_factory=now)
    live_changeset_count_at_fork: int = Field(default=0)
    recorded_actions: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

class Assumption(SQLModel, table=True):
    __tablename__ = "assumption"

    id: str = Field(default_factory=lambda: f"asm_{uuid.uuid4().hex[:8]}", primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str
    owner: str = Field(default="P1")
    source: str = Field(default="SPEC")
    reason: str = Field(default="Default fest operating baseline")
    impact_if_changed: str = Field(default="Recalculates dependent metrics and schedules")
    updated_at: datetime = Field(default_factory=now)
