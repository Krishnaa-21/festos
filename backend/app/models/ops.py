# OWNER: P2
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now
from app.models.change import Assumption  # noqa: F401


class Venue(SQLModel, table=True):
    __tablename__ = "venue"

    id: str = Field(default_factory=lambda: f"ven_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    code: str = Field(default="", index=True)
    building: str = Field(default="CAMPUS")
    capacity: int = Field(default=100)
    availability_windows: Optional[str] = Field(default=None)  # from venues.csv
    indoor_outdoor: Optional[str] = Field(default="indoor")    # 'indoor'|'outdoor'
    accessible: bool = Field(default=True)
    setup_time_min: int = Field(default=15)
    teardown_time_min: int = Field(default=15)
    feature_tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = Field(default="AVAILABLE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class TravelTime(SQLModel, table=True):
    __tablename__ = "travel_time"

    id: str = Field(default_factory=lambda: f"trt_{uuid.uuid4().hex[:8]}", primary_key=True)
    from_venue_id: str = Field(foreign_key="venue.id", index=True)
    to_venue_id: str = Field(foreign_key="venue.id", index=True)
    travel_time_min: int = Field(default=15)

class Incident(SQLModel, table=True):
    __tablename__ = "incident"

    id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:8]}", primary_key=True)
    title: str = Field(index=True)
    severity: int = Field(default=2)  # 1-4
    category: str = Field(default="GENERAL")  # LOGISTICS|ACCOMMODATION|MEDICAL|EVENT
    description: str
    status: str = Field(default="OPEN", index=True)  # OPEN|IN_PROGRESS|RESOLVED|ESCALATED
    reported_by: str = Field(default="SYSTEM")
    assigned_to: Optional[str] = Field(default=None)
    reported_at: datetime = Field(default_factory=now)
    resolved_at: Optional[datetime] = Field(default=None)

class NotificationDraft(SQLModel, table=True):
    __tablename__ = "notification_draft"

    id: str = Field(default_factory=lambda: f"not_{uuid.uuid4().hex[:8]}", primary_key=True)
    channel: str = Field(default="SMS")  # SMS|EMAIL|WHATSAPP|APP
    recipient: str = Field(index=True)
    subject: Optional[str] = Field(default=None)
    body: str
    status: str = Field(default="DRAFT")  # DRAFT|QUEUED|SENT|FAILED
    created_at: datetime = Field(default_factory=now)

class ImportBatchMetadata(SQLModel, table=True):
    __tablename__ = "import_batch_metadata"

    batch_id: str = Field(primary_key=True, index=True)
    content_hash: str = Field(index=True)
    sheet_name: str = Field(index=True)
    filename: str
    total_rows: int = Field(default=0)
    imported_rows: int = Field(default=0)
    quarantined_rows: int = Field(default=0)
    status: str = Field(default="STAGED", index=True)  # STAGED|PROMOTED|FAILED
    is_dry_run: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now)

class StagedRecord(SQLModel, table=True):
    __tablename__ = "staged_record"

    id: str = Field(default_factory=lambda: f"stg_{uuid.uuid4().hex[:10]}", primary_key=True)
    batch_id: str = Field(index=True)
    source_row_id: str = Field(index=True)
    sheet_name: str = Field(index=True)
    target_table: str = Field(index=True)
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="PENDING", index=True)  # PENDING|PROMOTED|REJECTED
    created_at: datetime = Field(default_factory=now)

