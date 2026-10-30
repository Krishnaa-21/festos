# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GeneratePlanParams(BaseModel):
    cleaning_buffer_minutes: int = 180
    max_distance_km: float = 15.0
    solver_timeout_sec: int = 10
    weights: Optional[Dict[str, float]] = Field(default_factory=lambda: {"cohesion": 0.5, "cost": 0.3, "travel": 0.2})
    allow_split_contingents: bool = True


class GeneratePlanRequest(BaseModel):
    kinds: List[str] = Field(default_factory=lambda: ["A", "B", "C"])
    params: Optional[GeneratePlanParams] = None
    # Support alternate frontend format
    kind: Optional[str] = None
    cleaning_buffer_minutes: Optional[int] = None
    max_distance_km: Optional[float] = None
    weights: Optional[Dict[str, float]] = None


class AccommodationPlanSchema(BaseModel):
    plan_id: str
    kind: str
    name: str
    status: str
    on_campus_placed: int
    external_placed: int
    unplaced_count: int
    contingent_splits: int
    total_cost_inr: float
    safety_flags_count: int
    accessibility_issues_count: int
    relaxed_constraints_count: int
    minors_external_count: int
    plan_hash: Optional[str] = None
    sacrifices_summary: Optional[str] = None
    parameters_applied: Optional[Dict[str, Any]] = None
    created_at: str


class PlansResponseData(BaseModel):
    plans: List[AccommodationPlanSchema]
    budget_ceiling_inr: Optional[float] = None
    is_budget_unset: bool = True


class ShortageGroupSchema(BaseModel):
    reason_code: str
    title: str
    count: int
    description: str
    affected_contingents: List[str]
    criticality: str  # LOW, MEDIUM, HIGH, CRITICAL


class UnplacedItemSchema(BaseModel):
    participant_id: str
    name: str
    contingent_id: str
    college: str
    blocking_reason: str
    accessibility_needed: bool
    housing_preference: str
    gender: str
    arrival_at: Optional[str] = None
    departure_at: Optional[str] = None


class ShortagesResponseData(BaseModel):
    total_unplaced: int
    grouped_by_reason: List[ShortageGroupSchema]
    unplaced_items: List[UnplacedItemSchema]


class WhyNotResponseData(BaseModel):
    participant_id: str
    name: str
    contingent_id: str
    plan_id: str
    blocking_requirement: str
    blocking_reason_code: str
    missing_information: str
    rejected_options: List[Dict[str, str]]
    counterfactual_impact: str
    counterfactual_runs: List[Dict[str, Any]]
    verification_target: Dict[str, str]


class TimelinePointSchema(BaseModel):
    timestamp: str
    confirmed_demand: int
    possible_demand: int
    cleaning_beds: int
    available_supply: int


class DemandTimelineResponseData(BaseModel):
    total_participants_requesting: int
    valid_intervals_included: int
    invalid_intervals_count: int
    invalid_intervals: List[Dict[str, Any]]
    confirmed_demand_count: int
    possible_demand_count: int
    peak_simultaneous_demand: int
    peak_time: str
    timeline: List[TimelinePointSchema]


class RoomItemSchema(BaseModel):
    id: str
    block: str
    floor: int
    capacity: int
    accessible: bool
    accessibility: str
    gender_class: str
    status: str
    cleaning_status: str
    cleaning_ready_at: Optional[str] = None


class PropertyItemSchema(BaseModel):
    id: str
    name: str
    beds: int
    cost_per_bed_night: float
    distance_km: float
    transport_availability: str
    transport_limited: bool
    accessibility_verified: bool
    gender_suitability_verified: bool
    status: str
