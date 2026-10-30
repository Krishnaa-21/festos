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
    building: str = Field(default="UNKNOWN")
    description: Optional[str] = Field(default=None)

class InventoryItem(SQLModel, table=True):
    __tablename__ = "inventory_item"

    id: str = Field(default_factory=lambda: f"itm_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    code: str = Field(index=True)
    kind: str = Field(default="equipment")  # equipment|merch
    size: Optional[str] = Field(default=None)
    condition: str = Field(default="GOOD")  # NEW|GOOD|FAIR|DAMAGED
    quantity: int = Field(default=1)
    available_quantity: int = Field(default=1)
    location_id: Optional[str] = Field(default=None, foreign_key="inventory_location.id", index=True)
    status: str = Field(default="AVAILABLE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class InventoryMovement(SQLModel, table=True):
    __tablename__ = "inventory_movement"

    id: str = Field(default_factory=lambda: f"mvt_{uuid.uuid4().hex[:8]}", primary_key=True)
    item_id: str = Field(foreign_key="inventory_item.id", index=True)
    from_location_id: Optional[str] = Field(default=None)
    to_location_id: Optional[str] = Field(default=None)
    quantity: int = Field(default=1)
    movement_type: str = Field(default="TRANSFER")  # CHECK_IN|CHECK_OUT|TRANSFER|ADJUSTMENT
    moved_by: str = Field(default="SYSTEM")
    moved_at: datetime = Field(default_factory=now)

class MerchClaim(SQLModel, table=True):
    __tablename__ = "merch_claim"
    __table_args__ = (
        UniqueConstraint("canonical_participant_id", "item_id", name="uq_merch_claim_participant_item"),
    )

    id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:10]}", primary_key=True)
    canonical_participant_id: str = Field(index=True)
    item_id: str = Field(foreign_key="inventory_item.id", index=True)
    claimed_at: datetime = Field(default_factory=now)
    issued_by: str = Field(default="SYSTEM")
    size: Optional[str] = Field(default=None)
    status: str = Field(default="ISSUED")  # ISSUED|REVOKED
