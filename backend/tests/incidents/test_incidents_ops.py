# OWNER: P2
from datetime import datetime, timezone

import app.models  # noqa: F401
import pytest
from app.core.db import get_session
from app.main import app
from app.models.accommodation import Room, StayAssignment
from app.models.change import ChangeSet
from app.models.decisions import DecisionCard
from app.models.events import Event, EventSession
from app.models.inventory import InventoryItem, MerchClaim
from app.models.ops import Incident, NotificationDraft, Venue
from app.models.participants import Contingent, Participant, Registration
from app.models.vendors import Vendor, VendorAssignment
from app.schemas.common import Actor, Role
from app.services.incidents.public import dependents as incidents_dependents
from app.services.incidents.public import risks as incidents_risks
from app.services.incidents.public import summary as incidents_summary
from app.services.notifications.service import approve_draft, send_draft
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


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
        # Contingents
        c1 = Contingent(id="CONT-01", name="IIT Delhi", code="IITD")
        session.add(c1)

        # Participants
        p1 = Participant(id="P-01", name="Alice", contingent_id="CONT-01", college="IIT Delhi", status="CONFIRMED")
        p2 = Participant(id="P-02", name="Bob", contingent_id="CONT-01", college="IIT Delhi", status="CONFIRMED")
        p_dup = Participant(id="P-DUP", name="Alice Duplicate", contingent_id="CONT-01", college="IIT Delhi", status="CONFIRMED")
        session.add_all([p1, p2, p_dup])

        # Accommodation: Hostel Block H1
        r1 = Room(id="R-H1-01", block="H1", room_number="101", floor=1, capacity=2, status="AVAILABLE")
        r2 = Room(id="R-H1-02", block="H1", room_number="102", floor=1, capacity=2, status="AVAILABLE")
        session.add_all([r1, r2])

        t_start = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
        t_end = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
        s1 = StayAssignment(id="S-H1-01", plan_id="live_plan", bed_key="R-H1-01-bed1", participant_id="P-01", room_id="R-H1-01", start_at=t_start, end_at=t_end, status="ACTIVE")
        s2 = StayAssignment(id="S-H1-02", plan_id="live_plan", bed_key="R-H1-01-bed2", participant_id="P-02", room_id="R-H1-01", start_at=t_start, end_at=t_end, status="ACTIVE")
        s_dup = StayAssignment(id="S-DUP-01", plan_id="live_plan", bed_key="R-H1-02-bed1", participant_id="P-DUP", room_id="R-H1-02", start_at=t_start, end_at=t_end, status="ACTIVE")
        session.add_all([s1, s2, s_dup])

        # Events & Venues
        v_old = Venue(id="VEN-OLD", name="Old Lecture Hall", capacity=200)
        v_new = Venue(id="VEN-NEW", name="New Seminar Complex", capacity=300)
        session.add_all([v_old, v_new])

        e1 = Event(id="EVT-DEBATE", code="DEBATE-01", name="Parliamentary Debate", min_team_size=1, max_team_size=5, venue_id="VEN-OLD")
        session.add(e1)

        sess1 = EventSession(id="SES-DEBATE-01", event_id="EVT-DEBATE", session_code="DEBATE-S1", venue_id="VEN-OLD")
        session.add(sess1)

        reg_dup = Registration(id="REG-DUP", participant_id="P-DUP", event_id="EVT-DEBATE", status="CONFIRMED")
        session.add(reg_dup)

        # Inventory / Equipment
        item1 = InventoryItem(id="EQ-SOUND-01", sku="SKU-SND-01", name="Digital Audio Console", category="EQUIPMENT", total_quantity=1, status="AVAILABLE")
        session.add(item1)

        clm_dup = MerchClaim(id="CLM-DUP", canonical_participant_id="P-DUP", item_id="EQ-SOUND-01", status="ISSUED")
        session.add(clm_dup)

        # Vendors & Assignments
        vnd_main = Vendor(id="VND-MAIN", name="Campus Caterer A", status="ACTIVE")
        vnd_backup = Vendor(id="VND-BACKUP", name="Campus Caterer B", status="ACTIVE")
        session.add_all([vnd_main, vnd_backup])

        va_main = VendorAssignment(id="VA-MAIN-01", vendor_id="VND-MAIN", meal_slot_id="SLOT-DINNER", location_name="Dining Court 1", date="2026-10-31")
        session.add(va_main)

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


AUTH_HEADERS = {
    "X-Actor-Role": Role.FESTIVAL_DIRECTOR.value,
    "X-Actor-Id": "dir_01",
    "X-Actor-Name": "Festival Director",
}


# ---------------------------------------------------------------------------
# Test Disruption Catalog
# ---------------------------------------------------------------------------
def test_disruption_catalog(client: TestClient):
    """Verify GET /api/v1/disruptions/catalog and GET /api/v1/incidents/catalog expose 7 mandatory scenarios."""
    resp1 = client.get("/api/v1/disruptions/catalog", headers=AUTH_HEADERS)
    assert resp1.status_code == 200
    scenarios1 = resp1.json()["data"]["scenarios"]

    sc_types = {s["scenario_type"] for s in scenarios1}
    assert "LATE_CONTINGENT" in sc_types
    assert "DUPLICATE_PARTICIPANT" in sc_types
    assert "HOSTEL_CLOSURE" in sc_types
    assert "EQUIPMENT_FAILURE" in sc_types
    assert "VENUE_CHANGE" in sc_types
    assert "VENDOR_SHUTDOWN" in sc_types
    assert "DUPLICATE_MERCHANDISE_CLAIM" in sc_types

    # Ensure root access /disruptions/catalog works
    resp_root = client.get("/disruptions/catalog", headers=AUTH_HEADERS)
    assert resp_root.status_code == 200


# ---------------------------------------------------------------------------
# Scenario 1: HOSTEL CLOSURE (Full Acceptance Flow)
# ---------------------------------------------------------------------------
def test_scenario_hostel_closure_acceptance_flow(client: TestClient, test_engine):
    """Full Acceptance Flow:
    1. Inject hostel closure from API
    2. Inspect impact tree and blast radius
    3. Compare recovery plans (Plan A vs Plan B)
    4. Approve Plan A
    5. Assert REAL database rows changed (Room.status == 'CLOSED', StayAssignment.notes updated)
    6. Verify DecisionCard, ChangeSet, and NotificationDrafts created
    7. Verify incident pass
    """
    # 1. Inject hostel closure
    inject_payload = {
        "scenario_type": "HOSTEL_CLOSURE",
        "entity_type": "hostel",
        "entity_id": "H1",
        "parameters": {"block": "H1", "reason": "Severe pipe burst flooding 1st floor"},
        "severity": "HIGH",
    }
    resp_inject = client.post("/api/v1/incidents", json=inject_payload, headers=AUTH_HEADERS)
    assert resp_inject.status_code == 201
    inc_data = resp_inject.json()["data"]
    inc_id = inc_data["id"]

    assert inc_data["status"] == "PLAN_PROPOSED"
    assert inc_data["people_affected"] >= 2
    assert len(inc_data["recovery_plans"]) >= 2

    # 2. Inspect impact tree
    resp_impact = client.get(f"/api/v1/incidents/{inc_id}/impact", headers=AUTH_HEADERS)
    assert resp_impact.status_code == 200
    impact_data = resp_impact.json()["data"]
    assert impact_data["impact_tree"]["entity_type"] == "hostel"
    assert impact_data["impact_tree"]["entity_id"] == "H1"
    assert len(impact_data["impact_tree"]["children"]) >= 1

    # 3. Compare two recovery plans
    resp_plans = client.get(f"/api/v1/incidents/{inc_id}/plans", headers=AUTH_HEADERS)
    assert resp_plans.status_code == 200
    plans = resp_plans.json()["data"]
    assert len(plans) >= 2
    plan_a = plans[0]
    plan_b = plans[1]

    assert plan_a["rank"] == 1
    assert plan_a["cost_increase_inr"] <= plan_b["cost_increase_inr"]
    assert len(plan_a["notification_draft_ids"]) == 5  # All 5 audiences drafted

    # 4. Approve Plan A
    approve_payload = {"plan_id": plan_a["plan_id"], "reason": "Minimal campus cost, high cohesion"}
    resp_approve = client.post(f"/api/v1/incidents/{inc_id}/approve", json=approve_payload, headers=AUTH_HEADERS)
    assert resp_approve.status_code == 200
    approved_detail = resp_approve.json()["data"]

    assert approved_detail["status"] == "EXECUTING"
    assert approved_detail["approved_plan_id"] == plan_a["plan_id"]
    assert approved_detail["change_set_id"] is not None
    assert approved_detail["decision_card_id"] is not None

    # 5. Assert REAL database rows changed!
    with Session(test_engine) as session:
        # Check Rooms are closed
        closed_rooms = session.exec(select(Room).where(Room.block == "H1")).all()
        assert len(closed_rooms) == 2
        for r in closed_rooms:
            assert r.status == "CLOSED"
            assert "Closed due to incident" in (r.safety_info or "")

        # Check StayAssignments updated
        stays = session.exec(select(StayAssignment).where(StayAssignment.room_id.in_([r.id for r in closed_rooms]))).all()
        assert len(stays) >= 2
        for s in stays:
            assert "Relocated under incident" in (s.explanation or "")

        # Check ChangeSet in DB
        cs = session.get(ChangeSet, approved_detail["change_set_id"])
        assert cs is not None
        assert cs.status == "APPLIED"

        # Check DecisionCard in DB
        dec = session.get(DecisionCard, approved_detail["decision_card_id"])
        assert dec is not None
        assert dec.module == "incidents"
        assert dec.decision_type == "RECOVERY_PLAN_APPROVAL"
        assert dec.why == "Minimal campus cost, high cohesion"

        # Check NotificationDrafts in DB
        drafts = session.exec(select(NotificationDraft).where(NotificationDraft.related_incident_id == inc_id)).all()
        assert len(drafts) == 5
        audiences = {d.audience for d in drafts}
        assert audiences == {"contingent_leaders", "volunteers", "vendors", "accommodation_coordinators", "event_organisers"}

    # 6. Verify Incident
    resp_verify = client.post(f"/api/v1/incidents/{inc_id}/verify", headers=AUTH_HEADERS)
    assert resp_verify.status_code == 200
    verify_data = resp_verify.json()["data"]
    assert verify_data["verification_passed"] is True
    assert verify_data["status"] == "CLOSED"


# ---------------------------------------------------------------------------
# Scenario 2: LATE CONTINGENT
# ---------------------------------------------------------------------------
def test_scenario_late_contingent(client: TestClient, test_engine):
    """Assert LATE_CONTINGENT updates arrivals, contingent notes and participant statuses."""
    payload = {
        "scenario_type": "LATE_CONTINGENT",
        "entity_type": "contingent",
        "entity_id": "CONT-01",
        "parameters": {"contingent_id": "CONT-01", "delay_hours": 4},
        "severity": "HIGH",
    }
    res = client.post("/api/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]
    plans = res.json()["data"]["recovery_plans"]

    # Approve Plan A
    client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plans[0]["plan_id"], "reason": "Shift window"}, headers=AUTH_HEADERS)

    with Session(test_engine) as session:
        cont = session.get(Contingent, "CONT-01")
        assert cont is not None
        assert "Arrival delayed by 4h" in (cont.preferences or "")
        participants = session.exec(select(Participant).where(Participant.contingent_id == "CONT-01")).all()
        for p in participants:
            assert p.status == "EXPECTED"


# ---------------------------------------------------------------------------
# Scenario 3: DUPLICATE PARTICIPANT
# ---------------------------------------------------------------------------
def test_scenario_duplicate_participant(client: TestClient, test_engine):
    """Assert DUPLICATE_PARTICIPANT repoints registrations, stays, and claims; marks duplicate MERGED."""
    payload = {
        "scenario_type": "DUPLICATE_PARTICIPANT",
        "entity_type": "participant",
        "entity_id": "P-01",
        "parameters": {"primary_participant_id": "P-01", "duplicate_participant_id": "P-DUP"},
        "severity": "MEDIUM",
    }
    res = client.post("/api/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]
    plans = res.json()["data"]["recovery_plans"]

    # Approve Plan A (Merge)
    client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plans[0]["plan_id"], "reason": "Reconciliation merge"}, headers=AUTH_HEADERS)

    with Session(test_engine) as session:
        dup = session.get(Participant, "P-DUP")
        assert dup.status == "MERGED"

        # Check registration repointed to P-01
        reg = session.get(Registration, "REG-DUP")
        assert reg.participant_id == "P-01"

        # Check stay repointed to P-01
        stay = session.get(StayAssignment, "S-DUP-01")
        assert stay.participant_id == "P-01"

        # Check claim repointed to P-01
        claim = session.get(MerchClaim, "CLM-DUP")
        assert claim.participant_id == "P-01"


# ---------------------------------------------------------------------------
# Scenario 4: EQUIPMENT FAILURE
# ---------------------------------------------------------------------------
def test_scenario_equipment_failure(client: TestClient, test_engine):
    """Assert EQUIPMENT_FAILURE marks item DAMAGED/MAINTENANCE in database."""
    payload = {
        "scenario_type": "EQUIPMENT_FAILURE",
        "entity_type": "equipment",
        "entity_id": "EQ-SOUND-01",
        "parameters": {"item_id": "EQ-SOUND-01", "issue": "Console power supply blowout"},
        "severity": "CRITICAL",
    }
    res = client.post("/api/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]
    plans = res.json()["data"]["recovery_plans"]

    client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plans[0]["plan_id"], "reason": "Hot-swap backup unit"}, headers=AUTH_HEADERS)

    with Session(test_engine) as session:
        item = session.get(InventoryItem, "EQ-SOUND-01")
        assert item.status == "MAINTENANCE"


# ---------------------------------------------------------------------------
# Scenario 5: VENUE CHANGE
# ---------------------------------------------------------------------------
def test_scenario_venue_change(client: TestClient, test_engine):
    """Assert VENUE_CHANGE repoints EventSession.venue_id in database."""
    payload = {
        "scenario_type": "VENUE_CHANGE",
        "entity_type": "venue",
        "entity_id": "VEN-OLD",
        "parameters": {"old_venue_id": "VEN-OLD", "new_venue_id": "VEN-NEW", "reason": "Electrical short circuit"},
        "severity": "HIGH",
    }
    res = client.post("/api/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]
    plans = res.json()["data"]["recovery_plans"]

    client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plans[0]["plan_id"], "reason": "Transfer to VEN-NEW"}, headers=AUTH_HEADERS)

    with Session(test_engine) as session:
        sess = session.get(EventSession, "SES-DEBATE-01")
        assert sess.venue_id == "VEN-NEW"


# ---------------------------------------------------------------------------
# Scenario 6: VENDOR SHUTDOWN
# ---------------------------------------------------------------------------
def test_scenario_vendor_shutdown(client: TestClient, test_engine):
    """Assert VENDOR_SHUTDOWN marks vendor SHUT_DOWN and repoints assignments in database."""
    payload = {
        "scenario_type": "VENDOR_SHUTDOWN",
        "entity_type": "vendor",
        "entity_id": "VND-MAIN",
        "parameters": {"vendor_id": "VND-MAIN", "replacement_vendor_id": "VND-BACKUP", "reason": "Food safety audit failure"},
        "severity": "CRITICAL",
    }
    res = client.post("/api/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]
    plans = res.json()["data"]["recovery_plans"]

    client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plans[0]["plan_id"], "reason": "Switch to backup vendor"}, headers=AUTH_HEADERS)

    with Session(test_engine) as session:
        vnd = session.get(Vendor, "VND-MAIN")
        assert vnd.status == "SHUT_DOWN"

        va = session.get(VendorAssignment, "VA-MAIN-01")
        assert va.vendor_id == "VND-BACKUP"


# ---------------------------------------------------------------------------
# Scenario 7: DUPLICATE MERCHANDISE CLAIM
# ---------------------------------------------------------------------------
def test_scenario_duplicate_merchandise_claim(client: TestClient, test_engine):
    """Assert DUPLICATE_MERCHANDISE_CLAIM rejects second claim in database."""
    payload = {
        "scenario_type": "DUPLICATE_MERCHANDISE_CLAIM",
        "entity_type": "merch_claim",
        "entity_id": "CLM-DUP",
        "parameters": {"claim_id": "CLM-DUP", "participant_id": "P-DUP"},
        "severity": "LOW",
    }
    res = client.post("/api/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]
    plans = res.json()["data"]["recovery_plans"]

    client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plans[0]["plan_id"], "reason": "Enforce single kit policy"}, headers=AUTH_HEADERS)

    with Session(test_engine) as session:
        clm = session.get(MerchClaim, "CLM-DUP")
        assert clm.status == "REJECTED"


# ---------------------------------------------------------------------------
# Concurrent Disruption Conflict Detection
# ---------------------------------------------------------------------------
def test_concurrent_disruption_conflict_detected(client: TestClient):
    """Assert second disruption arriving mid-resolution on overlapping entity warns of conflict."""
    # Inject first incident on hostel H1
    client.post(
        "/api/v1/incidents",
        json={"scenario_type": "HOSTEL_CLOSURE", "entity_type": "hostel", "entity_id": "H1", "parameters": {"block": "H1"}},
        headers=AUTH_HEADERS,
    )

    # Inject second disruption on same entity H1 before first is resolved
    res2 = client.post(
        "/api/v1/incidents",
        json={"scenario_type": "HOSTEL_CLOSURE", "entity_type": "hostel", "entity_id": "H1", "parameters": {"block": "H1"}},
        headers=AUTH_HEADERS,
    )
    assert res2.status_code == 201
    data2 = res2.json()["data"]
    conflicts = data2["concurrent_conflicts"]
    assert len(conflicts) >= 1
    assert "CONCURRENT_DISRUPTION_CONFLICT" in conflicts[0]["warning"]
    assert conflicts[0]["conflict_type"] == "IDENTICAL_ENTITY"


# ---------------------------------------------------------------------------
# Replay Idempotency & Rejected Plans
# ---------------------------------------------------------------------------
def test_replay_approved_plan_is_idempotent(client: TestClient):
    """Assert replay of an approved incident is idempotent and does not fail or duplicate state."""
    res = client.post(
        "/api/v1/incidents",
        json={"scenario_type": "EQUIPMENT_FAILURE", "entity_type": "equipment", "entity_id": "EQ-SOUND-01", "parameters": {"item_id": "EQ-SOUND-01"}},
        headers=AUTH_HEADERS,
    )
    inc_id = res.json()["data"]["id"]
    plan_id = res.json()["data"]["recovery_plans"][0]["plan_id"]

    # First approval
    resp1 = client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plan_id, "reason": "Approve once"}, headers=AUTH_HEADERS)
    assert resp1.status_code == 200

    # Second approval replay
    resp2 = client.post(f"/api/v1/incidents/{inc_id}/approve", json={"plan_id": plan_id, "reason": "Replay approval"}, headers=AUTH_HEADERS)
    assert resp2.status_code == 200
    assert resp2.json()["data"]["approved_plan_id"] == plan_id


def test_rejected_or_unapproved_plans_change_nothing(client: TestClient, test_engine):
    """Assert injecting an incident without approval leaves live rows unmodified."""
    with Session(test_engine) as session:
        room_before = session.get(Room, "R-H1-01").status

    client.post(
        "/api/v1/incidents",
        json={"scenario_type": "HOSTEL_CLOSURE", "entity_type": "hostel", "entity_id": "H1", "parameters": {"block": "H1"}},
        headers=AUTH_HEADERS,
    )

    with Session(test_engine) as session:
        room_after = session.get(Room, "R-H1-01").status
        assert room_after == room_before == "AVAILABLE"


# ---------------------------------------------------------------------------
# Notification Draft Approval Guard
# ---------------------------------------------------------------------------
def test_notification_draft_send_requires_approval(seeded_db: Session):
    """Verify notification drafts require prior human approval before mock sending."""
    draft = NotificationDraft(
        audience="contingent_leaders",
        channel="SMS",
        recipient="Leaders",
        body="Hostel closed",
        status="PENDING_APPROVAL",
    )
    seeded_db.add(draft)
    seeded_db.commit()

    actor = Actor(id="dir_01", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

    # Attempt send without approval -> should raise exception
    with pytest.raises(Exception) as excinfo:
        send_draft(seeded_db, draft.id, actor)
    assert "cannot be sent without prior approval" in str(excinfo.value)

    # Now approve draft
    approve_draft(seeded_db, draft.id, actor)
    assert draft.status == "APPROVED"

    # Send succeeds
    log_entry = send_draft(seeded_db, draft.id, actor)
    assert log_entry.status == "DELIVERED"
    assert draft.status == "SENT"


# ---------------------------------------------------------------------------
# Incident Report CSV & Public Contracts
# ---------------------------------------------------------------------------
def test_incident_report_csv_endpoint(client: TestClient):
    """Verify GET /api/v1/incidents/report/csv generates valid CSV."""
    resp = client.get("/api/v1/incidents/report/csv", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    csv_text = resp.text
    assert "incident_id,scenario_type,title,severity" in csv_text


def test_incidents_public_contract(seeded_db: Session):
    """Verify public.py summary, risks, dependents for incidents."""
    now_dt = datetime.now(timezone.utc)

    # Add open incident
    inc = Incident(
        title="Active Power Outage",
        severity=4,
        category="LOGISTICS",
        status="PLAN_PROPOSED",
        scenario_type="EQUIPMENT_FAILURE",
        entity_type="equipment",
        entity_id="EQ-SOUND-01",
        people_affected=40,
        plans=[{"plan_id": "p1"}],
    )
    seeded_db.add(inc)
    seeded_db.commit()

    summ = incidents_summary(seeded_db, now_dt)
    assert summ["module"] == "incidents"
    assert summ["stalled_approvals_count"] >= 1

    r = incidents_risks(seeded_db, now_dt)
    risk_kinds = {item.kind for item in r}
    assert "STALLED_APPROVAL" in risk_kinds

    deps = incidents_dependents(seeded_db, "equipment", "EQ-SOUND-01")
    assert len(deps) >= 1
    assert deps[0].id == inc.id
