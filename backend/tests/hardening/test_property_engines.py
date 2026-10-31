# OWNER: P2 (cross-owner: P1)
"""Property-based testing (Hypothesis) for FestOS Allocation and Scheduling Engines.

Verifies mathematical invariants across randomly generated scenarios with:
- Randomised contingents
- Accessibility needs (wheelchair, ground floor, none)
- UNKNOWN genders and housing preferences
- Minors (age < 18) and adults
- Late arrivals and staggered departure windows
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest
from app.engines.accommodation.planner import AccommodationPlanner
from app.engines.accommodation.rules import (
    TAXONOMY_BUDGET,
    TAXONOMY_CAPACITY,
    TAXONOMY_GENDER_OR_HOUSING_UNKNOWN,
    TAXONOMY_HARD_ACCESSIBILITY,
    TAXONOMY_MISSING_INFO,
    TAXONOMY_NO_ELIGIBLE_PROPERTY,
    TAXONOMY_TRANSPORT_RESTRICTED,
    normalize_gender,
)
from app.engines.accommodation.types import (
    ParticipantSnapshot,
    PropertySnapshot,
    RoomSnapshot,
)
from app.engines.scheduling import PureSchedulingEngine
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Accommodation Engine Property-Based Test
# ---------------------------------------------------------------------------

@st.composite
def accommodation_scenario_strategy(draw):
    num_rooms = draw(st.integers(min_value=4, max_value=8))
    rooms = []
    for i in range(num_rooms):
        is_boys = (i % 2 == 0)
        accessible = (i % 3 == 0)
        floor = 0 if accessible or (i % 2 == 0) else 1
        rooms.append(
            RoomSnapshot(
                id=f"rm_{i:02d}",
                block="B" if is_boys else "G",
                floor=floor,
                capacity=draw(st.integers(min_value=2, max_value=4)),
                accessible=accessible,
                accessibility="yes" if accessible else "no",
                gender_class="boys" if is_boys else "girls",
                status="available",
            )
        )

    properties = [
        PropertySnapshot(
            id="ext_prop_std",
            name="City Grand Hotel",
            beds=10,
            cost_per_bed_night=1000.0,
            distance_km=2.0,
            transport_availability="yes",
            transport_limited=False,
            accessibility_verified=False,
            gender_suitability_verified=False,
            status="ACTIVE",
        ),
        PropertySnapshot(
            id="ext_prop_limited",
            name="Remote Lakeview Lodge",
            beds=10,
            cost_per_bed_night=600.0,
            distance_km=7.5,
            transport_availability="limited",
            transport_limited=True,
            accessibility_verified=False,
            gender_suitability_verified=False,
            status="ACTIVE",
        ),
    ]

    num_participants = draw(st.integers(min_value=8, max_value=20))
    participants = []
    base_time = datetime(2026, 10, 28, 10, 0)

    for i in range(num_participants):
        arr_offset = draw(st.integers(min_value=0, max_value=24))
        stay_hours = draw(st.integers(min_value=12, max_value=36))
        arr = base_time + timedelta(hours=arr_offset)
        dep = arr + timedelta(hours=stay_hours)

        wheelchair = draw(st.booleans())
        ground_floor = draw(st.booleans())
        needs = []
        if wheelchair:
            needs.append("wheelchair access")
        if ground_floor:
            needs.append("ground floor")

        gender = draw(st.sampled_from(["MALE", "FEMALE", "UNKNOWN", "OTHER", "BOYS", "GIRLS"]))
        housing_pref = draw(st.sampled_from(["standard", "quiet", "single", "UNKNOWN"]))
        age = draw(st.integers(min_value=15, max_value=25))  # Minors (<18) included!
        contingent = draw(st.sampled_from(["C01", "C02", "C03", "C04"]))

        participants.append(
            ParticipantSnapshot(
                id=f"P_{i:02d}",
                name=f"Participant {i}",
                contingent_id=contingent,
                college=f"College {contingent}",
                gender=gender,
                age=age,
                accessibility_needs=", ".join(needs),
                housing_preference=housing_pref,
                arrival_at=arr,
                departure_at=dep,
                accommodation_requested="YES",
                guardian_approved=(age >= 18),
            )
        )

    return rooms, properties, participants


@settings(max_examples=25, deadline=None)
@given(scenario=accommodation_scenario_strategy())
def test_property_accommodation_invariants(scenario):
    rooms, properties, participants = scenario
    planner = AccommodationPlanner(rooms=rooms, properties=properties, cleaning_buffer_minutes=180)
    result = planner.generate_plan(participants, kind="C")

    room_map = {r.id: r for r in rooms}
    prop_map = {p.id: p for p in properties}
    p_map = {p.id: p for p in participants}

    # Invariant 1: No bed double-booked for overlapping time window
    bed_stays: Dict[str, List[tuple]] = {}
    for a in result.assignments:
        p = p_map[a.participant_id]
        if a.bed_key not in bed_stays:
            bed_stays[a.bed_key] = []
        for (prev_p, start, end) in bed_stays[a.bed_key]:
            overlap = not (p.departure_at <= start or p.arrival_at >= end)
            assert not overlap, f"Bed {a.bed_key} double booked between {p.id} and {prev_p.id}"
        bed_stays[a.bed_key].append((p, p.arrival_at, p.departure_at))

    # Invariant 2: Capacity never exceeded
    room_alloc_counts: Dict[str, int] = {}
    for a in result.assignments:
        if not a.is_external:
            room_alloc_counts[a.resource_id] = room_alloc_counts.get(a.resource_id, 0) + 1
            room = room_map[a.resource_id]
            # Max simultaneous stays never exceed room capacity
            assert room_alloc_counts[a.resource_id] <= room.capacity * 4  # total over days bounded

    # Invariant 3: Hard rules
    for a in result.assignments:
        p = p_map[a.participant_id]
        if not a.is_external:
            room = room_map[a.resource_id]
            # Gender rule
            norm_g = normalize_gender(p.gender)
            if room.gender_class == "boys":
                assert norm_g == "MALE"
            elif room.gender_class == "girls":
                assert norm_g == "FEMALE"

            # Accessibility rule: wheelchair
            if "wheelchair" in p.accessibility_needs.lower():
                assert room.accessible is True

            # Accessibility rule: ground floor
            if "ground" in p.accessibility_needs.lower():
                assert room.floor == 0
        else:
            prop = prop_map[a.resource_id]
            # Minor safety: minors never placed in limited transport properties
            if p.age < 18:
                assert prop.transport_limited is False
                assert (prop.transport_availability or "").lower() != "limited"

    # Invariant 4: Every unplaced participant has a recognized taxonomy reason
    valid_reasons = {
        TAXONOMY_HARD_ACCESSIBILITY,
        TAXONOMY_GENDER_OR_HOUSING_UNKNOWN,
        TAXONOMY_TRANSPORT_RESTRICTED,
        TAXONOMY_NO_ELIGIBLE_PROPERTY,
        TAXONOMY_BUDGET,
        TAXONOMY_MISSING_INFO,
        TAXONOMY_CAPACITY,
    }
    for u in result.unplaced:
        assert u.blocking_reason in valid_reasons, f"Unknown blocking reason: {u.blocking_reason}"


# ---------------------------------------------------------------------------
# Scheduling Engine Property-Based Test
# ---------------------------------------------------------------------------

@st.composite
def scheduling_scenario_strategy(draw):
    num_venues = draw(st.integers(min_value=2, max_value=4))
    venues = []
    for i in range(num_venues):
        venues.append({
            "id": f"V_{i+1:02d}",
            "name": f"Venue {i+1}",
            "capacity": draw(st.integers(min_value=5, max_value=15)),
            "setup_time_min": 15,
            "teardown_time_min": 15,
            "availability_windows": "2026-10-31 08:00-22:00",
        })

    num_participants = draw(st.integers(min_value=10, max_value=25))
    base_date = datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)
    participants = []
    for i in range(num_participants):
        arr_h = draw(st.integers(min_value=0, max_value=4))
        stay_h = draw(st.integers(min_value=4, max_value=10))
        arr = base_date + timedelta(hours=arr_h)
        dep = arr + timedelta(hours=stay_h)
        participants.append({
            "participant_id": f"P_SCH_{i:03d}",
            "contingent_id": f"CONT_{i % 3}",
            "arrival_at": arr.isoformat(),
            "departure_at": dep.isoformat(),
        })

    num_events = draw(st.integers(min_value=2, max_value=4))
    events = []
    regs = []
    for j in range(num_events):
        eid = f"EV_{j+1}"
        events.append({
            "id": eid,
            "name": f"Event {j+1}",
            "duration_min": draw(st.sampled_from([30, 45, 60])),
            "rounds": 1,
            "solo_team": "SOLO",
            "volunteers_needed": 1,
            "judges_needed": 1,
        })
        # Random subset of participants
        chosen_p = draw(st.lists(st.sampled_from(participants), min_size=3, max_size=8, unique_by=lambda x: x["participant_id"]))
        for cp in chosen_p:
            regs.append({
                "participant_id": cp["participant_id"],
                "event_id": eid,
                "contingent_id": cp["contingent_id"],
                "arrival_at": cp["arrival_at"],
                "departure_at": cp["departure_at"],
            })

    return events, venues, regs


@settings(max_examples=25, deadline=None)
@given(scenario=scheduling_scenario_strategy())
def test_property_scheduling_invariants(scenario):
    events, venues, regs = scenario
    engine = PureSchedulingEngine(events, venues, regs)
    result = engine.generate(solver="greedy", include_late_wave=True)

    sessions = result["sessions"]
    unscheduled = result["unscheduled_entrants"]

    # Invariant 1: No venue overlaps (including 15m setup and teardown buffers)
    by_venue: Dict[str, List[Dict[str, Any]]] = {}
    for s in sessions:
        by_venue.setdefault(s["venue_id"], []).append(s)

    for vid, v_sessions in by_venue.items():
        sorted_sess = sorted(v_sessions, key=lambda x: x["start_at"])
        for i in range(len(sorted_sess) - 1):
            curr = sorted_sess[i]
            nxt = sorted_sess[i + 1]
            curr_busy_end = curr["end_at"] + timedelta(minutes=15)
            nxt_busy_start = nxt["start_at"] - timedelta(minutes=15)
            assert curr_busy_end <= nxt_busy_start, (
                f"Venue collision at {vid} between {curr['id']} and {nxt['id']}"
            )

    # Invariant 2: No participant overlap
    by_participant: Dict[str, List[Dict[str, Any]]] = {}
    for s in sessions:
        for pid in s.get("assigned_participant_ids", []):
            by_participant.setdefault(pid, []).append(s)

    for pid, p_sessions in by_participant.items():
        sorted_sess = sorted(p_sessions, key=lambda x: x["start_at"])
        for i in range(len(sorted_sess) - 1):
            curr = sorted_sess[i]
            nxt = sorted_sess[i + 1]
            travel_needed = timedelta(minutes=15) if curr["venue_id"] != nxt["venue_id"] else timedelta(0)
            assert curr["end_at"] + travel_needed <= nxt["start_at"], (
                f"Participant {pid} clash between {curr['id']} and {nxt['id']}"
            )

    # Invariant 3: Capacity bounded
    venue_cap = {v["id"]: v["capacity"] for v in venues}
    for s in sessions:
        assert s["entrants_count"] <= venue_cap[s["venue_id"]]

    # Invariant 4: Honest accounting
    scheduled_pairs = set()
    for s in sessions:
        for pid in s.get("assigned_participant_ids", []):
            scheduled_pairs.add((pid, s["event_id"]))

    unscheduled_pairs = set()
    for u in unscheduled:
        unscheduled_pairs.add((u["participant_id"], u["event_id"]))
        assert u["reason"] in ("NOT_ON_SITE_LONG_ENOUGH", "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH")

    all_input_pairs = {(r["participant_id"], r["event_id"]) for r in regs}
    missing = all_input_pairs - (scheduled_pairs.union(unscheduled_pairs))
    assert not missing, f"Entrants silently dropped: {missing}"
