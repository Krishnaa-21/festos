# OWNER: P1
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: str = Field(default_factory=lambda: f"stf_{uuid.uuid4().hex[:8]}", primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True)
    name: str = Field(index=True)
    role: str = Field(default="VOLUNTEER", index=True)  # Registration Desk|Hospitality|Events Team|Logistics Head|Merchandise Desk|Food Coordinator|Volunteer|Festival Director
    shift: Optional[str] = Field(default=None)  # e.g. '22:00-06:00', '06:00-14:00', '14:00-22:00', '10:00-18:00'
    skills: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    phone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")
    is_participant: bool = Field(default=False, index=True)
    contingent_id: Optional[str] = Field(default=None, index=True)
    assigned_contingent_escort: Optional[str] = Field(default=None)

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Shift(SQLModel, table=True):
    __tablename__ = "shift"

    id: str = Field(default_factory=lambda: f"shf_{uuid.uuid4().hex[:8]}", primary_key=True)
    staff_id: Optional[str] = Field(default=None, foreign_key="staff.id", index=True)
    role_required: str = Field(default="VOLUNTEER")
    location: str = Field(default="CAMPUS")
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    event_id: Optional[str] = Field(default=None, foreign_key="event.id", index=True)
    session_id: Optional[str] = Field(default=None, foreign_key="event_session.id", index=True)
    start_at: Optional[datetime] = Field(default=None, index=True)
    end_at: Optional[datetime] = Field(default=None, index=True)
    handover_notes: Optional[str] = Field(default=None)
    status: str = Field(default="SCHEDULED")  # SCHEDULED|ACTIVE|COMPLETED|CANCELLED|MISSED

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
