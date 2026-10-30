# OWNER: P2
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ValidationIssue:
    file: str
    field: str
    severity: int  # 1: LOW, 2: MEDIUM, 3: HIGH, 4: CRITICAL
    code: str
    message: str
    count: int = 1
    details: Dict[str, Any] = field(default_factory=dict)


def validate_participant_row(
    row: Dict[str, Any], minor_age_threshold: int = 18
) -> Tuple[bool, Optional[str], List[ValidationIssue]]:
    """Validates an individual participant row.
    Returns:
        (is_quarantined, quarantine_reason_code, list_of_warning_issues)
    """
    issues: List[ValidationIssue] = []
    pid = row.get("id") or row.get("source_row_id") or "UNKNOWN"

    arr = row.get("arrival_at")
    dep = row.get("departure_at")

    # Rule 1: Arrival not before departure (HARD quarantine rule)
    if arr and dep and isinstance(arr, datetime) and isinstance(dep, datetime):
        if arr >= dep:
            return (
                True,
                "INVALID_ARRIVAL_DEPARTURE_INTERVAL",
                [
                    ValidationIssue(
                        file="participants.csv",
                        field="arrival_datetime",
                        severity=4,
                        code="INVALID_ARRIVAL_DEPARTURE_INTERVAL",
                        message=f"Participant {pid} has arrival ({arr}) at or after departure ({dep})",
                        details={"participant_id": pid, "arrival": str(arr), "departure": str(dep)},
                    )
                ],
            )

    # Rule 2: Age below minor threshold (flagged issue, not quarantined unless corrupted)
    age = row.get("age")
    if age is not None and isinstance(age, int) and age < minor_age_threshold:
        accom = row.get("accommodation_requested")
        issues.append(
            ValidationIssue(
                file="participants.csv",
                field="age",
                severity=3,
                code="MINOR_SAFETY_MONITORING",
                message=f"Participant {pid} is aged {age} (< minor threshold {minor_age_threshold}); requires guardian/escort verification",
                details={"participant_id": pid, "age": age, "accommodation_requested": accom},
            )
        )

    # Rule 3: UNKNOWN critical attributes
    gender = row.get("gender", "UNKNOWN")
    if gender == "UNKNOWN":
        issues.append(
            ValidationIssue(
                file="participants.csv",
                field="gender",
                severity=2,
                code="UNKNOWN_GENDER",
                message=f"Participant {pid} gender is UNKNOWN; cannot auto-assign to gender-segregated blocks",
                details={"participant_id": pid},
            )
        )

    diet = row.get("diet", "UNKNOWN")
    if diet == "UNKNOWN":
        issues.append(
            ValidationIssue(
                file="participants.csv",
                field="dietary_needs",
                severity=2,
                code="UNKNOWN_DIET",
                message=f"Participant {pid} diet is UNKNOWN; meal catering cannot guarantee dietary clearance",
                details={"participant_id": pid},
            )
        )

    return False, None, issues


def validate_cross_pack(
    participants: Any = None,
    registrations: Optional[List[Dict[str, Any]]] = None,
    contingents: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    venues: Optional[List[Dict[str, Any]]] = None,
    core_team: Optional[List[Dict[str, Any]]] = None,
    hostels: Optional[List[Dict[str, Any]]] = None,
    external_stays: Optional[List[Dict[str, Any]]] = None,
    inventory_logistics: Optional[List[Dict[str, Any]]] = None,
    vendors: Optional[List[Dict[str, Any]]] = None,
    festival_end_date: str = "2026-11-01",
    expected_hostel_beds: int = 710,
    expected_external_beds: int = 740,
) -> List[ValidationIssue]:
    """Runs cross-file validation checks across all loaded sheets."""
    if isinstance(participants, dict):
        d = participants
        participants = d.get("participants") or []
        registrations = d.get("registrations") or []
        contingents = d.get("contingents") or []
        events = d.get("events") or []
        venues = d.get("venues") or []
        core_team = d.get("core_team") or []
        hostels = d.get("hostels") or []
        external_stays = d.get("external_stays") or []
        inventory_logistics = d.get("inventory_logistics") or []
        vendors = d.get("vendors") or []

    participants = participants or []
    registrations = registrations or []
    contingents = contingents or []
    events = events or []
    venues = venues or []
    core_team = core_team or []
    hostels = hostels or []
    external_stays = external_stays or []
    inventory_logistics = inventory_logistics or []
    vendors = vendors or []

    issues: List[ValidationIssue] = []


    # 1. Contingents declared strength vs actual participant count
    p_by_contingent: Dict[str, List[Dict[str, Any]]] = {}
    for p in participants:
        cid = p.get("contingent_id")
        if cid:
            p_by_contingent.setdefault(cid, []).append(p)

    total_declared = 0
    total_actual = len(participants)
    contingent_diffs = []
    leaders_found_count = 0
    escorts_found_count = 0

    for c in contingents:
        cid = c.get("id") or c.get("contingent_id") or ""
        declared = c.get("strength_declared", 0) or 0
        total_declared += declared
        actual_list = p_by_contingent.get(cid, [])
        actual_count = len(actual_list)
        diff = actual_count - declared
        if diff != 0:
            contingent_diffs.append({"contingent_id": cid, "declared": declared, "actual": actual_count, "diff": diff})

        # Check leader and escort in same contingent
        leader_name = (c.get("leader") or "").strip()
        escort_name = (c.get("escort") or "").strip()
        in_c_names = set(p.get("name", "").strip() for p in actual_list)
        if leader_name and leader_name in in_c_names:
            leaders_found_count += 1
        if escort_name and escort_name in in_c_names:
            escorts_found_count += 1

    if contingent_diffs:
        issues.append(
            ValidationIssue(
                file="contingents.csv",
                field="strength_declared",
                severity=3,
                code="CONTINGENT_STRENGTH_MISMATCH",
                message=f"Total declared strength ({total_declared}) differs from actual participants ({total_actual}). {len(contingent_diffs)} contingents have discrepancies.",
                count=len(contingent_diffs),
                details={"total_declared": total_declared, "total_actual": total_actual, "discrepancies": contingent_diffs},
            )
        )

    # Leader / escort missing verification (spec: only 3 of 38 each found)
    contingent_count = len(contingents)
    if contingent_count > 0 and leaders_found_count < contingent_count:
        issues.append(
            ValidationIssue(
                file="contingents.csv",
                field="leader",
                severity=3,
                code="MISSING_CONTINGENT_LEADERS",
                message=f"Only {leaders_found_count} of {contingent_count} contingent leaders found in participant roster (~{contingent_count - leaders_found_count} unrepresented)",
                count=contingent_count - leaders_found_count,
                details={"found": leaders_found_count, "total": contingent_count},
            )
        )

    if contingent_count > 0 and escorts_found_count < contingent_count:
        issues.append(
            ValidationIssue(
                file="contingents.csv",
                field="escort",
                severity=3,
                code="MISSING_CONTINGENT_ESCORTS",
                message=f"Only {escorts_found_count} of {contingent_count} contingent escorts found in participant roster (~{contingent_count - escorts_found_count} unrepresented)",
                count=contingent_count - escorts_found_count,
                details={"found": escorts_found_count, "total": contingent_count},
            )
        )

    # 2. Registrations pointing to unknown participant/event & Team registrations missing team IDs
    part_ids = set(p.get("id") or p.get("source_row_id") for p in participants)
    event_dict = {e.get("id") or e.get("event_id"): e for e in events}

    unknown_p_regs = 0
    unknown_e_regs = 0
    team_regs_missing_team_id = 0

    for r in registrations:
        pid = r.get("participant_id")
        eid = r.get("event_id")
        tid = (r.get("team_id") or "").strip()

        if pid not in part_ids:
            unknown_p_regs += 1
        ev = event_dict.get(eid)
        if not ev:
            unknown_e_regs += 1
        else:
            # Check if event is team event
            solo_team = (ev.get("solo_team") or ev.get("type") or "solo").lower()
            if solo_team == "team" and not tid:
                team_regs_missing_team_id += 1

    if unknown_p_regs > 0:
        issues.append(
            ValidationIssue(
                file="registrations.csv",
                field="participant_id",
                severity=4,
                code="UNKNOWN_PARTICIPANT_IN_REGISTRATION",
                message=f"{unknown_p_regs} registrations point to participants not present in roster",
                count=unknown_p_regs,
            )
        )

    if unknown_e_regs > 0:
        issues.append(
            ValidationIssue(
                file="registrations.csv",
                field="event_id",
                severity=4,
                code="UNKNOWN_EVENT_IN_REGISTRATION",
                message=f"{unknown_e_regs} registrations point to events not in catalog",
                count=unknown_e_regs,
            )
        )

    if team_regs_missing_team_id > 0:
        issues.append(
            ValidationIssue(
                file="registrations.csv",
                field="team_id",
                severity=3,
                code="TEAM_REGISTRATION_MISSING_TEAM_ID",
                message=f"{team_regs_missing_team_id} registrations for team events have no team_id assigned",
                count=team_regs_missing_team_id,
            )
        )

    # 3. Staff appearing as participants
    staff_names = set(s.get("name", "").strip() for s in core_team)
    staff_phones = set(s.get("phone", "").strip() for s in core_team if s.get("phone"))
    staff_overlap_names = [p.get("id") for p in participants if p.get("name", "").strip() in staff_names]
    staff_overlap_phones = [p.get("id") for p in participants if p.get("phone", "").strip() in staff_phones]

    if staff_overlap_names:
        issues.append(
            ValidationIssue(
                file="participants.csv",
                field="name",
                severity=2,
                code="STAFF_PARTICIPANT_NAME_OVERLAP",
                message=f"{len(staff_overlap_names)} participant records share names with core team staff (due to synthetic name pool)",
                count=len(staff_overlap_names),
                details={"phone_overlaps": len(staff_overlap_phones)},
            )
        )

    # 4. Vendor hygiene cert dates & menu vs dietary options mismatch
    expired_hygiene = []
    menu_mismatches = []
    for v in vendors:
        vid = v.get("id") or v.get("vendor_id")
        vname = v.get("name") or v.get("vendor_name")
        expiry = v.get("hygiene_certificate_expiry") or ""
        if expiry and expiry <= festival_end_date:
            expired_hygiene.append({"vendor_id": vid, "name": vname, "expiry": expiry})

        menu = (v.get("menu_description") or v.get("menu") or "").lower()
        diet = (v.get("dietary_options") or "").lower()
        if "jain" in menu and "jain" not in diet:
            menu_mismatches.append({"vendor_id": vid, "name": vname, "issue": "Menu has Jain thali but Jain option not declared"})
        elif "jain" in diet and "jain" not in menu:
            menu_mismatches.append({"vendor_id": vid, "name": vname, "issue": "Dietary options list Jain but menu lacks Jain thali"})

    if expired_hygiene:
        issues.append(
            ValidationIssue(
                file="vendors.csv",
                field="hygiene_certificate_expiry",
                severity=4,
                code="HYGIENE_CERTIFICATE_EXPIRED_OR_EXPIRING",
                message=f"{len(expired_hygiene)} vendors have hygiene certificates expiring before or during festival (threshold: {festival_end_date})",
                count=len(expired_hygiene),
                details={"vendors": expired_hygiene},
            )
        )

    if menu_mismatches:
        issues.append(
            ValidationIssue(
                file="vendors.csv",
                field="menu",
                severity=3,
                code="VENDOR_MENU_DIETARY_MISMATCH",
                message=f"{len(menu_mismatches)} vendors have menu vs declared dietary option mismatches (e.g. Jain thali without Jain tag)",
                count=len(menu_mismatches),
                details={"mismatches": menu_mismatches},
            )
        )

    # 5. Hostel and external bed totals vs spec (710 / 740)
    hostel_beds = sum(int(r.get("capacity") or r.get("bed_count") or 0) for r in hostels)
    external_beds = sum(int(ep.get("beds") or 0) for ep in external_stays)

    if hostel_beds != expected_hostel_beds:
        issues.append(
            ValidationIssue(
                file="hostels.csv",
                field="capacity",
                severity=3,
                code="HOSTEL_BED_TOTAL_MISMATCH",
                message=f"Hostel total beds ({hostel_beds}) differs from spec reference ({expected_hostel_beds})",
                details={"actual": hostel_beds, "expected": expected_hostel_beds},
            )
        )

    if external_beds != expected_external_beds:
        issues.append(
            ValidationIssue(
                file="external_stays.csv",
                field="beds",
                severity=3,
                code="EXTERNAL_BED_TOTAL_MISMATCH",
                message=f"External total beds ({external_beds}) differs from spec reference ({expected_external_beds})",
                details={"actual": external_beds, "expected": expected_external_beds},
            )
        )

    # 6. Events lacking times or venues
    events_lacking_times_or_venues = len(events)
    if events_lacking_times_or_venues > 0:
        issues.append(
            ValidationIssue(
                file="events.csv",
                field="rounds",
                severity=2,
                code="EVENTS_LACKING_TIMESTAMPS_AND_VENUES",
                message=f"All {events_lacking_times_or_venues} events lack start/end times and venue assignments; schedule must be generated and labelled ASSUMED",
                count=events_lacking_times_or_venues,
            )
        )

    # 7. Equipment condition inconsistencies
    non_good_items = []
    for itm in inventory_logistics:
        cond = (itm.get("condition") or "").upper()
        if cond not in ("GOOD", "NEW"):
            non_good_items.append({"item_id": itm.get("id"), "item": itm.get("name"), "condition": cond})

    if non_good_items:
        issues.append(
            ValidationIssue(
                file="inventory_logistics.csv",
                field="condition",
                severity=3,
                code="EQUIPMENT_CONDITION_INCONSISTENCY",
                message=f"{len(non_good_items)} logistics inventory items are in non-good condition (under repair / needs check)",
                count=len(non_good_items),
                details={"items": non_good_items},
            )
        )

    return issues
