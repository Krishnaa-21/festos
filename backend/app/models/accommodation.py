# OWNER: P2
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import now


class Room(SQLModel, table=True):
    __tablename__ = "room"

    id: str = Field(default_factory=lambda: f"rm_{uuid.uuid4().hex[:8]}", primary_key=True)
    block: str = Field(index=True)
    floor: int = Field(default=1)
    bed_count: int = Field(default=2)
    capacity: int = Field(default=2)
    accessible: bool = Field(default=False)
    accessibility: str = Field(default="no")  # 'yes'|'no' from hostels.csv
    gender_class: str = Field(default="UNKNOWN")  # boys|girls|UNKNOWN
    status: str = Field(default="available")  # available|maintenance|closed
    cleaning_status: str = Field(default="READY")  # READY|CLEANING|DIRTY
    cleaning_ready_at: Optional[datetime] = Field(default=None)

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ExternalProperty(SQLModel, table=True):
    __tablename__ = "external_property"

    id: str = Field(default_factory=lambda: f"ext_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    beds: int = Field(default=0)
    cost_per_bed_night: float = Field(default=0.0)
    distance_km: float = Field(default=0.0)
    transport_availability: Optional[str] = Field(default="yes")  # 'yes'|'limited'|'no'
    transport_limited: bool = Field(default=False)
    accessibility_verified: bool = Field(default=False)
    gender_suitability_verified: bool = Field(default=False)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class StayAssignment(SQLModel, table=True):
    __tablename__ = "stay_assignment"
    __table_args__ = (
        UniqueConstraint("plan_id", "bed_key", "start_at", name="uq_stay_plan_bed_start"),
    )

    id: str = Field(default_factory=lambda: f"sty_{uuid.uuid4().hex[:10]}", primary_key=True)
    plan_id: str = Field(index=True)
    bed_key: str = Field(index=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    room_id: Optional[str] = Field(default=None, index=True)
    property_id: Optional[str] = Field(default=None, index=True)
    is_external: bool = Field(default=False)
    start_at: datetime = Field(index=True)
    end_at: datetime = Field(index=True)
    cost_inr: float = Field(default=0.0)
    status: str = Field(default="ACTIVE")  # ACTIVE|CANCELLED|COMPLETED

    # JSON-encoded explainability packet per spec section 3.4 & Task 8
    explanation: Optional[str] = Field(default=None)

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class AccommodationPlan(SQLModel, table=True):
    __tablename__ = "accommodation_plan"

    id: str = Field(default_factory=lambda: f"acp_{uuid.uuid4().hex[:8]}", primary_key=True)
    plan_id: str = Field(index=True, unique=True)
    kind: str = Field(default="A")  # A|B|C|LIVE (A cohesion-first, B cost-first, C balanced)
    name: str = Field(default="Plan")
    status: str = Field(default="CANDIDATE")  # CANDIDATE|APPROVED|LIVE|ARCHIVED

    # Plan-level comparison metrics
    on_campus_placed: int = Field(default=0)
    external_placed: int = Field(default=0)
    unplaced_count: int = Field(default=0)
    contingent_splits: int = Field(default=0)
    total_cost_inr: float = Field(default=0.0)
    safety_flags_count: int = Field(default=0)
    accessibility_issues_count: int = Field(default=0)
    relaxed_constraints_count: int = Field(default=0)
    minors_external_count: int = Field(default=0)

    # Deterministic hash & summaries
    plan_hash: Optional[str] = Field(default=None)
    sacrifices_summary: Optional[str] = Field(default=None)
    parameters_applied: Optional[str] = Field(default=None)  # JSON string
    shortages_data: Optional[str] = Field(default=None)  # JSON string

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
