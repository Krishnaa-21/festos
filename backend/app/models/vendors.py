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
    dietary_options: Optional[str] = Field(default=None)  # e.g. 'vegetarian'
    menu: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    menu_description: Optional[str] = Field(default=None) # e.g. 'North Indian'
    hygiene_valid_from: Optional[datetime] = Field(default=None)
    hygiene_valid_to: Optional[datetime] = Field(default=None)
    hygiene_certificate_expiry: Optional[str] = Field(default=None) # e.g. '2026-10-31'
    hours: Optional[str] = Field(default=None)            # e.g. '07:00-23:00'
    capacity: Optional[int] = Field(default=None)         # e.g. 264
    payment_terms: Optional[str] = Field(default=None)    # e.g. 'minimum guarantee'
    base_rate_per_meal_inr: float = Field(default=180.0)
    contact_phone: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")  # ACTIVE | SUSPENDED | SHUT_DOWN
    contract_info: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class MealSlot(SQLModel, table=True):
    __tablename__ = "meal_slot"

    id: str = Field(default_factory=lambda: f"msl_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)  # BREAKFAST | LUNCH | SNACKS | DINNER | LATE_NIGHT
    start_time: str                # e.g. "07:30"
    end_time: str                  # e.g. "10:00"
    date: str = Field(index=True)  # YYYY-MM-DD
    meal_type: str = Field(default="REGULAR")


class VendorAssignment(SQLModel, table=True):
    __tablename__ = "vendor_assignment"

    id: str = Field(default_factory=lambda: f"vna_{uuid.uuid4().hex[:8]}", primary_key=True)
    vendor_id: str = Field(foreign_key="vendor.id", index=True)
    meal_slot_id: str = Field(foreign_key="meal_slot.id", index=True)
    venue_id: Optional[str] = Field(default=None, foreign_key="venue.id", index=True)
    location_name: Optional[str] = Field(default=None)
    date: str = Field(index=True)
    allocated_capacity: int = Field(default=0)
    rate_per_meal_inr: float = Field(default=180.0)
    status: str = Field(default="SCHEDULED")  # SCHEDULED | ACTIVE | CANCELLED | REPLACED
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class VendorSettlement(SQLModel, table=True):
    __tablename__ = "vendor_settlement"

    id: str = Field(default_factory=lambda: f"stl_{uuid.uuid4().hex[:8]}", primary_key=True)
    vendor_id: str = Field(foreign_key="vendor.id", index=True)
    invoice_number: Optional[str] = Field(default=None)
    contract_amount_inr: float = Field(default=0.0)
    advance_paid_inr: float = Field(default=0.0)
    balance_due_inr: float = Field(default=0.0)
    payment_terms: str = Field(default="minimum guarantee")
    due_date: str = Field(default="2026-11-05")
    status: str = Field(default="PENDING_VERIFICATION")  # PENDING_VERIFICATION | PAID | PARTIALLY_PAID | DISPUTED | OVERDUE
    dispute_reason: Optional[str] = Field(default=None)
    disputed_amount_inr: float = Field(default=0.0)
    dispute_opened_by: Optional[str] = Field(default=None)
    dispute_opened_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class EmergencySpend(SQLModel, table=True):
    __tablename__ = "emergency_spend"

    id: str = Field(default_factory=lambda: f"emg_{uuid.uuid4().hex[:8]}", primary_key=True)
    description: str
    amount_inr: float
    category: str = Field(default="VENDOR_BACKUP")  # VENDOR_BACKUP | ACCOMMODATION | LOGISTICS | OTHER
    reason: str
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
    audit_link: Optional[str] = Field(default=None)
    status: str = Field(default="APPROVED")  # PENDING_APPROVAL | APPROVED | REJECTED
    created_at: datetime = Field(default_factory=now)

