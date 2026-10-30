# OWNER: P1
from datetime import datetime, timedelta, timezone

import pytest
from app.core import bus
from app.core.clock import set_demo_time
from app.core.scoring import (
    calculate_attention_score,
    heatmap_bucket,
    urgency_from_hours,
)
from app.main import app
from app.models.accommodation import Room
from app.models.audit import Approval, Override
from app.models.change import Scenario
from app.models.events import Conflict, EventSession
from app.models.ops import Incident
from app.models.participants import Participant
from app.models.vendors import Vendor
from app.schemas.common import Role, Severity
from app.services.dashboard import public as dashboard_public
from app.services.dashboard import service as dashboard_service
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_metrics_aggregation_and_spec_list(session: Session):
    """Test GET /dashboard/metrics aggregates every module's summary into the canonical spec list."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Populate sample rows
    p1 = Participant(id="P1", name="Alice", status="ARRIVED", diet="REGULAR")
    p2 = Participant(id="P2", name="Bob", status="CHECKED_IN", diet="VEG")
    p3 = Participant(id="P3", name="Charlie", status="EXPECTED", accommodation_requested="YES")
    session.add_all([p1, p2, p3])

    r1 = Room(id="RM1", block="H1", capacity=2, status="AVAILABLE")
    session.add(r1)

    s1 = EventSession(id="SES1", event_id="EV1", name="Dance Solo", status="SCHEDULED")
    c1 = Conflict(id="CONF1", conflict_type="VENUE_DOUBLE_BOOKING", severity=3, status="OPEN", description="Venue double booked")
    session.add_all([s1, c1])

    v1 = Vendor(id="VND1", name="Campus Caterers", status="ACTIVE")
    session.add(v1)

    inc1 = Incident(id="INC1", title="Water outage", severity=3, description="Leak in H1", status="OPEN")
    appr1 = Approval(id="APP1", entity_type="participant", entity_id="P3", status="PENDING")
    ovr1 = Override(id="OVR1", entity_type="session", entity_id="SES1", constraint_code="TRAVEL_TIME", status="ACTIVE", reason="Test")
    session.add_all([inc1, appr1, ovr1])
    session.commit()

    # Invalidate any cache first
    dashboard_service.invalidate_metrics_cache()

    metrics = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=True, now_dt=t0)

    # Spec list assertions
    assert "total_participants" in metrics
    assert "arrived" in metrics
    assert "checked_in" in metrics
    assert "pending_arrivals" in metrics
    assert "occupancy" in metrics
    assert "available_beds" in metrics
    assert "unplaced" in metrics
    assert "active_sessions" in metrics
    assert "open_conflicts" in metrics
    assert "equipment_availability" in metrics
    assert "merchandise_stock" in metrics
    assert "vendor_status" in metrics
    assert "food_coverage_gaps" in metrics
    assert "staff_availability" in metrics
    assert "open_incidents" in metrics
    assert "pending_approvals" in metrics
    assert "active_overrides" in metrics

    assert metrics["total_participants"] >= 3
    assert metrics["arrived"] >= 1
    assert metrics["checked_in"] >= 1
    assert metrics["pending_arrivals"] >= 1
    assert metrics["open_conflicts"] >= 1
    assert metrics["open_incidents"] >= 1
    assert metrics["pending_approvals"] >= 1
    assert metrics["active_overrides"] >= 1


def test_metrics_cache_ttl_and_bus_invalidation(session: Session):
    """Test short TTL caching and cache invalidation on bus change events."""
    t0 = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    dashboard_service.invalidate_metrics_cache()
    # Re-register bus subscriber in case clean_test_env cleared it
    bus.subscribe("*")(dashboard_service._on_bus_mutation_event)

    # Initial fetch (cache miss)
    m1 = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=False, now_dt=t0)
    assert m1["is_cached"] is False

    # Second fetch within TTL (cache hit)
    t1 = t0 + timedelta(seconds=5)
    m2 = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=False, now_dt=t1)
    assert m2["is_cached"] is True

    # Bus event published: must invalidate cache
    bus.publish("participant.status_changed", {"participant_id": "P1", "status": "CHECKED_IN"})
    m3 = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=False, now_dt=t1)
    assert m3["is_cached"] is False

    # Cache hit again
    m4 = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=False, now_dt=t1)
    assert m4["is_cached"] is True

    # After TTL (15s): expired cache triggers recalculation
    t2 = t0 + timedelta(seconds=20)
    m5 = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=False, now_dt=t2)
    assert m5["is_cached"] is False


def test_role_aware_subsets_volunteer(session: Session):
    """Test role-aware filtering: Volunteer gets nothing sensitive."""
    t0 = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    inc = Incident(id="INC_PRIV", title="Medical emergency", severity=4, description="Confidential", status="OPEN")
    appr = Approval(id="APP_PRIV", entity_type="budget", entity_id="B1", status="PENDING")
    ovr = Override(id="OVR_PRIV", entity_type="safety", entity_id="S1", constraint_code="FIRE_CAP", status="ACTIVE", reason="Test")
    session.add_all([inc, appr, ovr])
    session.commit()

    # Festival Director sees governance numbers
    dir_metrics = dashboard_service.get_metrics(session, actor_role=Role.FESTIVAL_DIRECTOR.value, bypass_cache=True, now_dt=t0)
    assert dir_metrics["open_incidents"] >= 1
    assert dir_metrics["pending_approvals"] >= 1
    assert dir_metrics["active_overrides"] >= 1
    assert dir_metrics["governance"]["open_incidents"] >= 1

    # Volunteer gets sanitized metrics (sensitive fields None or redacted)
    vol_metrics = dashboard_service.get_metrics(session, actor_role=Role.VOLUNTEER.value, bypass_cache=True, now_dt=t0)
    assert vol_metrics["open_incidents"] is None
    assert vol_metrics["pending_approvals"] is None
    assert vol_metrics["active_overrides"] is None
    assert vol_metrics["governance"]["open_incidents"] is None
    assert vol_metrics["governance"]["note"] == "REDACTED_FOR_ROLE"


def test_attention_queue_ranking_matches_hand_computed_scores(session: Session):
    """Test ranking strictly matches hand-computed scores using core.scoring only."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Compute expected scores for hand cases:
    # Item 1: Sev 4, Impact in 0.5h (Urgency 5), People: 50 -> 4 * 5 * 50 = 1000.0
    # Item 2: Sev 3, Impact in 3h (Urgency 4), People: 20 -> 3 * 4 * 20 = 240.0
    # Item 3: Sev 2, Impact in 10h (Urgency 3), People: 5 -> 2 * 3 * 5 = 30.0
    # Item 4: Sev 1, Impact in 30h (Urgency 1), People: 1 -> 1 * 1 * 1 = 1.0

    assert calculate_attention_score(4, 0.5, 50) == 1000.0
    assert calculate_attention_score(3, 3.0, 20) == 240.0
    assert calculate_attention_score(2, 10.0, 5) == 30.0
    assert calculate_attention_score(1, 30.0, 1) == 1.0

    # Populate items to trigger multiple risks
    # 1. Urgent accessibility participant arriving in 1 hour
    p1 = Participant(
        id="P_ACC",
        name="Wheelchair Attendee",
        status="EXPECTED",
        arrival_at=t0 + timedelta(hours=1),
        accessibility_needs={"wheelchair": True},
    )
    # 2. Overdue participant
    p2 = Participant(
        id="P_LATE",
        name="Late Attendee",
        status="EXPECTED",
        arrival_at=t0 - timedelta(hours=2),
    )
    # 3. Pending approval
    appr = Approval(
        id="APP_CRIT",
        entity_type="participant",
        entity_id="P_ACC",
        status="PENDING",
    )
    session.add_all([p1, p2, appr])
    session.commit()

    queue = dashboard_service.get_attention_queue(session, limit=50, now_dt=t0)
    items = queue["attention_items"]
    assert len(items) > 0

    # Verify every item in queue has score equal to calculate_attention_score
    for it in items:
        expected_score = calculate_attention_score(it["severity"], it["hours_to_impact"], it["people_affected"])
        assert it["score"] == expected_score

    # Verify strictly sorted in descending order of score
    scores = [it["score"] for it in items]
    assert scores == sorted(scores, reverse=True)


def test_attention_queue_deduplication_and_direct_actions(session: Session):
    """Test each module's risks appear exactly once (deduplicated) and every item carries a direct action."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    queue = dashboard_service.get_attention_queue(session, limit=100, now_dt=t0)
    items = queue["attention_items"]

    seen_ids = set()
    for it in items:
        # Deduplication check
        unique_key = (it["module"], it["kind"], it["id"])
        assert unique_key not in seen_ids, f"Duplicate risk item found: {unique_key}"
        seen_ids.add(unique_key)

        # Direct action check
        assert "action" in it
        act = it["action"]
        assert act is not None
        assert "route" in act and act["route"].startswith("/")
        assert "api" in act and act["api"].startswith("/")
        assert "label" in act and len(act["label"]) > 0


def test_heatmap_bucketing_and_edge_cases(session: Session):
    """Test heatmap matrix coordinates, edge case time windows, and critical quadrant."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Edge cases for urgency from hours
    assert urgency_from_hours(0.0) == 5       # Immediate (<= 1h)
    assert urgency_from_hours(1.0) == 5
    assert urgency_from_hours(1.1) == 4       # High priority (<= 4h)
    assert urgency_from_hours(4.0) == 4
    assert urgency_from_hours(4.1) == 3       # Elevated (<= 12h)
    assert urgency_from_hours(12.0) == 3
    assert urgency_from_hours(12.1) == 2      # Upcoming (<= 24h)
    assert urgency_from_hours(24.0) == 2
    assert urgency_from_hours(24.1) == 1      # Monitor (> 24h)
    assert urgency_from_hours(None) == 1

    # Heatmap bucket edge cases
    b1 = heatmap_bucket(Severity.CRITICAL, 0.5)
    assert b1["severity"] == 4
    assert b1["urgency"] == 5
    assert b1["is_critical_quadrant"] is True

    b2 = heatmap_bucket(Severity.LOW, 48.0)
    assert b2["severity"] == 1
    assert b2["urgency"] == 1
    assert b2["is_critical_quadrant"] is False

    heatmap = dashboard_service.get_risk_heatmap(session, now_dt=t0)
    matrix = heatmap["matrix"]
    summary = heatmap["summary"]

    assert "total_risks_mapped" in summary
    assert "critical_quadrant_risks" in summary

    # Verify each cell structure
    for cell in matrix:
        assert 1 <= cell["severity"] <= 4
        assert 1 <= cell["urgency"] <= 5
        assert cell["risk_count"] >= 1
        assert "people_affected" in cell
        assert "avg_uncertainty" in cell
        assert "max_criticality" in cell
        assert "top_risks" in cell
        if cell["severity"] >= 3 and cell["urgency"] >= 4:
            assert cell["is_critical_quadrant"] is True
        else:
            assert cell["is_critical_quadrant"] is False


def test_dashboard_public_contract(session: Session):
    """Test dashboard public module contract (summary and risks for stale cache / uncommitted scenarios)."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # 1. Dashboard summary
    summ = dashboard_public.summary(session, t0)
    assert summ["module"] == "dashboard"
    assert summ["status"] == "OPERATIONAL"

    # 2. Add an uncommitted scenario with recorded actions
    scn = Scenario(
        id="SCN_TEST_DECISION",
        name="Hostel Block Closure Drill",
        status="DRAFT",
        created_at=t0 - timedelta(hours=8),
        recorded_actions=[{"action": "accommodation.close_hostel", "entity_id": "H1"}],
    )
    session.add(scn)
    session.commit()

    # 3. Simulate stale metrics cache (> 60s)
    dashboard_service._metrics_cache = {"total_participants": 100}
    dashboard_service._cache_timestamp = t0 - timedelta(seconds=120)

    risks = dashboard_public.risks(session, t0)
    kinds = [r.kind for r in risks]

    assert "STALE_METRICS_CACHE" in kinds
    assert "SCENARIO_AWAITING_DECISION" in kinds
