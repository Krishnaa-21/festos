# OWNER: P2
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class Vendor(SQLModel, table=True):
    __tablename__ = "vendor"

    id: str = Field(default_factory=lambda: f"vnd_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    dietary_declared: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    menu: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    hygiene_valid_from: Optional[datetime] = Field(default=None)
    hygiene_valid_to: Optional[datetime] = Field(default=None)
    contact_phone: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class MealSlot(SQLModel, table=True):
    __tablename__ = "meal_slot"

    id: str = Field(default_factory=lambda: f"msl_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)  # BREAKFAST|LUNCH|SNACKS|DINNER|LATE_NIGHT
    start_time: str
    end_time: str
    date: str = Field(index=True)
    meal_type: str = Field(default="REGULAR")

class VendorAssignment(SQLModel, table=True):
    __tablename__ = "vendor_assignment"

    id: str = Field(default_factory=lambda: f"vna_{uuid.uuid4().hex[:8]}", primary_key=True)
    vendor_id: str = Field(foreign_key="vendor.id", index=True)
    meal_slot_id: str = Field(foreign_key="meal_slot.id", index=True)
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    date: str = Field(index=True)
    status: str = Field(default="SCHEDULED")
