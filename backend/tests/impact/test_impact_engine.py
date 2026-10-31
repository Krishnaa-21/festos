from datetime import datetime, timezone

import app.models  # noqa: F401
import pytest
from app.core.change_service import ChangeRequest
from app.core.db import get_session
from app.engines.impact.graph import (
    build_impact_graph,
)
from app.main import app
from app.models.accommodation import Room, StayAssignment
from app.models.events import Event, EventSession
from app.models.inventory import InventoryItem, MerchClaim
from app.models.ops import Venue
from app.models.participants import Contingent, Participant, Registration
from app.models.vendors import Vendor, VendorAssignment
from app.schemas.common import Actor, Role
from app.services.impact.public import dependents as impact_dependents
from app.services.impact.public import risks as impact_risks
from app.services.impact.public import summary as impact_summary
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def seeded_db(test_engine):
    with Session(test_engine) as session:
        # 1. Contingents & Participants
        c1 = Contingent(id="CONT-01", name="IIT Delhi", code="IITD")
        session.add(c1)

        p1 = Participant(id="P-01", name="Alice", contingent_id="CONT-01", college="IIT Delhi", status="CONFIRMED")
        p2 = Participant(id="P-02", name="Bob", contingent_id="CONT-01", college="IIT Delhi", status="CONFIRMED")
        session.add_all([p1, p2])

        # 2. Accommodation: Block A, Room 101, Stay Assignments
        r1 = Room(id="R-101", block="A", room_number="101", floor=1, capacity=2, status="AVAILABLE")
        session.add(r1)

        t_start = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
        t_end = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
        s1 = StayAssignment(id="S-01", plan_id="plan_live", bed_key="R-101-bed1", participant_id="P-01", room_id="R-101", start_at=t_start, end_at=t_end, status="ACTIVE")
        s2 = StayAssignment(id="S-02", plan_id="plan_live", bed_key="R-101-bed2", participant_id="P-02", room_id="R-101", start_at=t_start, end_at=t_end, status="ACTIVE")
        session.add_all([s1, s2])

        # 3. Events, Sessions, Venues
        v1 = Venue(id="VEN-MAIN", name="Main Auditorium", capacity=500)
        session.add(v1)

        e1 = Event(id="EVT-DANCE", code="DANCE-01", name="Choreo Night", min_team_size=1, max_team_size=10, venue_id="VEN-MAIN")
        session.add(e1)

        es1 = EventSession(id="SES-01", event_id="EVT-DANCE", session_code="DANCE-S1", venue_id="VEN-MAIN")
        session.add(es1)

        reg1 = Registration(id="REG-01", participant_id="P-01", event_id="EVT-DANCE", status="CONFIRMED")
        session.add(reg1)

        # 4. Inventory, Equipment, Merch Claims
        eq1 = InventoryItem(id="EQ-AMP-01", sku="SKU-AMP", name="Marshall 100W Amp", category="EQUIPMENT", total_quantity=1, status="AVAILABLE")
        session.add(eq1)

        clm1 = MerchClaim(id="CLM-01", canonical_participant_id="P-01", item_id="EQ-AMP-01", status="ISSUED")
        session.add(clm1)

        # 5. Vendors & Meal Assignments
        vnd1 = Vendor(id="VND-CATER-01", name="Annapurna Foods", status="ACTIVE")
        session.add(vnd1)

        va1 = VendorAssignment(id="VA-01", vendor_id="VND-CATER-01", meal_slot_id="SLOT-LUNCH-D1", location_name="Central Mess", date="2026-10-31")
        session.add(va1)

        session.commit()

    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine, seeded_db):
    def get_test_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_impact_engine_hostel_block_blast_radius(seeded_db: Session):
    """Assert impact engine calculates exact blast radius for Block A hostel closure."""
    change_req = ChangeRequest(
        action="accommodation.close_block",
        entity_type="hostel",
        entity_id="A",
        actor=Actor(id="dir_01", name="Festival Director", role=Role.FESTIVAL_DIRECTOR.value),
    )
    report = build_impact_graph(seeded_db, change_req)

    # Expectations:
    # Root: hostel:A
    # Children: Room R-101
    # Grandchildren: Participants P-01 and P-02
    assert report.total_people_affected == 2
    assert report.counts_by_type.get("room") == 1
    assert report.counts_by_type.get("participant") == 2
    assert report.tree is not None
    assert report.tree.entity_type == "hostel"
    assert report.tree.entity_id == "A"
    assert len(report.tree.children) == 1
    room_node = report.tree.children[0]
    assert room_node.entity_id == "R-101"
    assert len(room_node.children) == 2  # P-01, P-02

    # Check downstream tracking status initialized to PENDING
    for node in report.nodes_flat:
        assert node["downstream_status"] == "PENDING"


def test_impact_engine_event_venue_equipment_chain(seeded_db: Session):
    """Test chain: Venue -> EventSession -> Event -> Registration -> Participant."""
    change_req = ChangeRequest(
        action="venue.close",
        entity_type="venue",
        entity_id="VEN-MAIN",
        actor=Actor(id="dir_01", name="Festival Director", role=Role.FESTIVAL_DIRECTOR.value),
    )
    report = build_impact_graph(seeded_db, change_req)
    assert report.total_people_affected >= 1
    assert report.counts_by_type.get("event_session", 0) >= 1


def test_impact_cycle_termination(seeded_db: Session):
    """Assert dependency cycles terminate gracefully without infinite loops or recursion errors."""
    # Test BFS with arbitrary entity and ensure max_depth / cycle guard protects execution
    change_req = ChangeRequest(
        action="test.cycle_guard",
        entity_type="participant",
        entity_id="P-01",
        actor=Actor(id="dir_01", name="Festival Director", role=Role.FESTIVAL_DIRECTOR.value),
    )
    # Traversing P-01 -> Event -> Venue -> Sessions should terminate cleanly
    report = build_impact_graph(seeded_db, change_req, max_depth=5)
    assert report is not None
    assert len(report.nodes_flat) > 0


def test_api_post_impact_analyze(client: TestClient):
    """Test POST /api/v1/impact/analyze previews change without mutations."""
    headers = {"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value, "X-Actor-Id": "dir_01"}
    req_body = {
        "action": "accommodation.close_block",
        "entity_type": "hostel",
        "entity_id": "A",
        "payload": {"reason": "Plumbing breakdown"},
    }
    resp = client.post("/api/v1/impact/analyze", json=req_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["total_people_affected"] == 2
    assert data["counts_by_type"]["room"] == 1
    assert data["counts_by_type"]["participant"] == 2
    assert len(data["nodes_flat"]) >= 3


def test_api_get_impact_graph(client: TestClient):
    """Test GET /api/v1/impact/graph returns directed nodes and edges."""
    headers = {"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value, "X-Actor-Id": "dir_01"}
    resp = client.get("/api/v1/impact/graph?entity=hostel:A&depth=3", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["entity"] == "hostel:A"
    assert len(data["nodes"]) >= 3
    assert len(data["edges"]) >= 2
    assert len(data["direct_dependents"]) >= 1


def test_impact_public_contract(seeded_db: Session):
    """Test public.py summary, risks, dependents for impact module."""
    from datetime import datetime, timezone
    now_dt = datetime.now(timezone.utc)

    summ = impact_summary(seeded_db, now_dt)
    assert summ["module"] == "impact"
    assert summ["status"] == "OPERATIONAL"
    assert summ["cycle_guard_active"] is True

    r = impact_risks(seeded_db, now_dt)
    assert isinstance(r, list)

    deps = impact_dependents(seeded_db, "hostel", "A")
    assert len(deps) >= 1
    assert any(d.id == "R-101" for d in deps)
