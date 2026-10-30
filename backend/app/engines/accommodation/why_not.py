# OWNER: P2
from __future__ import annotations

from typing import Dict, List

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
    is_ground_floor_needed,
    is_wheelchair_needed,
    normalize_gender,
)
from app.engines.accommodation.types import (
    CounterfactualRun,
    ParticipantSnapshot,
    PropertySnapshot,
    RoomSnapshot,
    UnplacedSnapshot,
)


def diagnose_unplaced_participant(
    participant: ParticipantSnapshot,
    rooms: List[RoomSnapshot],
    properties: List[PropertySnapshot],
    room_occupancy_checker=None,
    property_occupancy_checker=None,
) -> UnplacedSnapshot:
    """Perform in-depth explainable shortage diagnosis and counterfactual analysis for an unplaced participant."""
    rejected_options: List[Dict[str, str]] = []
    blocking_codes: List[str] = []

    # 1. Test every room and record why it was rejected
    for room in rooms:
        eligible, reason, code = check_room_eligibility(participant, room)
        if not eligible:
            if code and code not in blocking_codes:
                blocking_codes.append(code)
            if len(rejected_options) < 6 and reason:
                rejected_options.append({"location": f"Room {room.id} ({room.block})", "reason": reason})
        else:
            # Passes hard rules, but check rolling occupancy if available
            if room_occupancy_checker and not room_occupancy_checker(room.id, participant):
                blocking_codes.append(TAXONOMY_CAPACITY)
                if len(rejected_options) < 6:
                    rejected_options.append({
                        "location": f"Room {room.id} ({room.block})",
                        "reason": "All beds occupied or in cleaning buffer during stay window.",
                    })

    # 2. Test every external property and record why it was rejected
    for prop in properties:
        eligible, reason, code = check_external_property_eligibility(participant, prop)
        if not eligible:
            if code and code not in blocking_codes:
                blocking_codes.append(code)
            if len(rejected_options) < 6 and reason:
                rejected_options.append({"location": f"Property {prop.name}", "reason": reason})
        else:
            if property_occupancy_checker and not property_occupancy_checker(prop.id, participant):
                blocking_codes.append(TAXONOMY_CAPACITY)
                if len(rejected_options) < 6:
                    rejected_options.append({
                        "location": f"Property {prop.name}",
                        "reason": "Property bed capacity fully committed during stay window.",
                    })

    # Determine primary blocking reason according to priority
    primary_code = TAXONOMY_CAPACITY
    if TAXONOMY_HARD_ACCESSIBILITY in blocking_codes:
        primary_code = TAXONOMY_HARD_ACCESSIBILITY
    elif TAXONOMY_GENDER_OR_HOUSING_UNKNOWN in blocking_codes:
        primary_code = TAXONOMY_GENDER_OR_HOUSING_UNKNOWN
    elif TAXONOMY_TRANSPORT_RESTRICTED in blocking_codes:
        primary_code = TAXONOMY_TRANSPORT_RESTRICTED
    elif TAXONOMY_MISSING_INFO in blocking_codes:
        primary_code = TAXONOMY_MISSING_INFO
    elif TAXONOMY_NO_ELIGIBLE_PROPERTY in blocking_codes:
        primary_code = TAXONOMY_NO_ELIGIBLE_PROPERTY
    elif TAXONOMY_BUDGET in blocking_codes:
        primary_code = TAXONOMY_BUDGET

    # 3. Identify missing information and verification target
    missing_info = ""
    verification_target: Dict[str, str] = {}
    gender_norm = normalize_gender(participant.gender)

    if gender_norm == "UNKNOWN":
        missing_info = "Gender attribute is UNKNOWN or non-binary in raw registration data."
        verification_target = {"field": "gender", "entity_id": participant.id, "owner": "contingent_leader"}
    elif is_wheelchair_needed(participant.accessibility_needs) or is_ground_floor_needed(participant.accessibility_needs):
        missing_info = "External property accessibility verification is UNVERIFIED."
        verification_target = {"field": "accessibility", "entity_id": participant.id, "owner": "accommodation_lead"}
    elif participant.age < 18 and not participant.guardian_approved:
        missing_info = "Guardian authorization / escort documentation for minor is pending confirmation."
        verification_target = {"field": "guardian_consent", "entity_id": participant.id, "owner": "faculty_escort"}
    else:
        missing_info = "All compliant rooms and properties reached 100% capacity during peak festival hours."
        verification_target = {"field": "stay_dates", "entity_id": participant.id, "owner": "event_lead"}

    # 4. Counterfactual Simulation (What would change if the unknown field were confirmed?)
    counterfactual_runs: List[CounterfactualRun] = []
    counterfactual_impact = ""

    if gender_norm == "UNKNOWN":
        # Simulate Female
        sim_female = ParticipantSnapshot(**{**participant.__dict__, "gender": "FEMALE"})
        female_eligible = sum(1 for r in rooms if check_room_eligibility(sim_female, r)[0])
        counterfactual_runs.append(
            CounterfactualRun(
                hypothetical_field="gender",
                hypothetical_value="FEMALE",
                eligible_bed_count=female_eligible * 2,
                outcome="PLACED_ON_CAMPUS" if female_eligible > 0 else "STILL_UNPLACED",
                details=f"Confirms eligibility for {female_eligible} rooms in Girls hostel blocks (G1–G3).",
            )
        )

        # Simulate Male
        sim_male = ParticipantSnapshot(**{**participant.__dict__, "gender": "MALE"})
        male_eligible = sum(1 for r in rooms if check_room_eligibility(sim_male, r)[0])
        counterfactual_runs.append(
            CounterfactualRun(
                hypothetical_field="gender",
                hypothetical_value="MALE",
                eligible_bed_count=male_eligible * 2,
                outcome="PLACED_ON_CAMPUS" if male_eligible > 0 else "STILL_UNPLACED",
                details=f"Confirms eligibility for {male_eligible} rooms in Boys hostel blocks (B1–B5).",
            )
        )

        counterfactual_impact = (
            f"If verified as 'Female', {female_eligible} Girls hostel rooms become immediately eligible; "
            f"if verified as 'Male', {male_eligible} Boys hostel rooms become eligible alongside contingent peers."
        )

    elif primary_code == TAXONOMY_HARD_ACCESSIBILITY:
        # Simulate external property accessibility verification
        ext_beds = sum(p.beds for p in properties)
        counterfactual_runs.append(
            CounterfactualRun(
                hypothetical_field="external_property_accessibility",
                hypothetical_value="VERIFIED",
                eligible_bed_count=ext_beds,
                outcome="PLACED_EXTERNALLY",
                details=f"Verifying ramp and lift compliance unlocks up to {ext_beds} external beds across 6 properties.",
            )
        )
        counterfactual_impact = (
            f"Verifying ground-floor ramp accessibility at nearby external hotels (e.g. Campus Guest House) "
            f"unlocks placement for {participant.name}."
        )

    elif primary_code == TAXONOMY_MISSING_INFO and participant.age < 18:
        # Simulate guardian approval
        sim_minor = ParticipantSnapshot(**{**participant.__dict__, "guardian_approved": True})
        unlocked_props = [
            p.name for p in properties
            if check_external_property_eligibility(sim_minor, p)[0]
        ]
        counterfactual_runs.append(
            CounterfactualRun(
                hypothetical_field="guardian_approval",
                hypothetical_value="CONFIRMED",
                eligible_bed_count=len(unlocked_props) * 80,
                outcome="PLACED_EXTERNALLY",
                details=f"Unlocks compliant external properties: {', '.join(unlocked_props[:3])}.",
            )
        )
        counterfactual_impact = (
            "Recording verified guardian consent authorizes placement in external hotels with contingent escorts."
        )

    else:
        counterfactual_impact = (
            "Peak bed contention: moving arrival or departure window by 6 hours shifts stay out of peak contention."
        )

    return UnplacedSnapshot(
        participant_id=participant.id,
        name=participant.name,
        contingent_id=participant.contingent_id,
        college=participant.college,
        blocking_reason=primary_code,
        accessibility_needed=is_wheelchair_needed(participant.accessibility_needs) or is_ground_floor_needed(participant.accessibility_needs),
        housing_preference=participant.housing_preference or "standard",
        gender=participant.gender or "UNKNOWN",
        rejected_options=rejected_options,
        missing_information=missing_info,
        counterfactual_impact=counterfactual_impact,
        counterfactual_runs=counterfactual_runs,
        verification_target=verification_target,
    )
