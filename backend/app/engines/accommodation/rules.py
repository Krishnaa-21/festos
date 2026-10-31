# OWNER: P2
from __future__ import annotations

from datetime import time
from typing import Any, Optional, Tuple

from app.engines.accommodation.types import (
    ParticipantSnapshot,
    PropertySnapshot,
    RoomSnapshot,
)

# Fixed taxonomy of shortage blocking reasons per Task 6
TAXONOMY_HARD_ACCESSIBILITY = "HARD_ACCESSIBILITY"
TAXONOMY_GENDER_OR_HOUSING_UNKNOWN = "GENDER_OR_HOUSING_UNKNOWN"
TAXONOMY_TRANSPORT_RESTRICTED = "TRANSPORT_RESTRICTED"
TAXONOMY_NO_ELIGIBLE_PROPERTY = "NO_ELIGIBLE_PROPERTY"
TAXONOMY_BUDGET = "BUDGET"
TAXONOMY_MISSING_INFO = "MISSING_INFO"
TAXONOMY_CAPACITY = "CAPACITY"

# Normalized gender categories
MALE_VARIANTS = {"MALE", "BOY", "MAN", "M"}
FEMALE_VARIANTS = {"FEMALE", "GIRL", "WOMAN", "F"}
UNKNOWN_GENDER_VARIANTS = {
    "NON-BINARY",
    "NON_BINARY",
    "PREFER NOT TO SAY",
    "PREFER_NOT_TO_SAY",
    "UNKNOWN",
    "BLANK",
    "",
}


def _accessibility_text(accessibility_needs: Any) -> str:
    """Normalize legacy strings and the canonical accessibility JSON object."""
    if isinstance(accessibility_needs, dict):
        needs = accessibility_needs.get("needs", [])
        if not isinstance(needs, list):
            needs = [needs]
        flags = [key.replace("is_", "").replace("_", " ")
                 for key in ("is_wheelchair", "is_ground_floor")
                 if accessibility_needs.get(key)]
        return " ".join(str(item) for item in [*needs, *flags])
    return str(accessibility_needs or "")


def is_wheelchair_needed(accessibility_needs: Any) -> bool:
    """Check if participant explicitly requires a wheelchair-accessible room."""
    norm = _accessibility_text(accessibility_needs).lower().replace("-", " ").strip()
    return "wheelchair" in norm or norm in ("yes", "accessible")


def is_ground_floor_needed(accessibility_needs: Any) -> bool:
    """Check if participant explicitly requires ground-floor accommodation."""
    norm = _accessibility_text(accessibility_needs).lower().replace("-", " ").strip()
    return "ground" in norm or "stairs" in norm


def is_manual_verification_accessibility_needed(accessibility_needs: Any) -> bool:
    """Check if participant has accessibility requirements that cannot be auto-satisfied.

    Near-washroom and visual-assistance needs -> NEEDS_MANUAL_VERIFICATION per Task 3.
    """
    norm = _accessibility_text(accessibility_needs).lower().replace("-", " ").strip()
    return "visual" in norm or "washroom" in norm or "toilet" in norm or "bathroom" in norm


def is_single_or_privacy_housing_needed(housing_preference: str) -> bool:
    """Check if participant requested a single or private room."""
    norm = (housing_preference or "").lower().strip()
    return norm in ("single", "privacy", "private")


def normalize_gender(gender_str: str) -> str:
    """Classify gender into MALE, FEMALE, or UNKNOWN/NON_BINARY."""
    norm = (gender_str or "").strip().upper()
    if norm in MALE_VARIANTS:
        return "MALE"
    if norm in FEMALE_VARIANTS:
        return "FEMALE"
    return "UNKNOWN"


def check_room_eligibility(
    participant: ParticipantSnapshot,
    room: RoomSnapshot,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if an on-campus room satisfies all hard constraints for the participant.

    Returns (eligible: bool, violation_message: Optional[str], failure_code: Optional[str]).
    """
    # 1. Room availability & status
    if (room.status or "").lower() not in ("available", "open"):
        return False, f"Room {room.id} is currently {room.status} (not available).", TAXONOMY_CAPACITY

    # 2. Wheelchair accessibility: wheelchair need -> accessible room only
    needs_wheelchair = is_wheelchair_needed(participant.accessibility_needs)
    if needs_wheelchair:
        if not (room.accessible or (room.accessibility or "").lower() == "yes"):
            return False, f"Room {room.id} is not wheelchair accessible.", TAXONOMY_HARD_ACCESSIBILITY

    # 3. Ground floor need: ground floor only (floor 0)
    needs_ground = is_ground_floor_needed(participant.accessibility_needs)
    if needs_ground:
        if room.floor != 0:
            return False, f"Room {room.id} is on floor {room.floor} (ground floor required).", TAXONOMY_HARD_ACCESSIBILITY

    # 4. Near-washroom & visual-assistance needs: NEEDS_MANUAL_VERIFICATION
    if is_manual_verification_accessibility_needed(participant.accessibility_needs):
        return (
            False,
            f"Accessibility request '{participant.accessibility_needs}' requires manual inspection; cannot auto-place.",
            TAXONOMY_HARD_ACCESSIBILITY,
        )

    # 5. Single / privacy room: standard multi-bed hostel rooms are ineligible
    if is_single_or_privacy_housing_needed(participant.housing_preference):
        if room.capacity > 1:
            return False, f"Room {room.id} has capacity {room.capacity}; single/private room required.", TAXONOMY_NO_ELIGIBLE_PROPERTY

    # 6. Gender-appropriate allocation:
    gender = normalize_gender(participant.gender)
    room_gender = (room.gender_class or "").lower()

    if gender == "MALE":
        if room_gender != "boys":
            return False, f"Room {room.id} is in {room.gender_class} block; participant is Male.", TAXONOMY_NO_ELIGIBLE_PROPERTY
    elif gender == "FEMALE":
        if room_gender != "girls":
            return False, f"Room {room.id} is in {room.gender_class} block; participant is Female.", TAXONOMY_NO_ELIGIBLE_PROPERTY
    else:
        # Non-binary, prefer-not-to-say, blank, or UNKNOWN gender
        # NEVER put in a gendered block automatically! Eligible only for neutral/single room.
        if room_gender in ("boys", "girls"):
            return (
                False,
                f"Participant gender is unconfirmed/non-binary; ineligible for gendered {room_gender} block.",
                TAXONOMY_GENDER_OR_HOUSING_UNKNOWN,
            )

    return True, None, None


def check_external_property_eligibility(
    participant: ParticipantSnapshot,
    prop: PropertySnapshot,
    external_property_accessibility_verified: bool = False,
    external_property_gender_verified: bool = False,
    minor_age_threshold: int = 18,
    late_night_start: time = time(22, 0),
    early_morning_end: time = time(8, 0),
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if an external property satisfies hard safety, accessibility, and transport constraints.

    Returns (eligible: bool, violation_message: Optional[str], failure_code: Optional[str]).
    """
    # 1. Active status
    if (prop.status or "").upper() != "ACTIVE":
        return False, f"Property {prop.name} is {prop.status} (not active).", TAXONOMY_NO_ELIGIBLE_PROPERTY

    # 2. Accessibility requirement: external properties lack verified accessibility
    needs_wheelchair = is_wheelchair_needed(participant.accessibility_needs)
    needs_ground = is_ground_floor_needed(participant.accessibility_needs)
    if needs_wheelchair or needs_ground or is_manual_verification_accessibility_needed(participant.accessibility_needs):
        if not prop.accessibility_verified and not external_property_accessibility_verified:
            return (
                False,
                f"External property {prop.name} lacks verified accessibility compliance.",
                TAXONOMY_HARD_ACCESSIBILITY,
            )

    # 3. Unconfirmed gender: external property gender suitability unverified
    gender = normalize_gender(participant.gender)
    if gender == "UNKNOWN":
        if not prop.gender_suitability_verified and not external_property_gender_verified:
            return (
                False,
                f"External property {prop.name} lacks verified gender-neutral accommodation.",
                TAXONOMY_GENDER_OR_HOUSING_UNKNOWN,
            )

    # 4. Minor safeguards (age < minor_age_threshold):
    is_minor = participant.age < minor_age_threshold
    if is_minor:
        # Never placed in limited-transport property
        if prop.transport_limited or (prop.transport_availability or "").lower() == "limited":
            return (
                False,
                f"Minor (<{minor_age_threshold}) cannot be placed in limited-transport property {prop.name}.",
                TAXONOMY_TRANSPORT_RESTRICTED,
            )
        # Minors placed externally only when guardian approval and escort conditions are modeled
        if not participant.guardian_approved and not participant.is_faculty_escort:
            # We flag with missing guardian consent/escort
            return (
                False,
                f"Minor (<{minor_age_threshold}) requires guardian/escort verification for external stay.",
                TAXONOMY_MISSING_INFO,
            )

    # 5. Transport window & night arrival (Rule 6):
    # If property has limited transport, arrivals after 22:00 or events before 08:00 are ineligible
    if prop.transport_limited or (prop.transport_availability or "").lower() == "limited":
        if participant.arrival_at:
            arr_time = participant.arrival_at.time()
            if arr_time >= late_night_start or arr_time < early_morning_end:
                return (
                    False,
                    f"Arrival at {arr_time.strftime('%H:%M')} is outside transport window for {prop.name}.",
                    TAXONOMY_TRANSPORT_RESTRICTED,
                )
        if participant.has_night_arrival or participant.has_early_event:
            return (
                False,
                f"Night schedule / early event restricts assignment to limited-transport property {prop.name}.",
                TAXONOMY_TRANSPORT_RESTRICTED,
            )

    return True, None, None
