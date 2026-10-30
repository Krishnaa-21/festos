# OWNER: P1
from datetime import datetime

from app.core.change_service import ChangeRequest, execute_change
from app.engines.transport import PureTransportEngine
from app.main import app
from app.models.change import Assumption
from app.models.participants import Participant
from app.models.transport import GuardianApproval, ShuttleAssignment, ShuttleRun
from app.schemas.common import Actor
from app.services.transport import public as transport_public
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def test_pure_transport_required_runs_formula():
    """Verify ceil(passengers / capacity) and edge cases: 0, exact multiple, and remainder."""
    calc = PureTransportEngine.calculate_required_runs

    # 0 passengers -> 0 runs
    assert calc(0, 15) == 0
    assert calc(-5, 15) == 0

    # 1 passenger -> 1 run
    assert calc(1, 15) == 1

    # Exact multiple: 30 / 15 -> 2 runs
    assert calc(30, 15) == 2

    # Remainder: 31 / 15 -> 3 runs
    assert calc(31, 15) == 3

    # Exact multiple: 45 / 15 -> 3 runs
    assert calc(45, 15) == 3

    # Remainder: 46 / 15 -> 4 runs
    assert calc(46, 15) == 4


def test_pure_transport_shuttle_planning():
    """Verify journey grouping, shortage calculation, and Lakeview Hotel high-risk rating."""
    passengers = [
        {"id": "p1", "property_id": "EXT04", "movement_time": "2026-10-31T00:30:00Z"},
        {"id": "p2", "property_id": "EXT04", "movement_time": "2026-10-31T00:30:00Z"},
        {"id": "p3", "property_id": "EXT04", "movement_time": "2026-10-31T00:30:00Z"},
    ]
    properties = [
        {
            "id": "EXT04",
            "name": "Lakeview Hotel",
            "distance_km": 9.0,
            "transport_availability": "limited",
        }
    ]
    # No runs scheduled yet
    res = PureTransportEngine.calculate_shuttle_plan(
        external_passengers=passengers,
        external_properties=properties,
        assumptions={"shuttle_capacity_seats": 2},
    )

    summary = res["plan_summary"]
    assert summary["total_passengers_external"] == 3
    # 3 passengers with capacity 2 -> ceil(3/2) = 2 runs required
    assert summary["total_runs_required"] == 2
    assert summary["shortage_runs"] == 2
    assert summary["is_capacity_deficit"] is True

    prop_plans = res["property_plans"]
    assert len(prop_plans) == 1
    assert prop_plans[0]["risk_level"] == "HIGH"
    assert prop_plans[0]["windows"][0]["is_uncovered"] is True


def test_pure_transport_night_roster_and_feasibility():
    """Verify late-night window detection and feasibility checks."""
    dt_night = datetime.fromisoformat("2026-10-31T00:30:00+00:00")
    dt_day = datetime.fromisoformat("2026-10-31T14:00:00+00:00")

    assert PureTransportEngine.is_late_night(dt_night, "22:00", "06:00") is True
    assert PureTransportEngine.is_late_night(dt_day, "22:00", "06:00") is False

    props = [{"id": "EXT04", "name": "Lakeview Hotel", "distance_km": 9.0}]

    # In day hours -> feasible
    f_day = PureTransportEngine.check_transport_feasibility(
        property_id="EXT04",
        target_time=dt_day,
        external_properties=props,
        assumptions={"transport_hours_start": "06:00", "transport_hours_end": "24:00"},
    )
    assert f_day["is_feasible"] is True

    # Late night without scheduled run -> infeasible
    f_night = PureTransportEngine.check_transport_feasibility(
        property_id="EXT04",
        target_time=dt_night,
        external_properties=props,
        assumptions={"transport_hours_start": "06:00", "transport_hours_end": "24:00"},
        scheduled_runs=[],
    )
    assert f_night["is_feasible"] is False

    # Late night with dedicated shuttle run -> feasible
    scheduled = [{"property_id": "EXT04", "departure_at": "2026-10-31T00:30:00+00:00"}]
    f_night_with_run = PureTransportEngine.check_transport_feasibility(
        property_id="EXT04",
        target_time=dt_night,
        external_properties=props,
        assumptions={"transport_hours_start": "06:00", "transport_hours_end": "24:00"},
        scheduled_runs=scheduled,
    )
    assert f_night_with_run["is_feasible"] is True


def test_transport_change_service_handlers(session: Session, director_actor: Actor):
    """Verify ChangeService handlers for update_assumptions, create_run, verify_safety, and approve_guardian."""
    # 1. Update assumptions
    req_asm = ChangeRequest(
        action="transport.update_assumptions",
        entity_type="assumption",
        entity_id="transport_assumptions",
        payload={"shuttle_capacity_seats": 20, "shuttle_vehicle_count": 6},
        actor=director_actor,
    )
    res_asm = execute_change(req_asm, session)
    assert res_asm.status == "APPLIED"

    asm = session.exec(select(Assumption).where(Assumption.key == "shuttle_capacity_seats")).first()
    assert asm is not None
    assert asm.value == "20"

    # 2. Create shuttle run
    req_run = ChangeRequest(
        action="transport.create_run",
        entity_type="shuttle_run",
        entity_id="new_run",
        payload={
            "route_name": "Campus to Lakeview Hotel",
            "property_id": "EXT04",
            "departure_at": "2026-10-31T23:30:00Z",
            "capacity": 20,
        },
        actor=director_actor,
    )
    res_run = execute_change(req_run, session)
    assert res_run.status == "APPLIED"
    run_id = res_run.data["run_id"]

    run_db = session.get(ShuttleRun, run_id)
    assert run_db is not None
    assert run_db.capacity == 20

    # 3. Verify safety
    req_ver = ChangeRequest(
        action="transport.verify_safety",
        entity_type="shuttle_assignment",
        entity_id="par_test",
        payload={
            "participant_id": "par_test",
            "shuttle_run_id": run_id,
            "escort_staff_id": "ST02",
            "verified": True,
            "notes": "Verified boarding with named escort",
        },
        actor=director_actor,
    )
    res_ver = execute_change(req_ver, session)
    assert res_ver.status == "APPLIED"

    asn_db = session.exec(select(ShuttleAssignment).where(ShuttleAssignment.participant_id == "par_test")).first()
    assert asn_db is not None
    assert asn_db.safety_verified is True

    # 4. Approve guardian
    gdn = GuardianApproval(
        id="gdn_test_01",
        participant_id="par_minor_01",
        property_id="EXT04",
        approval_status="PENDING",
    )
    session.add(gdn)
    session.commit()

    req_appr = ChangeRequest(
        action="transport.approve_guardian",
        entity_type="guardian_approval",
        entity_id="gdn_test_01",
        payload={
            "approval_id": "gdn_test_01",
            "approval_status": "APPROVED",
            "notes": "Signed guardian consent received and verified",
        },
        actor=director_actor,
    )
    res_appr = execute_change(req_appr, session)
    assert res_appr.status == "APPLIED"

    session.refresh(gdn)
    assert gdn.approval_status == "APPROVED"


def test_transport_api_endpoints():
    """Integration test verifying transport API endpoints match contract specifications."""
    client = TestClient(app)

    # 1. Assumptions
    resp_asm = client.get("/api/v1/transport/assumptions")
    assert resp_asm.status_code == 200
    asms = resp_asm.json()["data"]["assumptions"]
    assert "shuttle_capacity_seats" in asms
    assert asms["shuttle_capacity_seats"]["is_assumed"] is True

    # 2. Shuttle plan
    resp_plan = client.get("/api/v1/transport/shuttles/plan")
    assert resp_plan.status_code == 200
    plan = resp_plan.json()["data"]
    assert "plan_summary" in plan
    assert "property_plans" in plan

    # 3. Shuttle runs list
    resp_runs = client.get("/api/v1/transport/shuttles/runs")
    assert resp_runs.status_code == 200
    assert "runs" in resp_runs.json()["data"]

    # 4. Night safety roster
    resp_roster = client.get("/api/v1/transport/safety/night-roster")
    assert resp_roster.status_code == 200
    roster = resp_roster.json()["data"]
    assert "late_night_movements" in roster
    assert "total_unverified" in roster

    # 5. Guardian queue
    resp_gdn = client.get("/api/v1/transport/guardians/queue")
    assert resp_gdn.status_code == 200
    gdn_data = resp_gdn.json()["data"]
    assert "minors_queue" in gdn_data
    assert gdn_data["total"] >= 71

    # 6. Plain text alerts
    resp_alerts = client.get("/api/v1/transport/alerts")
    assert resp_alerts.status_code == 200
    alerts = resp_alerts.json()["data"]["alerts"]
    assert isinstance(alerts, list)
    assert len(alerts) > 0

    # 7. Coverage summary
    resp_cov = client.get("/api/v1/transport/coverage/summary")
    assert resp_cov.status_code == 200
    cov = resp_cov.json()["data"]
    assert "people_requiring_transport" in cov
    assert "confirmed_shuttle_capacity" in cov
    assert "uncovered_transport_requests" in cov

    # 8. Feasibility check
    resp_f = client.get("/api/v1/transport/feasibility?property_id=EXT04&time=2026-10-31T14:00:00Z")
    assert resp_f.status_code == 200
    f_data = resp_f.json()["data"]
    assert "is_feasible" in f_data
    assert f_data["is_feasible"] is True


def test_transport_public_and_participant_360(session: Session):
    """Test transport public contract and participant 360 dynamic section."""
    p_adult = Participant(id="P_ADULT", name="Adult Participant", age=22, status="ARRIVED")
    p_minor = Participant(id="P_MINOR", name="Minor Participant", age=17, status="ARRIVED")
    session.add(p_adult)
    session.add(p_minor)
    session.commit()

    sec_adult = transport_public.participant_transport_section("P_ADULT", session)
    assert sec_adult["is_minor"] is False
    assert sec_adult["guardian_approval_status"] == "NOT_REQUIRED"

    sec_minor = transport_public.participant_transport_section("P_MINOR", session)
    assert sec_minor["is_minor"] is True
    assert sec_minor["guardian_approval_status"] == "PENDING"

    # Feasibility helper for accommodation engine rule 6
    is_ok = transport_public.transport_feasible(session, "EXT01", datetime.fromisoformat("2026-10-31T12:00:00+00:00"))
    assert isinstance(is_ok, bool)

    # Resource timeline CSV
    csv_data = transport_public.resource_load_timeline_csv(session)
    assert "property_id" in csv_data
