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
    capacity: int = Field(default=12)
    driver_name: Optional[str] = Field(default=None)
    driver_phone: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class ShuttleAssignment(SQLModel, table=True):
    __tablename__ = "shuttle_assignment"

    id: str = Field(default_factory=lambda: f"sht_{uuid.uuid4().hex[:8]}", primary_key=True)
    transport_id: Optional[str] = Field(default=None, foreign_key="transport.id", index=True)
    route_name: str
    pickup_location: str
    drop_location: str
    departure_at: Optional[datetime] = Field(default=None)
    arrival_at: Optional[datetime] = Field(default=None)
    capacity: int = Field(default=12)
    assigned_count: int = Field(default=0)
    status: str = Field(default="SCHEDULED")  # SCHEDULED|IN_TRANSIT|COMPLETED
