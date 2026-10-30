# OWNER: P2
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ParticipantSnapshot:
    id: str
    name: str
    college: str
    contingent_id: str
    gender: str  # MALE, FEMALE, NON_BINARY, PREFER_NOT_TO_SAY, UNKNOWN, BLANK
    age: int
    accessibility_needs: str  # none, wheelchair, ground_floor, visual_assistance, near_washroom
    housing_preference: str  # standard, single, privacy, unknown
    arrival_at: Optional[datetime]
    departure_at: Optional[datetime]
    accommodation_requested: str  # YES, NO, UNKNOWN
    is_contingent_leader: bool = False
    is_faculty_escort: bool = False
    guardian_approved: bool = False
    has_night_arrival: bool = False  # e.g., arrival after 22:00
    has_early_event: bool = False  # e.g., event starting before 08:00


@dataclass
class RoomSnapshot:
    id: str
    block: str
    floor: int
    capacity: int
    accessible: bool
    accessibility: str  # 'yes' | 'no'
    gender_class: str  # 'boys' | 'girls' | 'neutral'
    status: str = "available"  # available, maintenance, closed
    cleaning_status: str = "READY"


@dataclass
class PropertySnapshot:
    id: str
    name: str
    beds: int
    cost_per_bed_night: float
    distance_km: float
    transport_availability: str  # 'yes', 'limited', 'no'
    transport_limited: bool = False
    accessibility_verified: bool = False
    gender_suitability_verified: bool = False
    status: str = "ACTIVE"


@dataclass
class AssignmentExplanation:
    constraints_satisfied: List[str] = field(default_factory=list)
    soft_constraints_relaxed: List[Dict[str, Any]] = field(default_factory=list)
    rejected_alternatives: List[Dict[str, Any]] = field(default_factory=list)
    cost_inr: float = 0.0
    verification_status: str = "VERIFIED"
    approval_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraints_satisfied": self.constraints_satisfied,
            "soft_constraints_relaxed": self.soft_constraints_relaxed,
            "rejected_alternatives": self.rejected_alternatives,
            "cost_inr": self.cost_inr,
            "verification_status": self.verification_status,
            "approval_info": self.approval_info,
        }


@dataclass
class AssignmentSnapshot:
    participant_id: str
    resource_id: str  # Room ID or Property ID
    bed_key: str  # e.g., "B1-0-01:bed_1" or "EXT01:bed_5"
    is_external: bool
    start_at: datetime
    end_at: datetime
    cost_inr: float
    explanation: AssignmentExplanation


@dataclass
class CounterfactualRun:
    hypothetical_field: str
    hypothetical_value: str
    eligible_bed_count: int
    outcome: str  # PLACED_ON_CAMPUS, PLACED_EXTERNALLY, STILL_UNPLACED
    details: str


@dataclass
class UnplacedSnapshot:
    participant_id: str
    name: str
    contingent_id: str
    college: str
    blocking_reason: str  # Fixed taxonomy
    accessibility_needed: bool
    housing_preference: str
    gender: str
    rejected_options: List[Dict[str, str]] = field(default_factory=list)
    missing_information: str = ""
    counterfactual_impact: str = ""
    counterfactual_runs: List[CounterfactualRun] = field(default_factory=list)
    verification_target: Dict[str, str] = field(default_factory=dict)


@dataclass
class PlanMetrics:
    on_campus_placed: int = 0
    external_placed: int = 0
    unplaced_count: int = 0
    contingent_splits: int = 0
    total_cost_inr: float = 0.0
    safety_flags_count: int = 0
    accessibility_issues_count: int = 0
    relaxed_constraints_count: int = 0
    minors_external_count: int = 0


@dataclass
class PlanResult:
    plan_id: str
    kind: str  # 'A', 'B', 'C'
    name: str
    status: str
    metrics: PlanMetrics
    assignments: List[AssignmentSnapshot]
    unplaced: List[UnplacedSnapshot]
    plan_hash: str
    sacrifices_summary: str
    parameters_applied: Dict[str, Any]


@dataclass
class TimelinePoint:
    timestamp: datetime
    confirmed_demand: int
    possible_demand: int
    cleaning_beds: int
    available_supply: int


@dataclass
class DemandTimelineResult:
    total_participants_requesting: int
    valid_intervals_included: int
    invalid_intervals_count: int
    invalid_intervals: List[Dict[str, Any]]
    confirmed_demand_count: int
    possible_demand_count: int
    peak_simultaneous_demand: int
    peak_time: datetime
    timeline: List[TimelinePoint]
