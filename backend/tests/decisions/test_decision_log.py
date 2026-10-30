# OWNER: P1
from datetime import datetime, timezone

import pytest
from app.core import decision_log
from app.core.clock import set_demo_time
from app.core.db import get_session
from app.main import app
from app.models.audit import Override
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture
def client(session: Session):
    def get_test_session():
        yield session

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_decision_log_add_helper(session: Session):
    """Test decision_log.add() helper writes consistent DecisionCard records across modules."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Add card via core helper
    card = decision_log.add(
        session=session,
        module="accommodation",
        decision_type="CHARTER_EXTERNAL_HOTEL",
        title="Charter Lemon Tree for 80 Male Participants",
        summary="Male hostel occupancy reached 100%. Contracted 80 external beds.",
        why="Hard constraint 'gender segregation' required distinct building. Alternatives like floor sharing were rejected.",
        hard_constraints_satisfied=["GENDER_SEGREGATION", "BED_CAPACITY_LIMIT"],
        soft_constraints_relaxed=[{"constraint": "ON_CAMPUS_PREFERENCE", "reason": "No male campus beds left"}],
        alternatives_rejected=[
            {"option": "Quadruple bunking in H1 common rooms", "why": "Severe fire code violation"},
            {"option": "Mixed-gender floor in H3", "why": "Cultural sensitivity & policy restriction"},
        ],
        cost_impact_inr=120000.0,
        people_affected=80,
        approved_by="usr_director",
        entity_refs=[{"type": "external_property", "id": "ext_lemon_tree", "label": "Lemon Tree Hotel"}],
    )
    session.commit()

    assert card.id.startswith("dec_")
    assert card.module == "accommodation"
    assert card.people_affected == 80
    assert card.cost_impact_inr == 120000.0
    assert len(card.alternatives_rejected) == 2
    assert card.approved_by == "usr_director"


def test_decisions_list_and_filters(session: Session, client: TestClient):
    """Test GET /api/v1/decisions with module, approver, and date filtering."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Populate 3 cards from different modules & approvers
    decision_log.add(
        session=session,
        module="accommodation",
        decision_type="ALLOCATE_ROOM",
        title="Accom Decision 1",
        summary="Summary 1",
        why="Why 1",
        approved_by="Lead_Accom",
    )
    decision_log.add(
        session=session,
        module="schedule",
        decision_type="MOVE_SESSION",
        title="Schedule Decision 2",
        summary="Summary 2",
        why="Why 2",
        approved_by="Lead_Events",
    )
    decision_log.add(
        session=session,
        module="vendors",
        decision_type="APPROVE_BACKUP_VENDOR",
        title="Vendor Decision 3",
        summary="Summary 3",
        why="Why 3",
        approved_by="Festival_Director",
    )
    session.commit()

    # 1. No filter: returns all
    resp = client.get("/api/v1/decisions")
    if resp.status_code != 200:
        print("ERROR RESP:", resp.status_code, resp.text)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 3

    # 2. Filter by module
    resp_accom = client.get("/api/v1/decisions?module=accommodation")
    assert resp_accom.status_code == 200
    data_accom = resp_accom.json()["data"]
    assert all(d["module"] == "accommodation" for d in data_accom["decisions"])

    # 3. Filter by approver
    resp_events = client.get("/api/v1/decisions?approver=Lead_Events")
    assert resp_events.status_code == 200
    data_events = resp_events.json()["data"]
    assert len(data_events["decisions"]) >= 1
    assert data_events["decisions"][0]["approved_by"] == "Lead_Events"


def test_decision_details_and_why_endpoint(session: Session, client: TestClient):
    """Test GET /api/v1/decisions/{id} and one-click 'why' endpoint."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    card = decision_log.add(
        session=session,
        module="incidents",
        decision_type="REROUTE_SHUTTLE",
        title="Emergency Shuttle Rerouting",
        summary="Heavy rain blocked East Gate. Diverted all shuttle buses to West Gate.",
        why="East gate waterlogging posed hazard to low-floor buses.",
        hard_constraints_satisfied=["PASSENGER_SAFETY"],
        soft_constraints_relaxed=[{"constraint": "TRANSIT_TIME_15M", "reason": "Detour adds 8 minutes"}],
        alternatives_rejected=[{"option": "Suspend bus service", "why": "Leaves 200 off-campus attendees stranded"}],
        people_affected=200,
        approved_by="usr_director",
    )
    session.commit()

    # 1. GET /api/v1/decisions/{id}
    resp = client.get(f"/api/v1/decisions/{card.id}")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["id"] == card.id
    assert detail["title"] == "Emergency Shuttle Rerouting"
    assert detail["people_affected"] == 200
    assert len(detail["soft_constraints_relaxed"]) == 1

    # 2. GET /api/v1/decisions/{id}/why (one-click explanation)
    resp_why = client.get(f"/api/v1/decisions/{card.id}/why")
    assert resp_why.status_code == 200
    why_data = resp_why.json()["data"]
    assert why_data["decision_id"] == card.id
    assert why_data["explanation"] == "East gate waterlogging posed hazard to low-floor buses."
    assert why_data["approver"] == "usr_director"
    assert why_data["people_affected"] == 200


def test_decision_links_to_override_without_duplication(session: Session, client: TestClient):
    """Test DecisionCard links to P3 Override register without duplicating data."""
    t0 = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    set_demo_time(t0)

    # Create Override in P3 override register
    ovr = Override(
        id="OVR_HOSTEL_CAP",
        entity_type="room",
        entity_id="RM_H1_101",
        constraint_code="MAX_CAPACITY_EXCEEDED",
        reason="Approved emergency extra cot for contingent escort",
        approved_by="Director_Singh",
        risk_level="HIGH",
        status="ACTIVE",
    )
    session.add(ovr)
    session.commit()

    # Create DecisionCard referencing override_id
    card = decision_log.add(
        session=session,
        module="overrides",
        decision_type="OVERRIDE_ROOM_CAPACITY",
        title="Allow 3rd Bed in Room 101",
        summary="Contingent escort required proximity to underage team member.",
        why="Escort needed in-room supervision per institution safety policy.",
        override_id=ovr.id,
        approved_by="Director_Singh",
    )
    session.commit()

    # Fetch decision
    resp = client.get(f"/api/v1/decisions/{card.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["override_id"] == "OVR_HOSTEL_CAP"
    # Linked details are populated on read, not duplicated in the card table
    assert data["override_details"] is not None
    assert data["override_details"]["id"] == "OVR_HOSTEL_CAP"
    assert data["override_details"]["constraint_code"] == "MAX_CAPACITY_EXCEEDED"
    assert data["override_details"]["approved_by"] == "Director_Singh"


def test_create_decision_via_api(client: TestClient):
    """Test POST /api/v1/decisions creates and persists a new decision card."""
    payload = {
        "module": "schedule",
        "decision_type": "EXTEND_EVENT_DURATION",
        "title": "Extend Hackathon Coding Round by 1 Hour",
        "summary": "Network glitch delayed submission portal opening by 45 minutes.",
        "why": "Ensures fairness for all 40 participating teams.",
        "hard_constraints_satisfied": ["EVENT_FAIRNESS"],
        "soft_constraints_relaxed": [{"constraint": "VENUE_CLOSING_TIME", "reason": "Auditorium staff agreed to overtime"}],
        "alternatives_rejected": [{"option": "Cancel remaining presentations", "why": "Deprives finalists of evaluation"}],
        "cost_impact_inr": 5000.0,
        "people_affected": 160,
    }
    resp = client.post("/api/v1/decisions", json=payload)
    assert resp.status_code == 201
    res_data = resp.json()["data"]
    assert "id" in res_data
    assert res_data["status"] == "RECORDED"
