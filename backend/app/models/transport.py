# OWNER: P1
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.clock import now


class Transport(SQLModel, table=True):
    __tablename__ = "transport"

    id: str = Field(default_factory=lambda: f"trn_{uuid.uuid4().hex[:8]}", primary_key=True)
    vehicle_number: str = Field(index=True)
    vehicle_type: str = Field(default="SHUTTLE")
    capacity: int = Field(default=15)
    driver_name: Optional[str] = Field(default=None)
    driver_phone: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Route(SQLModel, table=True):
    __tablename__ = "route"

    id: str = Field(default_factory=lambda: f"rot_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    origin: str = Field(default="CAMPUS")
    destination: str = Field(index=True)
    property_id: Optional[str] = Field(default=None, foreign_key="external_property.id", index=True)
    travel_time_min: int = Field(default=25)
    distance_km: float = Field(default=0.0)

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ShuttleRun(SQLModel, table=True):
    __tablename__ = "shuttle_run"

    id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}", primary_key=True)
    route_id: Optional[str] = Field(default=None, foreign_key="route.id", index=True)
    route_name: str = Field(default="Campus Shuttle")
    vehicle_id: Optional[str] = Field(default=None, foreign_key="transport.id", index=True)
    vehicle_number: Optional[str] = Field(default=None)
    property_id: Optional[str] = Field(default=None, foreign_key="external_property.id", index=True)
    departure_at: Optional[datetime] = Field(default=None, index=True)
    arrival_at: Optional[datetime] = Field(default=None, index=True)
    capacity: int = Field(default=15)
    passengers_assigned: int = Field(default=0)
    escort_staff_id: Optional[str] = Field(default=None, foreign_key="staff.id", index=True)
    status: str = Field(default="SCHEDULED")  # SCHEDULED|IN_TRANSIT|COMPLETED|CANCELLED

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ShuttleAssignment(SQLModel, table=True):
    __tablename__ = "shuttle_assignment"

    id: str = Field(default_factory=lambda: f"sht_{uuid.uuid4().hex[:8]}", primary_key=True)
    shuttle_run_id: Optional[str] = Field(default=None, foreign_key="shuttle_run.id", index=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    property_id: Optional[str] = Field(default=None, index=True)
    pickup_location: str = Field(default="CAMPUS")
    drop_location: str = Field(default="HOTEL")
    departure_at: Optional[datetime] = Field(default=None)
    safety_verified: bool = Field(default=False)
    verified_by_staff_id: Optional[str] = Field(default=None, foreign_key="staff.id")
    notes: Optional[str] = Field(default=None)
    status: str = Field(default="CONFIRMED")  # CONFIRMED|BOARDED|COMPLETED|CANCELLED

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class EscortAssignment(SQLModel, table=True):
    __tablename__ = "escort_assignment"

    id: str = Field(default_factory=lambda: f"esc_{uuid.uuid4().hex[:8]}", primary_key=True)
    staff_id: str = Field(foreign_key="staff.id", index=True)
    participant_id: Optional[str] = Field(default=None, foreign_key="participant.id", index=True)
    contingent_id: Optional[str] = Field(default=None, foreign_key="contingent.id", index=True)
    shuttle_run_id: Optional[str] = Field(default=None, foreign_key="shuttle_run.id", index=True)
    property_id: Optional[str] = Field(default=None, index=True)
    start_at: Optional[datetime] = Field(default=None)
    end_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="ASSIGNED")  # ASSIGNED|ACTIVE|COMPLETED|CANCELLED

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class GuardianApproval(SQLModel, table=True):
    __tablename__ = "guardian_approval"

    id: str = Field(default_factory=lambda: f"gdn_{uuid.uuid4().hex[:8]}", primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    contingent_id: Optional[str] = Field(default=None, index=True)
    property_id: str = Field(foreign_key="external_property.id", index=True)
    stay_duration_days: int = Field(default=3)
    escort_staff_id: Optional[str] = Field(default=None, foreign_key="staff.id", index=True)
    approval_status: str = Field(default="PENDING", index=True)  # PENDING|APPROVED|REJECTED
    responsible_coordinator_id: Optional[str] = Field(default=None, foreign_key="staff.id")
    notes: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
