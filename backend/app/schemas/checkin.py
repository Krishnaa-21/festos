# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CheckinRequest(BaseModel):
    client_op_id: Optional[str] = None
    participant_id: str
    wristband_code: Optional[str] = None
    verified_fields: Optional[Dict[str, Any]] = None
    desk_operator: Optional[str] = None
    override_room_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    client_op_id: Optional[str] = None
    participant_id: str
    bed_id: Optional[str] = None
    checkout_notes: Optional[str] = None


class ArrivalUpdateRequest(BaseModel):
    updated_arrival_at: str
    delay_reason: Optional[str] = None
    transport_mode: Optional[str] = None


class OfflineOperation(BaseModel):
    client_op_id: str
    op_type: str  # CHECKIN | CHECKOUT
    participant_id: str
    timestamp: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class SyncBatchRequest(BaseModel):
    device_id: Optional[str] = None
    sync_batch_id: str
    operations: List[OfflineOperation]


class SyncOperationResult(BaseModel):
    client_op_id: str
    status: str  # APPLIED | DUPLICATE_IGNORED | CONFLICT
    message: str


class SyncBatchResponseData(BaseModel):
    batch_id: str
    processed_count: int
    applied_count: int
    duplicate_count: int
    conflict_count: int
    results: List[SyncOperationResult]


class ReallocationSuggestionSchema(BaseModel):
    suggestion_id: str
    freed_bed_key: str
    freed_room_id: Optional[str] = None
    freed_by_participant_id: str
    reason: str
    suggested_participant_id: Optional[str] = None
    suggested_participant_name: Optional[str] = None
    contingent_id: Optional[str] = None
    priority_score: float
    cohesion_benefit: Optional[str] = None
    created_at: str
