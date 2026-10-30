# OWNER: P1
# Import all model modules so SQLModel metadata discovers every table
from app.models.accommodation import (
    AccommodationPlan,
    BedReallocationSuggestion,
    CheckinOperationRecord,
    ExternalProperty,
    Room,
    StayAssignment,
)
from app.models.audit import (
    Approval,
    AuditEvent,
    BreakGlassGrant,
    Override,
    User,
)
from app.models.change import Assumption, ChangeSet, IdempotencyKey, Scenario
from app.models.decisions import DecisionCard
from app.models.events import (
    Conflict,
    Event,
    EventRequirement,
    EventSession,
    ScheduleVersion,
)
from app.models.inventory import (
    EntitlementPolicy,
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
    MerchClaim,
    Transfer,
)
from app.models.ops import Incident, NotificationDraft, TravelTime, Venue
from app.models.participants import (
    Contingent,
    DuplicateCandidate,
    FieldVerification,
    ImportBatch,
    MergeRecord,
    Participant,
    QuarantineRow,
    RawRecord,
    Registration,
)
from app.models.staff import Shift, Staff
from app.models.transport import (
    EscortAssignment,
    GuardianApproval,
    Route,
    ShuttleAssignment,
    ShuttleRun,
    Transport,
)
from app.models.vendors import MealSlot, Vendor, VendorAssignment

__all__ = [
    "Participant",
    "Contingent",
    "Registration",
    "FieldVerification",
    "DuplicateCandidate",
    "MergeRecord",
    "RawRecord",
    "QuarantineRow",
    "ImportBatch",
    "Event",
    "EventRequirement",
    "EventSession",
    "ScheduleVersion",
    "Conflict",
    "InventoryLocation",
    "InventoryItem",
    "InventoryMovement",
    "MerchClaim",
    "Staff",
    "Shift",
    "Transport",
    "Route",
    "ShuttleRun",
    "ShuttleAssignment",
    "EscortAssignment",
    "GuardianApproval",
    "ChangeSet",
    "IdempotencyKey",
    "Scenario",
    "Assumption",
    "Room",
    "ExternalProperty",
    "StayAssignment",
    "AccommodationPlan",
    "BedReallocationSuggestion",
    "CheckinOperationRecord",
    "Vendor",
    "MealSlot",
    "VendorAssignment",
    "Venue",
    "TravelTime",
    "Incident",
    "NotificationDraft",
    "AuditEvent",
    "User",
    "BreakGlassGrant",
    "Approval",
    "Override",
    "DecisionCard",
]
