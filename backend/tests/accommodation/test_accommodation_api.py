# OWNER: P2
from datetime import datetime, timezone

import pytest
from app.core.clock import now
from app.main import app
from app.models.accommodation import ExternalProperty, Room
from app.models.participants import Participant
from app.schemas.common import Role
from app.seed.accommodation import seed_accommodation_resources
from app.services.accommodation.public import dependents, get_contingent_housing, risks, summary
from app.services.accommodation.service import (
    generate_plans,
)
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture
def test_engine():
    import app.models  # noqa: F401
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, create_engine

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def seeded_session(test_engine):
    """Seed room and external property data for testing."""
    with Session(test_engine) as session:
        seed_accommodation_resources(session)

        # Insert a couple of sample participants for API tests
        p1 = Participant(
            id="P_TEST_01",
            name="Rohan Verma",
            contingent_id="CONT_DELHI",
            college="IIT Delhi",
            gender="MALE",
            age=20,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc),
            departure_at=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
            accommodation_requested="YES",
        )
        p2 = Participant(
            id="P_TEST_02",
            name="Ananya Sharma",
            contingent_id="CONT_DELHI",
            college="IIT Delhi",
            gender="FEMALE",
            age=21,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc),
            departure_at=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
            accommodation_requested="YES",
        )
        p3 = Participant(
            id="P_TEST_UNK",
            name="Alex Unknown",
            contingent_id="CONT_MUMBAI",
            college="IIT Bombay",
            gender="UNKNOWN",
            age=22,
            accessibility_needs="",
            housing_preference="standard",
            arrival_at=datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc),
            departure_at=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
            accommodation_requested="YES",
        )
        session.add(p1)
        session.add(p2)
        session.add(p3)
        session.commit()

    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine, seeded_session):
    from app.core.db import get_session

    def get_test_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()



# ---------------------------------------------------------------------------
# 1. Seeder Tests
# ---------------------------------------------------------------------------

def test_accommodation_seeder(seeded_session: Session):
    """Verify order 30 seeder properly populates on-campus rooms and external properties."""
    rooms = seeded_session.exec(select(Room)).all()
    properties = seeded_session.exec(select(ExternalProperty)).all()

    assert len(rooms) == 200
    assert sum(r.capacity for r in rooms) == 710

    # 10 accessible rooms with 26 beds
    accessible_rooms = [r for r in rooms if r.accessible]
    assert len(accessible_rooms) == 10
    assert sum(r.capacity for r in accessible_rooms) == 26

    # 6 external properties with 740 beds
    assert len(properties) == 6
    assert sum(p.beds for p in properties) == 740


# ---------------------------------------------------------------------------
# 2. Plan Generation & Retrieval API Tests
# ---------------------------------------------------------------------------

def test_generate_and_list_plans_api(client: TestClient):
    """Test POST /api/v1/accommodation/plans/generate and GET /api/v1/accommodation/plans."""
    # Generate candidate plans A, B, C
    headers = {
        "x-actor-role": Role.ACCOMMODATION_LEAD.value,
        "x-actor-id": "usr_accom_mgr",
    }
    resp = client.post(
        "/api/v1/accommodation/plans/generate",
        json={"kinds": ["A", "B", "C"], "params": {"cleaning_buffer_minutes": 180}},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data["plans"]) == 3
    plan_kinds = {p["kind"] for p in data["plans"]}
    assert plan_kinds == {"A", "B", "C"}

    # Candidate plans are NOT live
    for p in data["plans"]:
        assert p["status"] == "CANDIDATE"
        assert p["plan_hash"].startswith("sha256:")
        assert p["on_campus_placed"] >= 2  # P1 (male) and P2 (female) placed

    # List candidate plans
    get_resp = client.get("/api/v1/accommodation/plans", headers=headers)
    assert get_resp.status_code == 200
    list_data = get_resp.json()["data"]
    assert len(list_data["plans"]) == 3


def test_compare_plans_api(client: TestClient):
    """Test GET /api/v1/accommodation/plans/compare."""
    headers = {"x-actor-role": Role.ACCOMMODATION_LEAD.value}
    # Ensure plans generated
    client.post("/api/v1/accommodation/plans/generate", json={"kinds": ["A", "B", "C"]}, headers=headers)

    resp = client.get("/api/v1/accommodation/plans/compare?ids=A,B,C", headers=headers)
    assert resp.status_code == 200
    comp_data = resp.json()["data"]
    assert "comparison" in comp_data
    assert len(comp_data["comparison"]) == 3
    assert "trade_off_analysis" in comp_data


def test_plan_shortages_and_why_not_api(client: TestClient):
    """Test GET /plans/{id}/shortages and GET /why-not/{participant_id}."""
    headers = {"x-actor-role": Role.ACCOMMODATION_LEAD.value}
    client.post("/api/v1/accommodation/plans/generate", json={"kinds": ["A"]}, headers=headers)

    # Shortages endpoint
    resp = client.get("/api/v1/accommodation/shortages", headers=headers)
    assert resp.status_code == 200
    shortages = resp.json()["data"]
    assert shortages["total_unplaced"] >= 1  # P_TEST_UNK is unplaced

    # Why-Not endpoint for P_TEST_UNK
    wn_resp = client.get("/api/v1/accommodation/why-not/P_TEST_UNK", headers=headers)
    assert wn_resp.status_code == 200
    wn_data = wn_resp.json()["data"]
    assert wn_data["participant_id"] == "P_TEST_UNK"
    assert wn_data["blocking_reason_code"] == "GENDER_OR_HOUSING_UNKNOWN"
    assert len(wn_data["counterfactual_runs"]) >= 2
    assert "verification_target" in wn_data


def test_demand_timeline_api(client: TestClient):
    """Test GET /api/v1/accommodation/demand-timeline."""
    headers = {"x-actor-role": Role.ACCOMMODATION_LEAD.value}
    resp = client.get("/api/v1/accommodation/demand-timeline", headers=headers)
    assert resp.status_code == 200
    timeline = resp.json()["data"]
    assert timeline["confirmed_demand_count"] >= 2
    assert "timeline" in timeline


def test_rooms_and_properties_api(client: TestClient):
    """Test GET /api/v1/accommodation/rooms and GET /api/v1/accommodation/properties."""
    headers = {"x-actor-role": Role.ACCOMMODATION_LEAD.value}
    rooms_resp = client.get("/api/v1/accommodation/rooms", headers=headers)
    assert rooms_resp.status_code == 200
    assert rooms_resp.json()["data"]["total_rooms"] == 200

    props_resp = client.get("/api/v1/accommodation/properties", headers=headers)
    assert props_resp.status_code == 200
    assert props_resp.json()["data"]["total_properties"] == 6


def test_download_reports_api(client: TestClient):
    """Test CSV report generation endpoints."""
    headers = {
        "x-actor-role": Role.ACCOMMODATION_LEAD.value,
        "x-actor-id": "usr_accom_mgr",
    }
    client.post("/api/v1/accommodation/plans/generate", json={"kinds": ["A", "B", "C"]}, headers=headers)

    reports = [
        "accommodation_plan_A.csv",
        "shortage_report.csv",
        "accommodation_summary.csv",
        "bed_demand_timeline.csv",
    ]
    for rep in reports:
        resp = client.get(f"/api/v1/accommodation/reports/{rep}", headers=headers)
        assert resp.status_code == 200, f"Failed downloading {rep}"
        assert resp.headers["content-type"].startswith("text/csv")
        assert len(resp.text) > 0


def test_decision_cards_api(client: TestClient):
    """Test GET /api/v1/accommodation/decision-cards/{plan_id}."""
    headers = {"x-actor-role": Role.ACCOMMODATION_LEAD.value}
    client.post("/api/v1/accommodation/plans/generate", json={"kinds": ["A"]}, headers=headers)

    resp = client.get("/api/v1/accommodation/decision-cards/plan_A_cohesion", headers=headers)
    assert resp.status_code == 200
    card = resp.json()["data"]
    assert card["id"] == "dec_plan_A_cohesion"
    assert "Accommodation Allocation" in card["subject"]


# ---------------------------------------------------------------------------
# 3. Public Service Interface Tests
# ---------------------------------------------------------------------------

def test_accommodation_public_functions(seeded_session: Session):
    """Verify summary, risks, dependents, and get_contingent_housing."""
    current_time = now()

    # Summary
    s = summary(seeded_session, current_time)
    assert s["module"] == "accommodation"
    assert s["total_beds"] == 1450

    # Risks
    r = risks(seeded_session, current_time)
    assert isinstance(r, list)
    assert any(risk.kind == "ACCESSIBILITY_DEFICIT" for risk in r)

    # Dependents
    deps = dependents(seeded_session, "room", "rm_b1_01")
    assert len(deps) > 0

    # Generate a plan to test get_contingent_housing
    generate_plans(seeded_session, kinds=["C"])
    ch = get_contingent_housing(seeded_session, "CONT_DELHI")
    assert ch is not None
    assert ch["status"] in ("ASSIGNED", "UNASSIGNED")
