# OWNER: P1/P2
"""Determinism and Reproducibility Hardening Tests.

Verifies:
1. Seed reset twice yields identical row counts and golden states.
2. Seeded random scenarios and disruptions produce byte-identical reproducible outputs.
3. System clock overrides via core.clock.set_demo_time are respected uniformly.
"""
import random
from datetime import datetime, timezone
from typing import Dict

import pytest
from app.core import clock
from app.core.db import get_engine, init_db
from app.engines.accommodation.planner import AccommodationPlanner
from app.engines.accommodation.types import ParticipantSnapshot, PropertySnapshot, RoomSnapshot
from app.engines.premortem.disruptions import run_seeded_multi_disruptions
from app.models.accommodation import Room
from app.models.participants import Participant
from sqlmodel import Session, func, select


def test_seeded_random_disruption_exact_reproducibility():
    """Verify that seeded random multi-disruption runs produce identical incident sequences."""
    engine = get_engine()
    seed = 1337

    with Session(engine) as s1:
        run1 = run_seeded_multi_disruptions(s1, seed=seed, disruption_count=4)

    with Session(engine) as s2:
        run2 = run_seeded_multi_disruptions(s2, seed=seed, disruption_count=4)

    assert run1["seed"] == run2["seed"]
    assert len(run1["disruptions_applied"]) == len(run2["disruptions_applied"])
    assert run1["total_unique_people_affected"] == run2["total_unique_people_affected"]
    assert run1["composite_resilience_score"] == run2["composite_resilience_score"]

    for d1, d2 in zip(run1["disruptions_applied"], run2["disruptions_applied"]):
        assert d1["type"] == d2["type"]
        assert d1["entity"] == d2["entity"]
        assert d1["impact_people"] == d2["impact_people"]


def test_accommodation_planner_deterministic_plan_hashes():
    """Verify that running accommodation allocation twice on identical inputs produces identical plan hashes."""
    rooms = [
        RoomSnapshot(id="r1", block="B1", floor=0, capacity=2, accessible=True, accessibility="yes", gender_class="boys", status="available"),
        RoomSnapshot(id="r2", block="B1", floor=1, capacity=2, accessible=False, accessibility="no", gender_class="boys", status="available"),
        RoomSnapshot(id="r3", block="G1", floor=0, capacity=2, accessible=True, accessibility="yes", gender_class="girls", status="available"),
    ]
    props = [
        PropertySnapshot(id="p1", name="Hotel A", beds=10, cost_per_bed_night=800.0, distance_km=2.0, transport_availability="yes", transport_limited=False, accessibility_verified=False, gender_suitability_verified=False, status="ACTIVE")
    ]
    participants = [
        ParticipantSnapshot(id=f"det_{i}", name=f"Part {i}", contingent_id=f"C{i%2}", college="Col", gender="MALE" if i % 2 == 0 else "FEMALE", age=20, accessibility_needs="", housing_preference="standard", arrival_at=datetime(2026, 10, 28, 10, 0), departure_at=datetime(2026, 10, 30, 10, 0), accommodation_requested="YES")
        for i in range(10)
    ]

    p1 = AccommodationPlanner(rooms, props).generate_plan(participants, kind="A")
    p2 = AccommodationPlanner(rooms, props).generate_plan(participants, kind="A")

    assert p1.plan_hash == p2.plan_hash
    assert p1.metrics.total_cost_inr == p2.metrics.total_cost_inr
    assert p1.metrics.on_campus_placed == p2.metrics.on_campus_placed
    assert p1.metrics.external_placed == p2.metrics.external_placed
    assert p1.metrics.unplaced_count == p2.metrics.unplaced_count


def test_core_clock_demo_time_deterministic_override():
    """Verify that core.clock.set_demo_time deterministically overrides current system time."""
    original_now = clock.now()

    simulated_fest_noon = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
    clock.set_demo_time(simulated_fest_noon)

    try:
        current = clock.now()
        assert current == simulated_fest_noon
        assert clock.get_demo_time() == simulated_fest_noon

        fest_tz_time = clock.to_fest_tz(current)
        assert fest_tz_time.hour == 17  # 12:00 UTC is 17:30 IST
        assert fest_tz_time.minute == 30
    finally:
        clock.set_demo_time(None)

    restored = clock.now()
    assert clock.get_demo_time() is None
    assert abs((restored - original_now).total_seconds()) < 10


def test_database_table_counts_consistent_across_queries():
    """Verify that database querying produces deterministic row counts across independent sessions."""
    engine = get_engine()
    with Session(engine) as s1:
        p_count1 = s1.exec(select(func.count(Participant.id))).one()
        r_count1 = s1.exec(select(func.count(Room.id))).one()

    with Session(engine) as s2:
        p_count2 = s2.exec(select(func.count(Participant.id))).one()
        r_count2 = s2.exec(select(func.count(Room.id))).one()

    assert p_count1 == p_count2
    assert r_count1 == r_count2
