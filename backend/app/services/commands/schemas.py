# OWNER: P1
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CommandIntent(str, Enum):
    SHOW_IMPACT = "show_impact"
    FIND_ACCOMMODATION_FOR_UNPLACED = "find_accommodation_for_unplaced"
    AFFECTED_EVENTS_BY_EQUIPMENT = "affected_events_by_equipment"
    ALTERNATIVE_VENDORS_FOR_DIET = "alternative_vendors_for_diet"
    LIST_LATE_ARRIVALS = "list_late_arrivals"
    QUERY = "query"
    NAVIGATE = "navigate"


MUTATING_INTENTS = {
    CommandIntent.FIND_ACCOMMODATION_FOR_UNPLACED,
}


class ShowImpactParams(BaseModel):
    entity_type: str = Field(default="room", description="Entity category: room, property, venue, vendor, equipment")
    entity_id: str = Field(..., description="ID or natural name of entity (e.g. Hostel C, V01)")
    action: str = Field(default="close", description="Simulated action: close, cancel, shutdown, fail")


class FindAccommodationParams(BaseModel):
    plan_kind: str = Field(default="C", description="Plan variant to optimize (A, B, or C)")
    target_group: str = Field(default="all_unplaced", description="Target subset of participants to allocate")


class AffectedEventsByEquipmentParams(BaseModel):
    item: str = Field(..., description="Name or category of equipment (e.g. camera, microphone, projector)")


class AlternativeVendorsForDietParams(BaseModel):
    diet: str = Field(..., description="Dietary classification: Jain, Veg, Non-Veg, Halal, Vegan")


class ListLateArrivalsParams(BaseModel):
    after_time: str = Field(default="22:00", description="Cutoff time in HH:MM format (e.g. 22:00)")


class QueryParams(BaseModel):
    query: str = Field(..., description="Operational search or aggregation query")
    target_entity: Optional[str] = Field(default=None, description="Optional entity type context")


class NavigateParams(BaseModel):
    destination: str = Field(..., description="Target UI section or dashboard tab")
    route: Optional[str] = Field(default=None, description="Resolved web path")


class StructuredCommand(BaseModel):
    intent: CommandIntent
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_mutating: bool = Field(default=False)
    raw_text: str = Field(default="")


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    context: Optional[Dict[str, Any]] = Field(default=None)


class ParseResponseData(BaseModel):
    command: StructuredCommand
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    parser_mode: Literal["LLM", "OFFLINE_FALLBACK"]


class ExecuteRequest(BaseModel):
    command: StructuredCommand
    reason: Optional[str] = None
    confirmed: bool = False


class ExecuteResponseData(BaseModel):
    intent: CommandIntent
    status: Literal["EXECUTED", "PROPOSAL_CREATED", "REJECTED"]
    is_mutating: bool
    proposal_id: Optional[str] = None
    approval_required: bool = False
    change_set_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    impact: Optional[Dict[str, Any]] = None
    dry_run_result: Optional[Dict[str, Any]] = None
    message: str
    warnings: List[str] = Field(default_factory=list)
