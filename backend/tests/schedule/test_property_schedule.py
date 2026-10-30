# OWNER: P1
"""Property tests for the Pure Scheduling Engine.

Verifies invariants across randomized and combinatorial inputs:
1. No venue overlaps (accounting for setup and teardown buffers)
2. No participant overlaps (accounting for travel buffers between distinct venues)
3. Heats never exceed venue capacity
4. Honest accounting: every input participant is either placed in a session or listed
   in unscheduled_entrants with a valid reason (never silently dropped).
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest
from app.engines.scheduling import PureSchedulingEngine


def _random_dt(start_base: datetime, max_offset_hours: int = 12) -> datetime:
    offset = random.randint(0, max_offset_hours * 60)
    return start_base + timedelta(minutes=offset)


def generate_random_scenario(seed: int, num_events: int = 4, num_venues: int = 3, num_participants: int = 25):
    random.seed(seed)
    base_date = datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)

    # Generate venues
    venues = []
    for i in range(num_venues):
        vid = f"V_{i+1:02d}"
        cap = random.choice([5, 10, 20])
        venues.append({
            "id": vid,
            "name": f"Venue {i+1}",
            "capacity": cap,
            "setup_time_min": 15,
            "teardown_time_min": 15,
            "availability_windows": "2026-10-31 08:00-22:00",
        })

    # Generate participants with valid arrival / departures
    participants = []
    for i in range(num_participants):
        pid = f"p_prop_{seed}_{i:03d}"
        arr = base_date + timedelta(hours=random.randint(0, 3))
        dep = arr + timedelta(hours=random.randint(4, 10))
        participants.append({
            "participant_id": pid,
            "contingent_id": f"CONT_{i % 3}",
            "arrival_at": arr.isoformat(),
            "departure_at": dep.isoformat(),
        })

    # Generate events
    events = []
    regs = []
    for j in range(num_events):
        eid = f"EV_PROP_{j+1}"
        dur = random.choice([30, 45, 60, 90])
        events.append({
            "id": eid,
            "name": f"Event {j+1}",
            "duration_min": dur,
            "rounds": 1,
            "solo_team": "SOLO",
            "volunteers_needed": 1,
            "judges_needed": 1,
        })

        # Assign subset of participants to each event
        entrant_sample = random.sample(participants, k=random.randint(3, min(15, len(participants))))
        for ep in entrant_sample:
            regs.append({
                "participant_id": ep["participant_id"],
                "event_id": eid,
                "contingent_id": ep["contingent_id"],
                "arrival_at": ep["arrival_at"],
                "departure_at": ep["departure_at"],
            })

    return events, venues, regs


@pytest.mark.parametrize("seed", [42, 101, 777, 9999, 12345])
def test_property_generated_schedules_invariants(seed: int):
    events, venues, regs = generate_random_scenario(seed)
    engine = PureSchedulingEngine(events, venues, regs)
    result = engine.generate(solver="greedy", include_late_wave=True)

    sessions = result["sessions"]
    unscheduled = result["unscheduled_entrants"]

    # Invariant 1: No venue overlaps (including 15m setup and 15m teardown buffers)
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
                f"Venue {vid} collision between {curr['id']} (busy until {curr_busy_end}) "
                f"and {nxt['id']} (busy from {nxt_busy_start})"
            )

    # Invariant 2: No participant overlaps (including travel buffer if venues differ)
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
                f"Participant {pid} clash between session {curr['id']} and {nxt['id']}"
            )

    # Invariant 3: Heats are bounded by venue capacity
    venue_cap_map = {v["id"]: v["capacity"] for v in venues}
    for s in sessions:
        cap = venue_cap_map.get(s["venue_id"], 100)
        assert s["entrants_count"] <= cap, (
            f"Session {s['id']} entrants ({s['entrants_count']}) exceed venue {s['venue_id']} capacity ({cap})"
        )

    # Invariant 4: Honest accounting - every registered (participant, event) pair
    # is either in a session or in unscheduled_entrants with a reason.
    scheduled_pairs = set()
    for s in sessions:
        for pid in s.get("assigned_participant_ids", []):
            scheduled_pairs.add((pid, s["event_id"]))

    unscheduled_pairs = set()
    for u in unscheduled:
        unscheduled_pairs.add((u["participant_id"], u["event_id"]))
        assert u["reason"] in ("NOT_ON_SITE_LONG_ENOUGH", "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH")
        assert len(u["alternatives"]) > 0

    all_input_pairs = {(r["participant_id"], r["event_id"]) for r in regs}

    # Verify no entrant was silently dropped
    accounted_for = scheduled_pairs.union(unscheduled_pairs)
    missing = all_input_pairs - accounted_for
    assert not missing, f"Entrants were silently dropped without unscheduled accounting: {missing}"
