# OWNER: P2
from app.engines.accommodation.demand import (
    compute_bed_demand_timeline,
    partition_demand,
    validate_stay_interval,
)
from app.engines.accommodation.planner import AccommodationPlanner
from app.engines.accommodation.reports import (
    generate_accommodation_summary_csv,
    generate_bed_demand_timeline_csv,
    generate_decision_card,
    generate_plan_csv,
    generate_shortage_report_csv,
)
from app.engines.accommodation.rules import (
    TAXONOMY_BUDGET,
    TAXONOMY_CAPACITY,
    TAXONOMY_GENDER_OR_HOUSING_UNKNOWN,
    TAXONOMY_HARD_ACCESSIBILITY,
    TAXONOMY_MISSING_INFO,
    TAXONOMY_NO_ELIGIBLE_PROPERTY,
    TAXONOMY_TRANSPORT_RESTRICTED,
    check_external_property_eligibility,
    check_room_eligibility,
)
from app.engines.accommodation.types import (
    AssignmentExplanation,
    AssignmentSnapshot,
    CounterfactualRun,
    DemandTimelineResult,
    ParticipantSnapshot,
    PlanMetrics,
    PlanResult,
    PropertySnapshot,
    RoomSnapshot,
    TimelinePoint,
    UnplacedSnapshot,
)
from app.engines.accommodation.why_not import diagnose_unplaced_participant

__all__ = [
    "AccommodationPlanner",
    "AssignmentExplanation",
    "AssignmentSnapshot",
    "CounterfactualRun",
    "DemandTimelineResult",
    "ParticipantSnapshot",
    "PlanMetrics",
    "PlanResult",
    "PropertySnapshot",
    "RoomSnapshot",
    "TimelinePoint",
    "UnplacedSnapshot",
    "TAXONOMY_BUDGET",
    "TAXONOMY_CAPACITY",
    "TAXONOMY_GENDER_OR_HOUSING_UNKNOWN",
    "TAXONOMY_HARD_ACCESSIBILITY",
    "TAXONOMY_MISSING_INFO",
    "TAXONOMY_NO_ELIGIBLE_PROPERTY",
    "TAXONOMY_TRANSPORT_RESTRICTED",
    "check_external_property_eligibility",
    "check_room_eligibility",
    "compute_bed_demand_timeline",
    "diagnose_unplaced_participant",
    "generate_accommodation_summary_csv",
    "generate_bed_demand_timeline_csv",
    "generate_decision_card",
    "generate_plan_csv",
    "generate_shortage_report_csv",
    "partition_demand",
    "validate_stay_interval",
]
