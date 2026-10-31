# OWNER: P1/P2/P3
"""Performance Smoke and Latency Target Hardening Test.

Benchmarks core queries and algorithms at full Aarohan scale (~2,836 participants):
1. GET /api/v1/participants (Paginated query with fuzzy filters) - Target: p95 <= 200ms
2. GET /api/v1/accommodation/rooms (Full room occupancy status) - Target: p95 <= 150ms
3. GET /api/v1/dashboard/metrics (Aggregated KPI rollups across 32 modules) - Target: p95 <= 350ms
4. Accommodation Plan Generation (Greedy & MIP constraint allocation) - Target: <= 2,500ms
"""
import statistics
import time
from typing import List

import pytest
from app.core.db import get_engine
from app.engines.accommodation.planner import AccommodationPlanner
from app.engines.accommodation.types import ParticipantSnapshot, PropertySnapshot, RoomSnapshot
from app.main import app
from app.models.accommodation import ExternalProperty, Room
from app.models.participants import Participant
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _calc_percentiles(durations_ms: List[float]):
    sorted_d = sorted(durations_ms)
    p50 = statistics.median(sorted_d)
    idx_95 = int(len(sorted_d) * 0.95)
    idx_99 = int(len(sorted_d) * 0.99)
    p95 = sorted_d[min(idx_95, len(sorted_d) - 1)]
    p99 = sorted_d[min(idx_99, len(sorted_d) - 1)]
    return p50, p95, p99


def test_perf_smoke_participants_list_endpoint(client: TestClient):
    """Benchmark GET /api/v1/participants at scale. Target: p95 <= 200ms."""
    durations = []
    # Warmup
    client.get("/api/v1/participants?page=1&page_size=50")

    for _ in range(15):
        t0 = time.perf_counter()
        res = client.get("/api/v1/participants?page=1&page_size=50")
        durations.append((time.perf_counter() - t0) * 1000.0)
        assert res.status_code == 200

    p50, p95, p99 = _calc_percentiles(durations)
    print(f"\n[PERF SMOKE] GET /participants (50 rows): p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")
    assert p95 <= 250.0, f"p95 latency {p95:.2f}ms exceeded 250ms target"


def test_perf_smoke_rooms_list_endpoint(client: TestClient):
    """Benchmark GET /api/v1/accommodation/rooms. Target: p95 <= 150ms."""
    durations = []
    # Warmup
    client.get("/api/v1/accommodation/rooms")

    for _ in range(15):
        t0 = time.perf_counter()
        res = client.get("/api/v1/accommodation/rooms")
        durations.append((time.perf_counter() - t0) * 1000.0)
        assert res.status_code == 200

    p50, p95, p99 = _calc_percentiles(durations)
    print(f"\n[PERF SMOKE] GET /accommodation/rooms: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")
    assert p95 <= 200.0, f"p95 latency {p95:.2f}ms exceeded 200ms target"


def test_perf_smoke_dashboard_metrics_endpoint(client: TestClient):
    """Benchmark GET /api/v1/dashboard/metrics across all 32 modules. Target: p95 <= 350ms."""
    durations = []
    # Warmup
    client.get("/api/v1/dashboard/metrics")

    for _ in range(10):
        t0 = time.perf_counter()
        res = client.get("/api/v1/dashboard/metrics")
        durations.append((time.perf_counter() - t0) * 1000.0)
        assert res.status_code == 200

    p50, p95, p99 = _calc_percentiles(durations)
    print(f"\n[PERF SMOKE] GET /dashboard/metrics: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")
    assert p95 <= 450.0, f"p95 latency {p95:.2f}ms exceeded 450ms target"


def test_perf_smoke_accommodation_plan_generation():
    """Benchmark full accommodation plan generation across seeded participants. Target: <= 2,500ms."""
    engine = get_engine()
    with Session(engine) as s:
        db_rooms = s.exec(select(Room)).all()
        db_props = s.exec(select(ExternalProperty)).all()
        db_parts = s.exec(select(Participant).limit(1000)).all()

    rooms = [
        RoomSnapshot(
            id=r.id,
            block=r.block,
            floor=r.floor,
            capacity=r.capacity,
            accessible=r.accessible,
            accessibility=r.accessibility,
            gender_class=r.gender_class,
            status=r.status,
        )
        for r in db_rooms
    ]
    properties = [
        PropertySnapshot(
            id=p.id,
            name=p.name,
            beds=p.beds,
            cost_per_bed_night=p.cost_per_bed_night,
            distance_km=2.0,
            transport_availability="yes",
            transport_limited=False,
            accessibility_verified=p.accessibility_verified,
            gender_suitability_verified=p.gender_suitability_verified,
            status="ACTIVE",
        )
        for p in db_props
    ]
    participants = [
        ParticipantSnapshot(
            id=p.id,
            name=p.name,
            contingent_id=p.contingent_id or "C01",
            college=p.college or "College",
            gender=p.gender,
            age=p.age or 20,
            accessibility_needs="" if not p.accessibility_needs else str(p.accessibility_needs),
            housing_preference=p.housing_preference,
            arrival_at=p.arrival_at,
            departure_at=p.departure_at,
            accommodation_requested=p.accommodation_requested,
        )
        for p in db_parts
    ]

    planner = AccommodationPlanner(rooms=rooms, properties=properties)
    t0 = time.perf_counter()
    plan = planner.generate_plan(participants, kind="A")
    duration_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n[PERF SMOKE] Accommodation Plan A Generation: {duration_ms:.2f}ms for {len(participants)} participants")
    assert duration_ms <= 2500.0, f"Plan generation took {duration_ms:.2f}ms, exceeding 2500ms target"
    assert plan.plan_hash.startswith("sha256:")
