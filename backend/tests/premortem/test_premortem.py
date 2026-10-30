# OWNER: P2
from datetime import datetime, timezone
import pytest
from sqlmodel import Session

from app.engines.premortem.disruptions import (
    find_single_points_of_failure,
    run_seeded_multi_disruptions,
    run_targeted_disruption,
)
from app.engines.premortem.resilience import calculate_resilience_score
from app.engines.premortem.timeline import compute_hourly_state, generate_hourly_timeline
from app.models.accommodation import ExternalProperty, Room
from app.models.events import Event
from app.models.participants import Participant
from app.models.vendors import Vendor


def test_premortem_timeline_equals_independent_hourly_recomputation(session: Session):
    """Pre-mortem timeline sequence equals independent hourly state recomputation on a fixture."""
    # Seed room, participant, event, vendor
    r = Room(id="r_pm_01", block="A", capacity=4, gender_class="BOYS", status="READY")
    p = Participant(
        id="p_pm_01",
        name="Anand Sen",
        gender="Male",
        accommodation_requested="YES",
        arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
        departure_at=datetime(2026, 10, 31, 20, 0, tzinfo=timezone.utc),
        status="EXPECTED",
    )
    v = Vendor(id="v_pm_01", name="Food Point", status="ACTIVE", capacity_per_meal=150)
    ev = Event(
        id="ev_pm_01",
        name="Keynote Debate",
        code="EV_DEBATE",
        start_time=datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
        venue_id="V_AUD_01",
        status="CONFIRMED",
    )
    session.add_all([r, p, v, ev])
    session.commit()

    start_time = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)

    # 1. Timeline engine run
    timeline_result = generate_hourly_timeline(session, start_time=start_time, end_time=end_time, step_hours=1)
    intervals = timeline_result["timeline"]
    assert len(intervals) == 4  # 09:00, 10:00, 11:00, 12:00

    # 2. Independent hourly recomputation check for 10:00 UTC
    target_hour = datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc)
    independent_state = compute_hourly_state(session, target_hour)

    interval_10am = next(i for i in intervals if i["timestamp"] == target_hour.isoformat())

    assert interval_10am["accommodation"]["total_beds"] == independent_state["accommodation"]["total_beds"]
    assert interval_10am["accommodation"]["occupied_beds"] == independent_state["accommodation"]["occupied_beds"]
    assert interval_10am["venues"]["active_events"] == independent_state["venues"]["active_events"]
    assert interval_10am["food"]["vendor_capacity"] == independent_state["food"]["vendor_capacity"]
    assert interval_10am["max_severity"] == independent_state["max_severity"]


def test_resilience_score_changes_in_expected_direction_when_redundancy_added(session: Session):
    """Resilience score strictly increases when redundancy (spare beds, extra caterers) is added."""
    # Initial state with tight capacity
    p = Participant(id="p_res_01", name="Kunal", status="EXPECTED", accommodation_requested="YES")
    session.add(p)
    session.commit()

    initial_resilience = calculate_resilience_score(session)
    initial_score = initial_resilience["festival_resilience_score"]

    # Add standby accommodation beds (redundancy)
    redundant_resilience = calculate_resilience_score(
        session,
        additional_beds=200,
        additional_vendors=2,
        additional_equipment=30,
    )
    new_score = redundant_resilience["festival_resilience_score"]

    assert new_score > initial_score, f"Expected new_score ({new_score}) > initial_score ({initial_score})"
    assert redundant_resilience["components"]["accommodation_buffer"]["score"] >= initial_resilience["components"]["accommodation_buffer"]["score"]
    assert redundant_resilience["components"]["vendor_redundancy"]["score"] >= initial_resilience["components"]["vendor_redundancy"]["score"]


def test_seeded_randomness_is_reproducible(session: Session):
    """Running multi-disruptions with the same seed produces exact identical outputs."""
    res_a = run_seeded_multi_disruptions(session, seed=12345, disruption_count=4)
    res_b = run_seeded_multi_disruptions(session, seed=12345, disruption_count=4)

    assert res_a["total_unique_people_affected"] == res_b["total_unique_people_affected"]
    assert res_a["composite_resilience_score"] == res_b["composite_resilience_score"]
    assert res_a["disruptions_applied"] == res_b["disruptions_applied"]
    assert res_a["spofs_exposed"] == res_b["spofs_exposed"]

    # Different seed gives different results
    res_c = run_seeded_multi_disruptions(session, seed=99999, disruption_count=4)
    assert res_c["disruptions_applied"] != res_a["disruptions_applied"]


def test_spof_detection_and_targeted_disruption(session: Session):
    """Detects SPOFs and simulates targeted hostel and vendor disruptions in sandbox."""
    # Seed large block
    r1 = Room(id="r_spof_01", block="MEGA_BLOCK", capacity=120, gender_class="BOYS", status="READY")
    v1 = Vendor(id="v_spof_01", name="Jain Deluxe", status="ACTIVE", capacity_per_meal=250, dietary_options="Jain;Vegan")
    session.add_all([r1, v1])
    session.commit()

    spofs = find_single_points_of_failure(session)
    spof_ids = [s["entity_id"] for s in spofs]
    assert any("MEGA_BLOCK" in sid for sid in spof_ids)
    assert "v_spof_01" in spof_ids

    # Run targeted disruption
    disr = run_targeted_disruption(session, disruption_type="HOSTEL_CLOSURE", target_entity_id="MEGA_BLOCK")
    assert disr["disruption_type"] == "HOSTEL_CLOSURE"
    assert disr["people_affected"] == 120
    assert disr["is_spof"] is True
    assert len(disr["preventive_actions"]) > 0
    assert "CONTRACT_STANDBY_EXTERNAL_BEDS" in disr["preventive_actions"][0]["action"]
