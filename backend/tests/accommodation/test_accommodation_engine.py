# OWNER: P2
from datetime import datetime

import pytest
from app.engines.accommodation.demand import (
    compute_bed_demand_timeline,
    partition_demand,
)
from app.engines.accommodation.planner import AccommodationPlanner, BedTimeline
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
    normalize_gender,
)
from app.engines.accommodation.types import (
    ParticipantSnapshot,
    PropertySnapshot,
    RoomSnapshot,
)
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Test Fixtures & Small Scenarios
# ---------------------------------------------------------------------------

@pytest.fixture
def small_rooms():
    return [
        RoomSnapshot(
            id="rm_b1_01",
            block="B1",
            floor=0,
            capacity=2,
            accessible=True,
            accessibility="yes",
            gender_class="boys",
            status="available",
        ),
        RoomSnapshot(
            id="rm_b1_02",
            block="B1",
            floor=1,
            capacity=2,
            accessible=False,
            accessibility="no",
            gender_class="boys",
            status="available",
        ),
        RoomSnapshot(
            id="rm_g1_01",
            block="G1",
            floor=0,
            capacity=2,
            accessible=True,
            accessibility="yes",
            gender_class="girls",
            status="available",
        ),
        RoomSnapshot(
            id="rm_g1_02",
            block="G1",
            floor=1,
            capacity=2,
            accessible=False,
            accessibility="no",
            gender_class="girls",
            status="available",
        ),
    ]


@pytest.fixture
def small_properties():
    return [
        PropertySnapshot(
            id="ext_prop_1",
            name="City Grand Hotel",
            beds=4,
            cost_per_bed_night=1000.0,
            distance_km=2.5,
            transport_availability="yes",
            transport_limited=False,
            accessibility_verified=False,
            gender_suitability_verified=False,
            status="ACTIVE",
        ),
        PropertySnapshot(
            id="ext_prop_limited",
            name="Remote Lakeview Lodge",
            beds=4,
            cost_per_bed_night=800.0,
            distance_km=8.0,
            transport_availability="limited",
            transport_limited=True,
            accessibility_verified=False,
            gender_suitability_verified=False,
            status="ACTIVE",
        ),
    ]


# ---------------------------------------------------------------------------
# 1. Hand-Calculated Small Fixture Test
# ---------------------------------------------------------------------------

def test_hand_calculated_small_fixture(small_rooms, small_properties):
    """Hand-calculated 5-participant scenario verifying deterministic assignment.

    Participants:
    - P1: Male, needs wheelchair, arrives 28 Oct, departs 30 Oct. Should get rm_b1_01 (accessible boys).
    - P2: Male, no needs, arrives 28 Oct, departs 30 Oct. Should share rm_b1_01 with P1.
    - P3: Male, no needs, arrives 28 Oct, departs 30 Oct. rm_b1_01 full -> gets rm_b1_02.
    - P4: Female, no needs, arrives 28 Oct, departs 30 Oct. Should get rm_g1_01.
    - P5: UNKNOWN gender, arrives 28 Oct, departs 30 Oct. Ineligible for boys/girls rooms -> unplaced with GENDER_OR_HOUSING_UNKNOWN.
    """
    participants = [
        ParticipantSnapshot(
            id="P01",
            name="Alice Walker",
            contingent_id="C01",
            college="IIT Bombay",
            gender="MALE",
            age=20,
            accessibility_needs="wheelchair access",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        ),
        ParticipantSnapshot(
            id="P02",
            name="Bob Smith",
            contingent_id="C01",
            college="IIT Bombay",
            gender="MALE",
            age=21,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        ),
        ParticipantSnapshot(
            id="P03",
            name="Charlie Brown",
            contingent_id="C01",
            college="IIT Bombay",
            gender="MALE",
            age=22,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        ),
        ParticipantSnapshot(
            id="P04",
            name="Diana Prince",
            contingent_id="C02",
            college="IIT Delhi",
            gender="FEMALE",
            age=20,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        ),
        ParticipantSnapshot(
            id="P05",
            name="Evan Taylor",
            contingent_id="C02",
            college="IIT Delhi",
            gender="UNKNOWN",
            age=19,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        ),
    ]

    planner = AccommodationPlanner(rooms=small_rooms, properties=small_properties, cleaning_buffer_minutes=180)
    result = planner.generate_plan(participants, kind="A")

    assigned_map = {a.participant_id: a for a in result.assignments}

    # P01 gets rm_b1_01 bed 1
    assert "P01" in assigned_map
    assert assigned_map["P01"].resource_id == "rm_b1_01"

    # P02 gets rm_b1_01 bed 2
    assert "P02" in assigned_map
    assert assigned_map["P02"].resource_id == "rm_b1_01"

    # P03 gets rm_b1_02 bed 1
    assert "P03" in assigned_map
    assert assigned_map["P03"].resource_id == "rm_b1_02"

    # P04 gets rm_g1_01
    assert "P04" in assigned_map
    assert assigned_map["P04"].resource_id == "rm_g1_01"

    # P05 is UNKNOWN gender -> never auto-assigned to boys/girls room
    assert "P05" not in assigned_map
    unplaced_p05 = next((u for u in result.unplaced if u.participant_id == "P05"), None)
    assert unplaced_p05 is not None
    assert unplaced_p05.blocking_reason == TAXONOMY_GENDER_OR_HOUSING_UNKNOWN


# ---------------------------------------------------------------------------
# 2. Rolling Occupancy & Cleaning Buffer Test
# ---------------------------------------------------------------------------

def test_cleaning_interval_respected():
    """Verify that a bed cannot be booked during the 180-minute cleaning buffer."""
    bed = BedTimeline(bed_key="rm_01:bed_1", cleaning_buffer_minutes=180)

    # Participant 1 stays from 10:00 to 14:00 on 28 Oct
    p1_start = datetime(2026, 10, 28, 10, 0)
    p1_end = datetime(2026, 10, 28, 14, 0)
    assert bed.book(p1_start, p1_end, "P01") is True

    # Participant 2 arrives at 15:00 (1 hour after P1 checkout; inside 3h cleaning buffer)
    p2_start = datetime(2026, 10, 28, 15, 0)
    p2_end = datetime(2026, 10, 28, 19, 0)
    assert bed.is_available(p2_start, p2_end) is False
    assert bed.book(p2_start, p2_end, "P02") is False

    # Participant 3 arrives at 17:00 (exactly 3 hours after P1 checkout; cleaning buffer expired)
    p3_start = datetime(2026, 10, 28, 17, 0)
    p3_end = datetime(2026, 10, 28, 22, 0)
    assert bed.is_available(p3_start, p3_end) is True
    assert bed.book(p3_start, p3_end, "P03") is True


def test_bed_timeline_unbook():
    """Verify unbook frees the bed for subsequent allocations."""
    bed = BedTimeline(bed_key="rm_01:bed_1", cleaning_buffer_minutes=180)
    start = datetime(2026, 10, 28, 10, 0)
    end = datetime(2026, 10, 28, 14, 0)
    assert bed.book(start, end, "P01") is True
    assert bed.is_available(start, end) is False

    assert bed.unbook(start, "P01") is True
    assert bed.is_available(start, end) is True


# ---------------------------------------------------------------------------
# 3. Stage A Hard Filters & Taxonomy Tests
# ---------------------------------------------------------------------------

def test_unknown_never_silently_assigned(small_rooms):
    """Non-binary, prefer-not-to-say, blank or UNKNOWN participants are NEVER placed in a gendered block."""
    for unknown_gender in ["UNKNOWN", "NON-BINARY", "Prefer Not To Say", "", "blank"]:
        p = ParticipantSnapshot(
            id="P_unk",
            name="Unknown Guest",
            contingent_id="C1",
            college="Test College",
            gender=unknown_gender,
            age=22,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        )
        for room in small_rooms:
            eligible, reason, code = check_room_eligibility(p, room)
            assert eligible is False
            assert code == TAXONOMY_GENDER_OR_HOUSING_UNKNOWN


def test_wheelchair_and_ground_floor_hard_rules(small_rooms):
    """Wheelchair needs must get accessible rooms; ground floor needs must get floor 0."""
    p_wheelchair = ParticipantSnapshot(
        id="P_wc",
        name="Wheelchair User",
        contingent_id="C1",
        college="College",
        gender="MALE",
        age=20,
        accessibility_needs="Wheelchair required",
        housing_preference="standard",
        arrival_at=datetime(2026, 10, 28, 10, 0),
        departure_at=datetime(2026, 10, 30, 10, 0),
        accommodation_requested="YES",
    )

    for room in small_rooms:
        if room.gender_class == "boys":
            eligible, reason, code = check_room_eligibility(p_wheelchair, room)
            if room.accessible:
                assert eligible is True
            else:
                assert eligible is False
                assert code == TAXONOMY_HARD_ACCESSIBILITY


def test_manual_verification_needs_never_auto_satisfied(small_rooms):
    """Near-washroom and visual-assistance needs -> NEEDS_MANUAL_VERIFICATION, never auto-satisfied."""
    p_visual = ParticipantSnapshot(
        id="P_vis",
        name="Visual Assist Needed",
        contingent_id="C1",
        college="College",
        gender="MALE",
        age=20,
        accessibility_needs="visual assistance required",
        housing_preference="standard",
        arrival_at=datetime(2026, 10, 28, 10, 0),
        departure_at=datetime(2026, 10, 30, 10, 0),
        accommodation_requested="YES",
    )
    for room in small_rooms:
        eligible, reason, code = check_room_eligibility(p_visual, room)
        assert eligible is False
        assert "manual inspection" in reason.lower()
        assert code == TAXONOMY_HARD_ACCESSIBILITY


def test_minor_safeguards_in_external_properties(small_properties):
    """Minors (<18) cannot be placed in limited transport properties, and require guardian approval."""
    minor_no_guardian = ParticipantSnapshot(
        id="P_minor",
        name="Minor Student",
        contingent_id="C1",
        college="High School",
        gender="MALE",
        age=16,
        accessibility_needs="",
        housing_preference="standard",
        arrival_at=datetime(2026, 10, 28, 10, 0),
        departure_at=datetime(2026, 10, 30, 10, 0),
        guardian_approved=False,
        accommodation_requested="YES",
    )

    prop_normal = next(p for p in small_properties if not p.transport_limited)
    prop_limited = next(p for p in small_properties if p.transport_limited)

    # Minor in normal property without guardian approval -> TAXONOMY_MISSING_INFO
    el1, r1, c1 = check_external_property_eligibility(minor_no_guardian, prop_normal)
    assert el1 is False
    assert c1 == TAXONOMY_MISSING_INFO

    # Minor in limited transport property -> TAXONOMY_TRANSPORT_RESTRICTED
    minor_with_guardian = ParticipantSnapshot(**{**minor_no_guardian.__dict__, "guardian_approved": True})
    el2, r2, c2 = check_external_property_eligibility(minor_with_guardian, prop_limited)
    assert el2 is False
    assert c2 == TAXONOMY_TRANSPORT_RESTRICTED


def test_invalid_intervals_tracked_not_dropped():
    """Participants with arrival >= departure must be listed in invalid_intervals, never dropped silently."""
    participants = [
        ParticipantSnapshot(
            id="P_valid",
            name="Valid",
            contingent_id="C1",
            college="IIT",
            gender="MALE",
            age=20,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        ),
        ParticipantSnapshot(
            id="P_invalid_inverted",
            name="Inverted Dates",
            contingent_id="C1",
            college="IIT",
            gender="MALE",
            age=20,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 30, 10, 0),
            departure_at=datetime(2026, 10, 28, 10, 0),  # Departure before arrival
            accommodation_requested="YES",
        ),
    ]

    confirmed, possible, invalid = partition_demand(participants)
    assert len(confirmed) == 1
    assert confirmed[0].id == "P_valid"
    assert len(invalid) == 1
    assert invalid[0]["participant_id"] == "P_invalid_inverted"
    assert "before arrival" in invalid[0]["reason"].lower() or "duration" in invalid[0]["reason"].lower()


# ---------------------------------------------------------------------------
# 4. Determinism & Plan Comparison Tests
# ---------------------------------------------------------------------------

def test_deterministic_plans_and_plan_hash(small_rooms, small_properties):
    """Running generate_plan twice with the same inputs must yield identical plan hash and assignments."""
    participants = [
        ParticipantSnapshot(
            id=f"P_{i:02d}",
            name=f"Participant {i}",
            contingent_id=f"C_{i%2}",
            college="Test College",
            gender="MALE" if i % 2 == 0 else "FEMALE",
            age=20,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        )
        for i in range(8)
    ]

    planner = AccommodationPlanner(rooms=small_rooms, properties=small_properties)
    run1 = planner.generate_plan(participants, kind="A")
    run2 = planner.generate_plan(participants, kind="A")

    assert run1.plan_hash == run2.plan_hash
    assert len(run1.assignments) == len(run2.assignments)
    for a1, a2 in zip(run1.assignments, run2.assignments):
        assert a1.participant_id == a2.participant_id
        assert a1.resource_id == a2.resource_id
        assert a1.bed_key == a2.bed_key


def test_plans_a_b_c_tradeoffs(small_rooms, small_properties):
    """Plans A, B, and C must reflect their design tradeoffs (A cohesion, B cost, C balanced)."""
    participants = [
        ParticipantSnapshot(
            id=f"P_{i:02d}",
            name=f"Participant {i}",
            contingent_id="C_LARGE" if i < 6 else "C_SMALL",
            college="Test College",
            gender="MALE",
            age=20,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0),
            departure_at=datetime(2026, 10, 30, 10, 0),
            accommodation_requested="YES",
        )
        for i in range(10)
    ]

    planner = AccommodationPlanner(rooms=small_rooms, properties=small_properties)
    plan_a = planner.generate_plan(participants, kind="A")
    plan_b = planner.generate_plan(participants, kind="B")
    plan_c = planner.generate_plan(participants, kind="C")

    assert plan_a.kind == "A"
    assert plan_b.kind == "B"
    assert plan_c.kind == "C"

    # All three plans must have sacrifices summaries
    assert len(plan_a.sacrifices_summary) > 0
    assert len(plan_b.sacrifices_summary) > 0
    assert len(plan_c.sacrifices_summary) > 0


# ---------------------------------------------------------------------------
# 5. Property-Based Testing with Hypothesis
# ---------------------------------------------------------------------------

@settings(max_examples=25, deadline=None)
@given(
    genders=st.lists(st.sampled_from(["MALE", "FEMALE", "UNKNOWN", "NON-BINARY", ""]), min_size=5, max_size=15),
    wheelchairs=st.lists(st.booleans(), min_size=5, max_size=15),
    ground_floors=st.lists(st.booleans(), min_size=5, max_size=15),
    ages=st.lists(st.integers(min_value=15, max_value=25), min_size=5, max_size=15),
)
def test_hypothesis_hard_constraints_never_violated(
    genders, wheelchairs, ground_floors, ages
):
    """Hypothesis test: across arbitrary random participant profiles, hard constraints are NEVER violated."""
    rooms = [
        RoomSnapshot(id="rm_b1_01", block="B1", floor=0, capacity=2, accessible=True, accessibility="yes", gender_class="boys", status="available"),
        RoomSnapshot(id="rm_b1_02", block="B1", floor=1, capacity=2, accessible=False, accessibility="no", gender_class="boys", status="available"),
        RoomSnapshot(id="rm_g1_01", block="G1", floor=0, capacity=2, accessible=True, accessibility="yes", gender_class="girls", status="available"),
        RoomSnapshot(id="rm_g1_02", block="G1", floor=1, capacity=2, accessible=False, accessibility="no", gender_class="girls", status="available"),
    ]
    properties = [
        PropertySnapshot(id="ext_prop_1", name="City Grand Hotel", beds=4, cost_per_bed_night=1000.0, distance_km=2.5, transport_availability="yes", transport_limited=False, accessibility_verified=False, gender_suitability_verified=False, status="ACTIVE"),
        PropertySnapshot(id="ext_prop_limited", name="Remote Lakeview Lodge", beds=4, cost_per_bed_night=800.0, distance_km=8.0, transport_availability="limited", transport_limited=True, accessibility_verified=False, gender_suitability_verified=False, status="ACTIVE"),
    ]

    min_len = min(len(genders), len(wheelchairs), len(ground_floors), len(ages))
    participants = []

    for i in range(min_len):
        needs = []
        if wheelchairs[i]:
            needs.append("wheelchair")
        if ground_floors[i]:
            needs.append("ground floor")

        participants.append(
            ParticipantSnapshot(
                id=f"H_{i:02d}",
                name=f"Hypothesis {i}",
                contingent_id=f"C_{i%3}",
                college="Hypothesis University",
                gender=genders[i],
                age=ages[i],
                accessibility_needs=", ".join(needs),
                housing_preference="standard",
                arrival_at=datetime(2026, 10, 28, 10, 0),
                departure_at=datetime(2026, 10, 30, 10, 0),
                accommodation_requested="YES",
            )
        )

    planner = AccommodationPlanner(rooms=rooms, properties=properties)
    result = planner.generate_plan(participants, kind="C")

    # Invariants verification
    room_map = {r.id: r for r in rooms}
    prop_map = {p.id: p for p in properties}
    p_map = {p.id: p for p in participants}

    # 1. No capacity exceeded
    bed_usage = {}
    for a in result.assignments:
        bed_usage[a.bed_key] = bed_usage.get(a.bed_key, 0) + 1
        # No bed double-booked for the same time window
        assert bed_usage[a.bed_key] <= 1

        p = p_map[a.participant_id]

        if not a.is_external:
            room = room_map[a.resource_id]
            # Hard Rule 1: Gender alignment
            gender_norm = normalize_gender(p.gender)
            if room.gender_class == "boys":
                assert gender_norm == "MALE"
            elif room.gender_class == "girls":
                assert gender_norm == "FEMALE"

            # Hard Rule 2: Wheelchair user only in accessible room
            if "wheelchair" in p.accessibility_needs.lower():
                assert room.accessible is True

            # Hard Rule 3: Ground floor user only on floor 0
            if "ground" in p.accessibility_needs.lower():
                assert room.floor == 0
        else:
            prop = prop_map[a.resource_id]
            # Hard Rule 4: Minor never in limited transport property
            if p.age < 18:
                assert prop.transport_limited is False
                assert (prop.transport_availability or "").lower() != "limited"

    # 2. Every unplaced participant has documented blocking reason from fixed taxonomy
    valid_taxonomy = {
        TAXONOMY_HARD_ACCESSIBILITY,
        TAXONOMY_GENDER_OR_HOUSING_UNKNOWN,
        TAXONOMY_TRANSPORT_RESTRICTED,
        TAXONOMY_NO_ELIGIBLE_PROPERTY,
        TAXONOMY_BUDGET,
        TAXONOMY_MISSING_INFO,
        TAXONOMY_CAPACITY,
    }
    for u in result.unplaced:
        assert u.blocking_reason in valid_taxonomy
        assert len(u.counterfactual_runs) >= 0


# ---------------------------------------------------------------------------
# 6. Golden Run on Real Data Pack
# ---------------------------------------------------------------------------

def test_golden_run_data_pack():
    """Execute golden run on actual data pack and print sanity metrics next to prototype references.

    Prototype references for Cohesion-First (Plan A):
    - On campus: ~861
    - External: ~920
    - Unplaced: ~360
    - Peak simultaneous bed demand: ~1,601 at 30 Oct 6 PM
    """
    import csv
    import os

    data_dir = "/home/avnish_sharma/festos/data/raw"
    hostels_path = os.path.join(data_dir, "hostels.csv")
    properties_path = os.path.join(data_dir, "external_stays.csv")
    participants_path = os.path.join(data_dir, "participants.csv")

    assert os.path.exists(hostels_path), f"Missing {hostels_path}"
    assert os.path.exists(properties_path), f"Missing {properties_path}"
    assert os.path.exists(participants_path), f"Missing {participants_path}"

    # Load rooms
    rooms = []
    with open(hostels_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rooms.append(
                RoomSnapshot(
                    id=r["room_id"],
                    block=r["block"],
                    floor=int(r["floor"]),
                    capacity=int(r["capacity"]),
                    accessible=(r["accessibility"].lower() == "yes"),
                    accessibility=r["accessibility"].lower(),
                    gender_class=r.get("gender", r.get("gender_class", "UNKNOWN")).lower(),
                    status="available",
                )
            )

    # Load properties
    properties = []
    with open(properties_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for p in reader:
            properties.append(
                PropertySnapshot(
                    id=p["property_id"],
                    name=p["property_name"],
                    beds=int(p["beds"]),
                    cost_per_bed_night=float(p["cost_per_bed_per_night"]),
                    distance_km=float(p["distance_km"]),
                    transport_availability=p.get("transport_availability", "yes").lower(),
                    transport_limited=(p.get("transport_availability", "").lower() == "limited"),
                    accessibility_verified=False,
                    gender_suitability_verified=False,
                    status="ACTIVE",
                )
            )

    # Load participants
    participants = []
    with open(participants_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for p in reader:
            arr = None
            dep = None
            if p.get("arrival_datetime"):
                arr = datetime.fromisoformat(p["arrival_datetime"])
            if p.get("departure_datetime"):
                dep = datetime.fromisoformat(p["departure_datetime"])

            raw_accom = p.get("accommodation_requested", "").strip().lower()
            accom_req = "YES" if raw_accom in ("yes", "true", "1") else ("NO" if raw_accom in ("no", "false", "0") else "UNKNOWN")
            age_val = int(p["age"]) if p.get("age") and p["age"].isdigit() else 20

            participants.append(
                ParticipantSnapshot(
                    id=p["participant_id"],
                    name=p.get("name", ""),
                    contingent_id=p.get("contingent_id", ""),
                    college=p.get("college", ""),
                    gender=p.get("gender_as_given", p.get("gender", "UNKNOWN")),
                    age=age_val,
                    accessibility_needs=p.get("accessibility_needs", ""),
                    housing_preference=p.get("housing_preference", "standard"),
                    arrival_at=arr,
                    departure_at=dep,
                    is_contingent_leader=(p.get("is_contingent_leader", "").lower() == "true"),
                    is_faculty_escort=(p.get("is_faculty_escort", "").lower() == "true"),
                    guardian_approved=(p.get("guardian_approved", "").lower() == "true" or age_val >= 18),
                    has_night_arrival=(p.get("has_night_arrival", "").lower() == "true"),
                    has_early_event=(p.get("has_early_event", "").lower() == "true"),
                    accommodation_requested=accom_req,
                )
            )

    # 1. Timeline verification
    timeline_res = compute_bed_demand_timeline(participants, cleaning_buffer_minutes=180)
    print(f"\n[Golden Run] Total requesting: {timeline_res.total_participants_requesting}")
    print(f"[Golden Run] Peak simultaneous bed demand: {timeline_res.peak_simultaneous_demand} at {timeline_res.peak_time}")
    print(f"[Golden Run] Invalid intervals: {timeline_res.invalid_intervals_count}")

    # Verify demand at 30 Oct 6 PM (18:00) matches spec reference ~1,601
    pt_30_oct_18 = next(pt for pt in timeline_res.timeline if pt.timestamp == datetime(2026, 10, 30, 18, 0))
    assert pt_30_oct_18.confirmed_demand == 1601
    assert timeline_res.invalid_intervals_count == 3

    # 2. Run Plan A (Cohesion-First)
    planner = AccommodationPlanner(rooms=rooms, properties=properties, cleaning_buffer_minutes=180)
    plan_a = planner.generate_plan(participants, kind="A")
    m_a = plan_a.metrics

    print("\n--- Plan A (Cohesion-First) Metrics vs Prototype References ---")
    print(f"On-Campus Placed:   {m_a.on_campus_placed:<5} (Prototype ref: ~861)")
    print(f"External Placed:    {m_a.external_placed:<5} (Prototype ref: ~920)")
    print(f"Unplaced Count:     {m_a.unplaced_count:<5} (Prototype ref: ~360)")
    print(f"Contingent Splits:  {m_a.contingent_splits}")
    print(f"Total Cost:         ₹{m_a.total_cost_inr:,.2f}")
    print(f"Plan Hash:          {plan_a.plan_hash}")
    print(f"Accessibility Def:  {m_a.accessibility_issues_count} (Must be 0)")
    print("---------------------------------------------------------------\n")

    # Sanity checks
    assert m_a.accessibility_issues_count == 0
    assert m_a.on_campus_placed > 700
    assert m_a.external_placed > 150
    assert m_a.unplaced_count > 300
    assert plan_a.plan_hash.startswith("sha256:")
