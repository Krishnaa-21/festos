# OWNER: P1
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: str = Field(default_factory=lambda: f"stf_{uuid.uuid4().hex[:8]}", primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True)
    name: str = Field(index=True)
    role: str = Field(default="VOLUNTEER")  # VOLUNTEER|LEAD|STAFF
    skills: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    phone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class Shift(SQLModel, table=True):
    __tablename__ = "shift"

    id: str = Field(default_factory=lambda: f"shf_{uuid.uuid4().hex[:8]}", primary_key=True)
    staff_id: Optional[str] = Field(default=None, foreign_key="staff.id", index=True)
    role_required: str = Field(default="VOLUNTEER")
    location: str = Field(default="CAMPUS")
    start_at: Optional[datetime] = Field(default=None)
    end_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="SCHEDULED")  # SCHEDULED|IN_PROGRESS|COMPLETED|MISSED
