# OWNER: P1
import os
from datetime import datetime, timezone

import pytest
from app.core.change_service import ChangeRequest, execute_change
from app.core.clock import set_demo_time
from app.core.db import get_engine, get_session, use_scenario
from app.main import app
from app.models.accommodation import Room
from app.models.audit import AuditEvent
from app.schemas.common import Actor
from app.services.scenarios import service as scenarios_service
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture
def client(session: Session):
    def get_test_session():
        yield session

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_scenario_fork_and_sandbox_isolation(session: Session):
    """Test database fork: sandbox mutations never touch live data (assert row counts & audit)."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # 1. Setup initial live data
    r1 = Room(id="RM_LIVE_1", block="H1", capacity=2, status="AVAILABLE")
    r2 = Room(id="RM_LIVE_2", block="H1", capacity=2, status="AVAILABLE")
    session.add_all([r1, r2])
    session.commit()

    live_rooms_before = len(session.exec(select(Room)).all())
    live_audit_before = len(session.exec(select(AuditEvent)).all())

    # 2. Fork into sandbox scenario
    scen_info = scenarios_service.create_scenario(session, name="Drill Sandbox", description="Testing isolation")
    scenario_id = scen_info["scenario_id"]

    try:
        # 3. Apply changes inside sandbox ONLY
        act_res = scenarios_service.execute_action_in_scenario(
            session=session,
            scenario_id=scenario_id,
            action="accommodation.close_hostel",
            entity_type="room",
            entity_id="H1",
            payload={"block": "H1", "status": "MAINTENANCE"},
            reason="Simulated plumbing failure",
        )
        assert act_res["status"] == "APPLIED_IN_SANDBOX"

        # 4. Assert sandbox reflects the mutation
        with use_scenario(scenario_id):
            scen_engine = get_engine()
            with Session(scen_engine) as scen_session:
                scen_rooms = scen_session.exec(select(Room).where(Room.block == "H1")).all()
                assert len(scen_rooms) == 2
                assert all(r.status == "MAINTENANCE" for r in scen_rooms)

        # 5. CRITICAL: Assert LIVE data is 100% UNTOUCHED
        live_rooms_after = session.exec(select(Room).where(Room.block == "H1")).all()
        assert len(live_rooms_after) == live_rooms_before
        assert all(r.status == "AVAILABLE" for r in live_rooms_after), "Live rooms were mutated by sandbox!"

        live_audit_after = len(session.exec(select(AuditEvent)).all())
        assert live_audit_after == live_audit_before, "Live audit log was mutated by sandbox!"
    finally:
        scenarios_service.discard_scenario(session, scenario_id)


def test_multiple_parallel_scenarios(session: Session):
    """Test running multiple isolated scenarios in parallel without interference."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Base rooms in blocks H1 and H2
    r_h1 = Room(id="RM_H1", block="H1", capacity=2, status="AVAILABLE")
    r_h2 = Room(id="RM_H2", block="H2", capacity=2, status="AVAILABLE")
    session.add_all([r_h1, r_h2])
    session.commit()

    # Fork Scenario A (closes H1) and Scenario B (closes H2)
    s_a = scenarios_service.create_scenario(session, name="Scenario A")["scenario_id"]
    s_b = scenarios_service.create_scenario(session, name="Scenario B")["scenario_id"]

    try:
        scenarios_service.execute_action_in_scenario(
            session=session,
            scenario_id=s_a,
            action="accommodation.close_hostel",
            entity_type="room",
            entity_id="H1",
            payload={"block": "H1", "status": "MAINTENANCE"},
        )

        scenarios_service.execute_action_in_scenario(
            session=session,
            scenario_id=s_b,
            action="accommodation.close_hostel",
            entity_type="room",
            entity_id="H2",
            payload={"block": "H2", "status": "MAINTENANCE"},
        )

        # Verify Scenario A: H1 is MAINTENANCE, H2 is AVAILABLE
        with use_scenario(s_a):
            with Session(get_engine()) as s_a_sess:
                assert s_a_sess.get(Room, "RM_H1").status == "MAINTENANCE"
                assert s_a_sess.get(Room, "RM_H2").status == "AVAILABLE"

        # Verify Scenario B: H1 is AVAILABLE, H2 is MAINTENANCE
        with use_scenario(s_b):
            with Session(get_engine()) as s_b_sess:
                assert s_b_sess.get(Room, "RM_H1").status == "AVAILABLE"
                assert s_b_sess.get(Room, "RM_H2").status == "MAINTENANCE"

        # Verify LIVE: both are AVAILABLE
        assert session.get(Room, "RM_H1").status == "AVAILABLE"
        assert session.get(Room, "RM_H2").status == "AVAILABLE"
    finally:
        scenarios_service.discard_scenario(session, s_a)
        scenarios_service.discard_scenario(session, s_b)


def test_scenario_compare_returns_metric_diffs(session: Session):
    """Test GET /scenarios/{id}/compare returns metric diffs versus live."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Live rooms with 4 total beds
    r1 = Room(id="RM_DIFF_1", block="H1", capacity=2, status="AVAILABLE")
    r2 = Room(id="RM_DIFF_2", block="H1", capacity=2, status="AVAILABLE")
    session.add_all([r1, r2])
    session.commit()

    scen = scenarios_service.create_scenario(session, name="Compare Test")
    scen_id = scen["scenario_id"]

    try:
        # Close H1 in sandbox: removes 4 available beds
        scenarios_service.execute_action_in_scenario(
            session=session,
            scenario_id=scen_id,
            action="accommodation.close_hostel",
            entity_type="room",
            entity_id="H1",
            payload={"block": "H1", "status": "MAINTENANCE"},
        )

        comp = scenarios_service.compare_scenario(session, scen_id)
        diff = comp["diff"]

        assert "beds_delta" in diff
        assert "unplaced_delta" in diff
        assert "cost_delta_inr" in diff
        assert "conflicts_delta" in diff
        assert "risks_delta" in diff
        assert diff["beds_delta"] == -4
        assert "summary" in comp
    finally:
        scenarios_service.discard_scenario(session, scen_id)


def test_scenario_commit_replays_recorded_changes(session: Session, director_actor: Actor):
    """Test scenario commit replays recorded actions onto live database after approval."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Initial live room
    r = Room(id="RM_COMMIT_1", block="H3", capacity=3, status="AVAILABLE")
    session.add(r)
    session.commit()

    scen = scenarios_service.create_scenario(session, name="Commit Test")
    scen_id = scen["scenario_id"]

    # Record action in sandbox
    scenarios_service.execute_action_in_scenario(
        session=session,
        scenario_id=scen_id,
        action="accommodation.update_room",
        entity_type="room",
        entity_id="RM_COMMIT_1",
        payload={"status": "MAINTENANCE"},
        reason="Scheduled AC repair",
    )

    # Commit scenario to live
    commit_res = scenarios_service.commit_scenario(
        session=session,
        scenario_id=scen_id,
        actor=director_actor,
        reason="Approved by Festival Director",
    )

    assert commit_res["status"] == "COMMITTED"
    assert commit_res["replayed_actions_count"] == 1
    assert len(commit_res["live_changesets_created"]) == 1

    # Assert live room now reflects the committed change
    live_room = session.get(Room, "RM_COMMIT_1")
    assert live_room.status == "MAINTENANCE"


def test_stale_fork_rebase_divergence_warning(session: Session, director_actor: Actor):
    """Test stale-fork commit detects live database mutation and issues divergence warning."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Setup base entity
    r = Room(id="RM_STALE_1", block="H4", capacity=2, status="AVAILABLE")
    session.add(r)
    session.commit()

    # 1. Fork scenario when live changeset count is N
    scen = scenarios_service.create_scenario(session, name="Stale Fork Test")
    scen_id = scen["scenario_id"]

    # 2. Add an action in the scenario
    scenarios_service.execute_action_in_scenario(
        session=session,
        scenario_id=scen_id,
        action="accommodation.update_room",
        entity_type="room",
        entity_id="RM_STALE_1",
        payload={"status": "RESERVED"},
    )

    # 3. Mutate LIVE database directly (creating a new ChangeSet N+1)
    req = ChangeRequest(
        action="accommodation.update_room",
        entity_type="room",
        entity_id="RM_STALE_1",
        payload={"capacity": 4},
        reason="Live emergency upgrade",
        actor=director_actor,
    )
    execute_change(req, session)
    session.commit()

    # 4. Commit scenario: should detect divergence
    commit_res = scenarios_service.commit_scenario(
        session=session,
        scenario_id=scen_id,
        actor=director_actor,
    )

    assert commit_res["rebase_status"] == "DIVERGED"
    assert len(commit_res["warnings"]) > 0
    assert "Live database has mutated since this scenario was forked" in commit_res["warnings"][0]


def test_scenario_discard_cleans_file(session: Session):
    """Test scenario discard removes the sandbox database file."""
    scen = scenarios_service.create_scenario(session, name="Discard Test")
    scen_id = scen["scenario_id"]
    db_file = os.path.join("scenarios", f"{scen_id}.db")

    assert os.path.exists(db_file), "Sandbox file was not created"

    # Discard scenario
    res = scenarios_service.discard_scenario(session, scen_id)
    assert res["status"] == "DISCARDED"
    assert not os.path.exists(db_file), "Sandbox file was not removed after discard!"


def test_incident_simulation_adapter(session: Session):
    """Test Prompt 14 incident simulation adapter inside a scenario sandbox."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Add hostel block H5
    r = Room(id="RM_H5", block="H5", capacity=20, status="AVAILABLE")
    session.add(r)
    session.commit()

    scen = scenarios_service.create_scenario(session, name="Incident Simulation Drill")
    scen_id = scen["scenario_id"]

    try:
        res = scenarios_service.simulate_incident_in_scenario(
            session=session,
            scenario_id=scen_id,
            incident_type="HOSTEL_PIPE_BURST",
            target_id="H5",
            severity=4,
            details="Major pipe burst flooding ground floor rooms",
        )

        assert res["status"] == "SIMULATED"
        assert res["impact"]["affected_people"] >= 20
        assert len(res["impact"]["immediate_actions_required"]) > 0

        # Verify live room in H5 is STILL AVAILABLE
        assert session.get(Room, "RM_H5").status == "AVAILABLE"
    finally:
        scenarios_service.discard_scenario(session, scen_id)


def test_full_acceptance_drill(session: Session, director_actor: Actor):
    """ACCEPTANCE: fork live data, close a hostel in the sandbox, compare, discard,
    and show live data untouched; then commit another scenario with approval.
    """
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Base live state: 2 rooms in Hostel A (4 beds total)
    r1 = Room(id="RM_ACC_A1", block="HA", capacity=2, status="AVAILABLE")
    r2 = Room(id="RM_ACC_A2", block="HA", capacity=2, status="AVAILABLE")
    session.add_all([r1, r2])
    session.commit()

    live_room_count_initial = len(session.exec(select(Room)).all())
    live_audit_count_initial = len(session.exec(select(AuditEvent)).all())

    # STEP 1: Fork live data into Scenario 1 (Disruption drill)
    s1 = scenarios_service.create_scenario(session, name="Acceptance Drill 1 - Closure")
    s1_id = s1["scenario_id"]

    # STEP 2: Close hostel block 'HA' in the sandbox
    scenarios_service.execute_action_in_scenario(
        session=session,
        scenario_id=s1_id,
        action="accommodation.close_hostel",
        entity_type="room",
        entity_id="HA",
        payload={"block": "HA", "status": "MAINTENANCE"},
        reason="Emergency structural inspection",
    )

    # STEP 3: Compare Scenario 1 against live
    comp1 = scenarios_service.compare_scenario(session, s1_id)
    assert comp1["diff"]["beds_delta"] == -4
    assert comp1["simulated_state"]["available_beds"] == comp1["live_state"]["available_beds"] - 4

    # STEP 4: Discard Scenario 1
    scenarios_service.discard_scenario(session, s1_id)

    # STEP 5: PROVE LIVE DATA IS UNTOUCHED
    live_rooms_check = session.exec(select(Room).where(Room.block == "HA")).all()
    assert len(live_rooms_check) == 2
    assert all(r.status == "AVAILABLE" for r in live_rooms_check), "LIVE data was touched during discarded drill!"
    assert len(session.exec(select(Room)).all()) == live_room_count_initial
    assert len(session.exec(select(AuditEvent)).all()) == live_audit_count_initial

    # STEP 6: Fork live data into Scenario 2 (Approval plan)
    s2 = scenarios_service.create_scenario(session, name="Acceptance Drill 2 - Approved Plan")
    s2_id = s2["scenario_id"]

    # STEP 7: Apply planned room capacity reconfiguration in Scenario 2
    scenarios_service.execute_action_in_scenario(
        session=session,
        scenario_id=s2_id,
        action="accommodation.update_room",
        entity_type="room",
        entity_id="RM_ACC_A1",
        payload={"capacity": 3},
        reason="Approved extra bed placement",
    )

    # STEP 8: Commit Scenario 2 with approval
    commit_res = scenarios_service.commit_scenario(
        session=session,
        scenario_id=s2_id,
        actor=director_actor,
        reason="Festival Director sign-off on accommodation plan",
    )

    # STEP 9: Verify committed state on LIVE
    assert commit_res["status"] == "COMMITTED"
    assert session.get(Room, "RM_ACC_A1").capacity == 3
    assert len(session.exec(select(AuditEvent)).all()) > live_audit_count_initial
