# OWNER: P1
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    judges_needed: int = Field(default=2)
    requirements: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    min_team_size: Optional[int] = Field(default=1)
    max_team_size: Optional[int] = Field(default=1)
    status: str = Field(default="ACTIVE")  # ACTIVE|CANCELLED|MERGED

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
    schedule_version_id: Optional[str] = Field(default=None, index=True)
    event_id: str = Field(foreign_key="event.id", index=True)
    event_name: str = Field(default="")
    round: str = Field(default="prelims")  # prelims|semis|finals|single
    round_number: int = Field(default=1)
    heat: str = Field(default="1")  # M1, E1, L1, etc.
    session_code: Optional[str] = Field(default=None)
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    venue_name: Optional[str] = Field(default=None)
    start_at: Optional[datetime] = Field(default=None, index=True)
    end_at: Optional[datetime] = Field(default=None, index=True)
    entrants_count: int = Field(default=0)
    entrant_basis: str = Field(default="registered (assigned)")
    volunteers_required: int = Field(default=0)
    equipment_required: Optional[str] = Field(default=None)
    judge_slots_needed: int = Field(default=2)
    assigned_judges: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    assigned_participant_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    wave: Optional[str] = Field(default=None)
    status: str = Field(default="SCHEDULED")  # SCHEDULED|IN_PROGRESS|COMPLETED|CANCELLED

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ScheduleVersion(SQLModel, table=True):
    __tablename__ = "schedule_version"

    id: str = Field(default_factory=lambda: f"sch_{uuid.uuid4().hex[:8]}", primary_key=True)
    plan_name: str
    status: str = Field(default="ASSUMED")  # All generated schedules labelled ASSUMED
    solver: str = Field(default="greedy")
    sessions_count: int = Field(default=0)
    unscheduled_count: int = Field(default=0)
    unplaced_sessions_count: int = Field(default=0)
    conflicts_count: int = Field(default=0)
    sessions_snapshot: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=now)
    created_by: Optional[str] = Field(default="SYSTEM")
    published_at: Optional[datetime] = Field(default=None)


class Conflict(SQLModel, table=True):
    __tablename__ = "conflict"

    id: str = Field(default_factory=lambda: f"cfl_{uuid.uuid4().hex[:8]}", primary_key=True)
    schedule_version_id: Optional[str] = Field(default=None, index=True)
    conflict_type: str = Field(index=True)  # 10 conflict types
    severity: int = Field(default=2)  # 1-4
    status: str = Field(default="OPEN", index=True)  # OPEN|RESOLVED|ACCEPTED
    description: str
    entity_refs: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    resolution_notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now)
    resolved_at: Optional[datetime] = Field(default=None)


class Judge(SQLModel, table=True):
    __tablename__ = "judge"

    id: str = Field(default_factory=lambda: f"jdg_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    college_affiliation: Optional[str] = Field(default=None, index=True)  # contingent_id
    expert_events: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now)


class ProvisionalTeam(SQLModel, table=True):
    __tablename__ = "provisional_team"

    id: str = Field(primary_key=True)  # e.g. "TEAM_C01_E03"
    contingent_id: str = Field(index=True)
    event_id: str = Field(index=True)
    name: str
    status: str = Field(default="ASSUMED")  # ASSUMED|CONFIRMED
    participant_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
