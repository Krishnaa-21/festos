# OWNER: P1
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    code: str = Field(index=True)
    solo_team: str = Field(default="SOLO")  # SOLO|TEAM
    event_type: Optional[str] = Field(default="solo")  # solo|team
    rounds: int = Field(default=1)
    rounds_text: Optional[str] = Field(default=None)  # e.g. 'prelims|semis|finals'
    duration_min: int = Field(default=60)
    venue_requirements: Optional[str] = Field(default=None)
    equipment_needs: Optional[str] = Field(default=None)
    volunteers_needed: Optional[int] = Field(default=0)
    requirements: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    min_team_size: Optional[int] = Field(default=1)
    max_team_size: Optional[int] = Field(default=1)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class EventRequirement(SQLModel, table=True):
    __tablename__ = "event_requirement"

    id: str = Field(default_factory=lambda: f"erq_{uuid.uuid4().hex[:8]}", primary_key=True)
    event_id: str = Field(foreign_key="event.id", index=True)
    item_name: str
    quantity: int = Field(default=1)
    is_critical: bool = Field(default=True)
    notes: Optional[str] = Field(default=None)

class EventSession(SQLModel, table=True):
    __tablename__ = "event_session"

    id: str = Field(default_factory=lambda: f"ses_{uuid.uuid4().hex[:8]}", primary_key=True)
    event_id: str = Field(foreign_key="event.id", index=True)
    round_number: int = Field(default=1)
    start_at: Optional[datetime] = Field(default=None)
    end_at: Optional[datetime] = Field(default=None)
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    status: str = Field(default="SCHEDULED")  # SCHEDULED|IN_PROGRESS|COMPLETED|CANCELLED

class ScheduleVersion(SQLModel, table=True):
    __tablename__ = "schedule_version"

    id: str = Field(default_factory=lambda: f"sch_{uuid.uuid4().hex[:8]}", primary_key=True)
    plan_name: str
    status: str = Field(default="ASSUMED")  # Schedules are labelled ASSUMED
    created_at: datetime = Field(default_factory=now)
    published_at: Optional[datetime] = Field(default=None)

class Conflict(SQLModel, table=True):
    __tablename__ = "conflict"

    id: str = Field(default_factory=lambda: f"cfl_{uuid.uuid4().hex[:8]}", primary_key=True)
    schedule_version_id: Optional[str] = Field(default=None, index=True)
    conflict_type: str = Field(index=True)
    severity: int = Field(default=2)
    description: str
    entity_refs: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    resolved: bool = Field(default=False)
