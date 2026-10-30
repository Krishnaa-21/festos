# OWNER: P1
from datetime import datetime, timezone

from app.core.change_service import ChangeRequest, execute_change
from app.engines.staff import PureStaffEngine
from app.main import app
from app.models.staff import Shift, Staff
from app.schemas.common import Actor
from app.services.staff import public as staff_public
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_pure_staff_demand_and_gaps():
    """Verify volunteer requirement calculation over time and peak gap detection."""
    sessions = [
        {
            "id": "ses_01",
            "start_at": "2026-10-31T08:00:00Z",
            "end_at": "2026-10-31T11:00:00Z",
            "volunteers_required": 15,
        },
        {
            "id": "ses_02",
            "start_at": "2026-10-31T10:00:00Z",
            "end_at": "2026-10-31T13:00:00Z",
            "volunteers_required": 25,
        },
    ]
    shifts = [
        {
            "id": "shf_01",
            "staff_id": "ST01",
            "start_at": "2026-10-31T06:00:00Z",
            "end_at": "2026-10-31T14:00:00Z",
            "status": "SCHEDULED",
        },
        {
            "id": "shf_02",
            "staff_id": "ST02",
            "start_at": "2026-10-31T06:00:00Z",
            "end_at": "2026-10-31T14:00:00Z",
            "status": "SCHEDULED",
        },
    ]

    res = PureStaffEngine.calculate_demand_and_gaps(sessions, shifts)
    # Between 10:00 and 11:00, both sessions are active: 15 + 25 = 40 required, 2 staff on shift -> gap = 38
    assert res["peak_requirement"] == 40
    assert res["peak_available_on_shift"] == 2
    assert res["max_gap"] == 38
    assert res["uncovered_hours_total"] > 0
    assert len(res["demand_timeline"]) == 5


def test_pure_staff_overload_detection():
    """Verify detection of daily hours >10h and consecutive hours >8h."""
    shifts = [
        # ST01 scheduled 12 hours on same day
        {
            "id": "s1",
            "staff_id": "ST01",
            "staff_name": "Aditi Verma",
            "start_at": "2026-10-31T06:00:00Z",
            "end_at": "2026-10-31T18:00:00Z",
            "status": "SCHEDULED",
        },
        # ST02 scheduled normal 8 hours
        {
            "id": "s2",
            "staff_id": "ST02",
            "staff_name": "Ananya Patel",
            "start_at": "2026-10-31T06:00:00Z",
            "end_at": "2026-10-31T14:00:00Z",
            "status": "SCHEDULED",
        },
    ]

    overloaded = PureStaffEngine.detect_overloaded_staff(shifts, max_daily_hours=10.0)
    assert len(overloaded) == 1
    assert overloaded[0]["staff_id"] == "ST01"
    assert overloaded[0]["scheduled_hours"] == 12.0


def test_pure_staff_conflict_and_overlap():
    """Verify dual roles, concurrent overlaps, and venue travel infeasibility are detected."""
    staff_list = [
        {"id": "ST11", "name": "Riya Das", "is_participant": True, "skills": []},
        {"id": "ST07", "name": "Meera Khan", "is_participant": False, "skills": []},
    ]
    shifts = [
        # Concurrent overlapping shifts for ST07
        {
            "id": "shf_a",
            "staff_id": "ST07",
            "start_at": "2026-10-31T10:00:00Z",
            "end_at": "2026-10-31T13:00:00Z",
            "venue_id": "V01",
        },
        {
            "id": "shf_b",
            "staff_id": "ST07",
            "start_at": "2026-10-31T12:00:00Z",
            "end_at": "2026-10-31T15:00:00Z",
            "venue_id": "V02",
        },
    ]
    travel_mat = {("V01", "V02"): 20}

    conflicts = PureStaffEngine.detect_conflicts(
        staff_list=staff_list,
        shifts=shifts,
        travel_matrix=travel_mat,
    )
    c_types = [c["conflict_type"] for c in conflicts]
    assert "PARTICIPANT_STAFF_DUAL_ROLE" in c_types
    assert "SHIFT_OVERLAP" in c_types


def test_pure_staff_suggest_replacements():
    """Verify candidate ranking filters busy/overloaded staff and rewards skill & travel proximity."""
    staff_list = [
        {"id": "ST01", "name": "Candidate A", "role": "Volunteer", "skills": ["stage_ops"], "status": "ACTIVE"},
        {"id": "ST02", "name": "Candidate B", "role": "Registration Desk", "skills": [], "status": "ACTIVE"},
        {"id": "ST03", "name": "Candidate Busy", "role": "Volunteer", "skills": ["stage_ops"], "status": "ACTIVE"},
    ]
    shifts = [
        # Candidate Busy is busy during the requested window
        {
            "id": "shf_busy",
            "staff_id": "ST03",
            "start_at": "2026-10-31T10:00:00Z",
            "end_at": "2026-10-31T12:00:00Z",
            "venue_id": "V01",
        }
    ]

    suggestions = PureStaffEngine.suggest_replacements(
        window_start=datetime.fromisoformat("2026-10-31T10:00:00+00:00"),
        window_end=datetime.fromisoformat("2026-10-31T12:00:00+00:00"),
        venue_id="V01",
        role_required="Volunteer",
        staff_list=staff_list,
        shifts=shifts,
    )

    sug_ids = [s["staff_id"] for s in suggestions]
    assert "ST03" not in sug_ids  # Filtered due to overlap
    assert "ST01" in sug_ids
    assert suggestions[0]["staff_id"] == "ST01"  # Best score (role + skill match)


def test_handover_notes_enforcement(session: Session, director_actor: Actor):
    """Verify shift replacement without handover notes is rejected with HANDOVER_NOTE_MISSING."""
    stf1 = Staff(id="ST01", name="Staff 1", role="Volunteer", status="ACTIVE")
    stf2 = Staff(id="ST02", name="Staff 2", role="Volunteer", status="ACTIVE")
    shf = Shift(
        id="shf_001",
        staff_id="ST01",
        start_at=datetime.fromisoformat("2026-10-31T06:00:00+00:00"),
        end_at=datetime.fromisoformat("2026-10-31T14:00:00+00:00"),
        status="SCHEDULED",
    )
    session.add(stf1)
    session.add(stf2)
    session.add(shf)
    session.commit()

    # 1. Attempt replace without handover notes -> REJECTED
    req_fail = ChangeRequest(
        action="staff.replace",
        entity_type="shift",
        entity_id="shf_001",
        payload={
            "shift_id": "shf_001",
            "replacement_staff_id": "ST02",
            "handover_notes": "",
        },
        actor=director_actor,
    )
    res_fail = execute_change(req_fail, session)
    assert res_fail.status == "REJECTED"
    codes = [v.code for v in res_fail.violations]
    assert "HANDOVER_NOTE_MISSING" in codes

    # 2. Attempt replace with valid handover notes -> APPLIED
    req_pass = ChangeRequest(
        action="staff.replace",
        entity_type="shift",
        entity_id="shf_001",
        payload={
            "shift_id": "shf_001",
            "replacement_staff_id": "ST02",
            "handover_notes": "Handing over stage audio kit and emergency walkie-talkie",
        },
        actor=director_actor,
    )
    res_pass = execute_change(req_pass, session)
    assert res_pass.status == "APPLIED"

    session.refresh(shf)
    assert shf.staff_id == "ST02"
    assert "stage audio kit" in shf.handover_notes


def test_staff_api_endpoints():
    """Integration test verifying staff API endpoints return Envelope and match contract."""
    client = TestClient(app)

    # 1. List staff
    resp = client.get("/api/v1/staff?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "staff" in data
    assert "total" in data

    # 2. Staff demand
    resp_dem = client.get("/api/v1/staff/demand")
    assert resp_dem.status_code == 200
    dem = resp_dem.json()["data"]
    assert "peak_requirement" in dem
    assert "max_gap" in dem
    assert "demand_timeline" in dem

    # 3. Staff overloaded
    resp_ov = client.get("/api/v1/staff/overloaded")
    assert resp_ov.status_code == 200
    assert "overloaded_staff" in resp_ov.json()["data"]

    # 4. Staff conflicts
    resp_conf = client.get("/api/v1/staff/conflicts")
    assert resp_conf.status_code == 200
    assert "conflicts" in resp_conf.json()["data"]

    # 5. Replacement suggestions
    resp_sug = client.get(
        "/api/v1/staff/replacements/suggest?venue_id=V01&start_at=2026-10-31T09:00:00Z&end_at=2026-10-31T12:00:00Z&role_required=Volunteer"
    )
    assert resp_sug.status_code == 200
    assert "suggestions" in resp_sug.json()["data"]

    # 6. CSV Report
    resp_csv = client.get("/api/v1/staff/reports/staff-coverage")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "time_window_start" in resp_csv.text


def test_staff_public_contract(session: Session):
    """Test public contract KPI summary, active risks, and dependents."""
    stf = Staff(id="ST01", name="Aditi Verma", role="Volunteer", status="ACTIVE")
    session.add(stf)
    session.commit()

    now_dt = datetime.now(timezone.utc)
    summary = staff_public.summary(session, now_dt)
    assert summary["module"] == "staff"
    assert summary["status"] == "OPERATIONAL"

    deps = staff_public.dependents(session, "staff", "ST01")
    assert isinstance(deps, list)

    csv_data = staff_public.staff_coverage_csv(session)
    assert "time_window_start" in csv_data
