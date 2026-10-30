# OWNER: P1
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import now


class InventoryLocation(SQLModel, table=True):
    __tablename__ = "inventory_location"

    id: str = Field(default_factory=lambda: f"loc_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    code: str = Field(index=True)
    building: str = Field(default="CAMPUS")
    location_type: str = Field(default="STORAGE")  # VENUE | STORAGE | DESK | IN_TRANSIT | REPAIR
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)


class InventoryItem(SQLModel, table=True):
    __tablename__ = "inventory_item"

    id: str = Field(default_factory=lambda: f"itm_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    code: str = Field(default="", index=True)
    kind: str = Field(default="equipment")  # equipment | merch
    category: str = Field(default="general")  # audio | video | power | furniture | stage | apparel | badge | medal
    size: Optional[str] = Field(default=None)
    condition: str = Field(default="good")  # good | needs check | under repair | damaged
    quantity: int = Field(default=1)
    reserved_quantity: Optional[int] = Field(default=0)
    available_quantity: int = Field(default=1)
    location: Optional[str] = Field(default=None)  # e.g. 'Registration Desk'
    location_id: Optional[str] = Field(default=None, foreign_key="inventory_location.id", index=True)
    low_stock_threshold: int = Field(default=5)
    unit: str = Field(default="pcs")
    status: str = Field(default="AVAILABLE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class InventoryMovement(SQLModel, table=True):
    __tablename__ = "inventory_movement"

    id: str = Field(default_factory=lambda: f"mvt_{uuid.uuid4().hex[:8]}", primary_key=True)
    item_id: str = Field(foreign_key="inventory_item.id", index=True)
    from_location_id: Optional[str] = Field(default=None, index=True)
    to_location_id: Optional[str] = Field(default=None, index=True)
    quantity: int = Field(default=1)
    movement_type: str = Field(default="RECEIVE")
    # RECEIVE | RESERVE | RELEASE | TRANSFER_OUT | TRANSFER_IN | ISSUE | RETURN | DAMAGE | SEND_REPAIR | REPAIR_DONE | ADJUST
    reason: Optional[str] = Field(default=None)
    reference_id: Optional[str] = Field(default=None, index=True)
    eta: Optional[datetime] = Field(default=None)
    status: str = Field(default="COMPLETED")  # COMPLETED | PENDING
    moved_by: str = Field(default="SYSTEM")
    moved_at: datetime = Field(default_factory=now)


class Transfer(SQLModel, table=True):
    __tablename__ = "inventory_transfer"

    id: str = Field(default_factory=lambda: f"trf_{uuid.uuid4().hex[:8]}", primary_key=True)
    item_id: str = Field(foreign_key="inventory_item.id", index=True)
    from_location_id: str = Field(index=True)
    to_location_id: str = Field(index=True)
    quantity: int = Field(default=1)
    eta: Optional[datetime] = Field(default=None)
    vehicle: Optional[str] = Field(default=None)
    status: str = Field(default="IN_TRANSIT")  # IN_TRANSIT | COMPLETED | CANCELLED
    reason: Optional[str] = Field(default=None)
    initiated_by: str = Field(default="SYSTEM")
    initiated_at: datetime = Field(default_factory=now)
    completed_by: Optional[str] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)


class MerchClaim(SQLModel, table=True):
    __tablename__ = "merch_claim"
    __table_args__ = (
        UniqueConstraint("canonical_participant_id", "item_id", name="uq_merch_claim_participant_item"),
    )

    id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:10]}", primary_key=True)
    canonical_participant_id: str = Field(index=True)
    item_id: str = Field(foreign_key="inventory_item.id", index=True)
    item_name: Optional[str] = Field(default=None)
    size: Optional[str] = Field(default=None)
    counter_id: Optional[str] = Field(default=None)
    claimed_at: datetime = Field(default_factory=now)
    issued_by: str = Field(default="SYSTEM")
    status: str = Field(default="ISSUED")  # ISSUED | VOIDED
    void_reason: Optional[str] = Field(default=None)
    voided_by: Optional[str] = Field(default=None)
    voided_at: Optional[datetime] = Field(default=None)


class EntitlementPolicy(SQLModel, table=True):
    __tablename__ = "entitlement_policy"

    id: str = Field(default_factory=lambda: f"pol_{uuid.uuid4().hex[:8]}", primary_key=True)
    item_name: str = Field(index=True, unique=True)
    per_head: bool = Field(default=True)
    default_quantity: int = Field(default=1)
    is_editable: bool = Field(default=True)
    description: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=now)
