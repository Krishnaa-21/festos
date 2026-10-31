# OWNER: P1
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class Participant(SQLModel, table=True):
    __tablename__ = "participant"

    id: str = Field(default_factory=lambda: f"par_{uuid.uuid4().hex[:10]}", primary_key=True)
    canonical_participant_id: Optional[str] = Field(default=None, index=True)
    source_row_id: Optional[str] = Field(default=None, index=True)
    contingent_id: Optional[str] = Field(default=None, foreign_key="contingent.id", index=True)

    name: str = Field(default="UNKNOWN")
    college: Optional[str] = Field(default=None, index=True)
    email: Optional[str] = Field(default=None, index=True)
    phone: Optional[str] = Field(default=None)
    gender: str = Field(default="UNKNOWN")  # UNKNOWN is first-class (Male|Female|Non-binary|Prefer not to say|UNKNOWN)
    diet: str = Field(default="UNKNOWN")    # UNKNOWN is first-class
    housing_preference: str = Field(default="UNKNOWN")
    accessibility_needs: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    accommodation_requested: str = Field(default="UNKNOWN") # Tri: YES|NO|UNKNOWN
    tshirt_size: Optional[str] = Field(default=None)

    arrival_at: Optional[datetime] = Field(default=None, index=True)
    departure_at: Optional[datetime] = Field(default=None)
    dob: Optional[str] = Field(default=None)
    age: Optional[int] = Field(default=None)
    role: str = Field(default="PARTICIPANT")  # PARTICIPANT|LEADER|ESCORT|JUDGE|VOLUNTEER|STAFF
    status: str = Field(default="EXPECTED", index=True) # EXPECTED|ARRIVED|CHECKED_IN|CHECKED_OUT|CANCELLED|NO_SHOW|WITHDRAWN|INVALID|MERGED

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

    @property
    def canonical_id(self) -> Optional[str]:
        return self.canonical_participant_id

class Contingent(SQLModel, table=True):
    __tablename__ = "contingent"

    id: str = Field(default_factory=lambda: f"ctg_{uuid.uuid4().hex[:8]}", primary_key=True)
    name: str = Field(index=True)
    code: str = Field(index=True)
    college: Optional[str] = Field(default=None, index=True)
    leader: Optional[str] = Field(default=None)
    escort: Optional[str] = Field(default=None)
    strength_declared: Optional[int] = Field(default=0)
    preferences: Optional[str] = Field(default=None)
    contact_name: Optional[str] = Field(default=None)
    contact_phone: Optional[str] = Field(default=None)
    contact_email: Optional[str] = Field(default=None)
    status: str = Field(default="ACTIVE")

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class Registration(SQLModel, table=True):
    __tablename__ = "registration"

    id: str = Field(default_factory=lambda: f"reg_{uuid.uuid4().hex[:10]}", primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    event_id: str = Field(foreign_key="event.id", index=True)
    team_id: Optional[str] = Field(default=None, index=True)
    team_name: Optional[str] = Field(default=None)
    status: str = Field(default="REGISTERED")
    registered_at: datetime = Field(default_factory=now)

    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class FieldVerification(SQLModel, table=True):
    __tablename__ = "field_verification"

    id: str = Field(default_factory=lambda: f"ver_{uuid.uuid4().hex[:10]}", primary_key=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    field: str = Field(index=True)
    status: str = Field(default="UNKNOWN")  # UNKNOWN|CLAIMED|VERIFIED
    value: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None)
    verified_by: Optional[str] = Field(default=None)
    verified_at: Optional[datetime] = Field(default=None)
    owner: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now)

class DuplicateCandidate(SQLModel, table=True):
    __tablename__ = "duplicate_candidate"

    id: str = Field(default_factory=lambda: f"dup_{uuid.uuid4().hex[:10]}", primary_key=True)
    participant_a_id: str = Field(index=True)
    participant_b_id: str = Field(index=True)
    score: float = Field(default=0.0)
    classification: str = Field(default="POSSIBLE", index=True)  # EXACT|LIKELY|POSSIBLE
    reasons: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="PENDING", index=True)  # PENDING|RESOLVED|IGNORED
    created_at: datetime = Field(default_factory=now)

class MergeRecord(SQLModel, table=True):
    __tablename__ = "merge_record"

    id: str = Field(default_factory=lambda: f"mrg_{uuid.uuid4().hex[:10]}", primary_key=True)
    canonical_participant_id: str = Field(index=True)
    merged_participant_id: str = Field(index=True)
    merge_details: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    reason: Optional[str] = Field(default=None)
    merged_by: str = Field(default="SYSTEM")
    merged_at: datetime = Field(default_factory=now)
    is_reverted: bool = Field(default=False)
    reverted_at: Optional[datetime] = Field(default=None)
    reverted_by: Optional[str] = Field(default=None)

class RawRecord(SQLModel, table=True):
    __tablename__ = "raw_record"

    id: str = Field(default_factory=lambda: f"raw_{uuid.uuid4().hex[:10]}", primary_key=True)
    batch_id: Optional[str] = Field(default=None, index=True)
    source_row_id: Optional[str] = Field(default=None)
    source_sheet: Optional[str] = Field(default=None)
    raw_payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)

class QuarantineRow(SQLModel, table=True):
    __tablename__ = "quarantine_row"

    id: str = Field(default_factory=lambda: f"qrn_{uuid.uuid4().hex[:10]}", primary_key=True)
    batch_id: Optional[str] = Field(default=None, index=True)
    reason: str = Field(default="UNKNOWN_ERROR")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)

class ImportBatch(SQLModel, table=True):
    __tablename__ = "import_batch"

    id: str = Field(default_factory=lambda: f"imp_{uuid.uuid4().hex[:8]}", primary_key=True)
    filename: str
    total_rows: int = Field(default=0)
    imported_rows: int = Field(default=0)
    quarantined_rows: int = Field(default=0)
    status: str = Field(default="COMPLETED")
    imported_at: datetime = Field(default_factory=now)
