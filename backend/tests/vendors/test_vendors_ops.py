# OWNER: P2
from datetime import date, datetime, timezone

import pytest
from app.core.db import get_session
from app.engines.vendors.compliance import (
    get_certificate_validity_status,
    hours_cover_slot,
    is_certificate_valid_at,
    parse_operating_hours,
    verify_menu_labels,
)
from app.engines.vendors.coverage import (
    evaluate_dietary_matrix,
)
from app.engines.vendors.shutdown import vendor_shutdown_analysis
from app.main import app
from app.models.ops import NotificationDraft
from app.models.participants import Participant
from app.models.vendors import MealSlot, Vendor, VendorAssignment
from app.schemas.common import Role
from app.seed.vendors import seed_vendors
from app.services.vendors.public import (
    dependents,
    generate_vendor_compliance_csv,
    generate_vendor_coverage_csv,
    risks,
    summary,
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
    with Session(test_engine) as session:
        seed_vendors(session)

        # Seed sample participants for dietary coverage tests
        # Vegetarian (3), Jain (2), Unknown (2)
        sample_participants = [
            Participant(
                id=f"P_VEG_{i}",
                name=f"Veg User {i}",
                contingent_id="CONT_DELHI",
                college="IIT Delhi",
                gender="MALE",
                age=20,
                diet="Vegetarian",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            )
            for i in range(1, 4)
        ] + [
            Participant(
                id=f"P_JAIN_{i}",
                name=f"Jain User {i}",
                contingent_id="CONT_MUMBAI",
                college="IIT Bombay",
                gender="FEMALE",
                age=21,
                diet="Jain",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            )
            for i in range(1, 3)
        ] + [
            Participant(
                id=f"P_UNK_{i}",
                name=f"Unknown User {i}",
                contingent_id="CONT_BLR",
                college="IISc",
                gender="UNKNOWN",
                age=22,
                diet="UNKNOWN",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            )
            for i in range(1, 3)
        ]
        session.add_all(sample_participants)
        session.commit()

    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine, seeded_session):
    def get_test_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# 1. Compliance Engine Unit Tests
# ===========================================================================

def test_certificate_validity_classification():
    """Verify certificate classification relative to festival dates (Oct 30 - Nov 2, 2026)."""
    # Expired before festival
    assert get_certificate_validity_status(date(2026, 10, 15)) == "EXPIRED"
    assert get_certificate_validity_status(date(2026, 10, 29)) == "EXPIRED"

    # Expires during festival
    assert get_certificate_validity_status(date(2026, 10, 30)) == "EXPIRES_DURING_FESTIVAL"
    assert get_certificate_validity_status(date(2026, 10, 31)) == "EXPIRES_DURING_FESTIVAL"
    assert get_certificate_validity_status(date(2026, 11, 1)) == "EXPIRES_DURING_FESTIVAL"

    # Valid throughout festival
    assert get_certificate_validity_status(date(2026, 11, 2)) == "EXPIRES_DURING_FESTIVAL"
    assert get_certificate_validity_status(date(2026, 11, 3)) == "VALID_THROUGHOUT"
    assert get_certificate_validity_status(date(2026, 12, 31)) == "VALID_THROUGHOUT"
    assert get_certificate_validity_status(None) == "EXPIRED"


def test_certificate_expiry_mid_festival_reduces_capacity_only_after_expiry():
    """Requirement: a vendor's capacity drops out of coverage from expiry moment, NOT whole festival."""
    # Vendor expiring on Oct 31, 2026 (e.g. VND01, VND02)
    exp_oct31 = date(2026, 10, 31)

    # On Oct 30 and Oct 31, certificate is still valid
    assert is_certificate_valid_at(exp_oct31, date(2026, 10, 30)) is True
    assert is_certificate_valid_at(exp_oct31, date(2026, 10, 31)) is True

    # On Nov 1 and Nov 2, certificate has expired and capacity drops out
    assert is_certificate_valid_at(exp_oct31, date(2026, 11, 1)) is False
    assert is_certificate_valid_at(exp_oct31, date(2026, 11, 2)) is False


def test_operating_hours_cover_slot():
    """Verify vendor hours overlap with meal slot start and end times."""
    start_h, end_h = parse_operating_hours("07:00-23:00")
    assert hours_cover_slot("07:00-23:00", "07:30", "10:00") is True
    assert hours_cover_slot("07:00-23:00", "12:30", "15:00") is True

    # Vendor closing at 14:00 cannot cover Dinner (19:30-22:00)
    assert hours_cover_slot("07:00-14:00", "19:30", "22:00") is False


def test_menu_label_verification_flags_mismatches():
    """Requirement: Keyword classifier reports menu mismatches (VND09 Jain thali, VND11 vegan bowls)."""
    # VND09: Jain thali on menu without Jain declared
    vendor_09 = {
        "id": "VND09",
        "name": "QuickBite Express",
        "dietary_options": "vegetarian",
        "menu": "Paneer Roll, Jain Thali, Veg Sandwich, Masala Tea",
    }
    flags_09 = verify_menu_labels(
        vendor_09["id"],
        vendor_09["name"],
        vendor_09["menu"],
        vendor_09["dietary_options"],
    )
    assert len(flags_09) > 0
    jain_flag = next((f for f in flags_09 if f["menu_keyword"] == "Jain thali" or "jain" in f["id"]), None)
    assert jain_flag is not None
    assert jain_flag["requires_human_confirmation"] is True
    assert "Jain" in jain_flag["message"]

    # VND11: Vegan bowls on menu with non-vegetarian / halal declared
    vendor_11 = {
        "id": "VND11",
        "name": "Green Leaf Salads",
        "dietary_options": "non-vegetarian, halal",
        "menu": "Tofu Crunch, Vegan Buddha Bowl, Quinoa Salad",
    }
    flags_11 = verify_menu_labels(
        vendor_11["id"],
        vendor_11["name"],
        vendor_11["menu"],
        vendor_11["dietary_options"],
    )
    assert len(flags_11) > 0
    vegan_flag = next((f for f in flags_11 if f["menu_keyword"] == "Vegan bowls" or "vegan" in f["id"]), None)
    assert vegan_flag is not None
    assert vegan_flag["requires_human_confirmation"] is True


# ===========================================================================
# 2. Coverage Matrix Unit Tests
# ===========================================================================

def test_unknown_diet_stays_demand_range_never_assumed_vegetarian():
    """Requirement: UNKNOWN dietary stays its own group as a demand range, never assumed vegetarian."""
    participants = [
        Participant(
            id="P1",
            name="Veg Person",
            contingent_id="C1",
            college="IIT",
            gender="MALE",
            age=20,
            diet="Vegetarian",
            status="CHECKED_IN",
            arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
            departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
        ),
        Participant(
            id="P2",
            name="Unknown Person 1",
            contingent_id="C1",
            college="IIT",
            gender="FEMALE",
            age=21,
            diet="UNKNOWN",
            status="CHECKED_IN",
            arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
            departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
        ),
        Participant(
            id="P3",
            name="Unknown Person 2",
            contingent_id="C1",
            college="IIT",
            gender="FEMALE",
            age=22,
            diet="UNKNOWN",
            status="CHECKED_IN",
            arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
            departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
        ),
    ]

    vendors = [
        Vendor(
            id="V_TEST",
            name="Test Veg",
            dietary_options="vegetarian",
            capacity=100,
            hours="07:00-23:00",
            hygiene_certificate_expiry="2026-11-05",
            status="ACTIVE",
        )
    ]

    slots = [
        MealSlot(
            id="SLOT_LUNCH",
            name="LUNCH",
            date="2026-10-30",
            start_time="12:30",
            end_time="15:00",
            venue="Main Dining Hall",
            expected_headcount=3,
        )
    ]

    result = evaluate_dietary_matrix(participants, vendors, slots, [], target_date=date(2026, 10, 30))

    # Vegetarian row: demand_confirmed = 1, demand_max_with_unknown = 1 + 2 = 3
    veg_row = next(r for r in result["matrix"] if r["category"] == "vegetarian")
    assert veg_row["demand_confirmed"] == 1
    assert veg_row["demand_max_with_unknown"] == 3
    assert result["summary"]["unknown_dietary_headcount"] == 2


def test_coverage_per_slot_not_just_aggregate(seeded_session: Session):
    """Requirement: compute valid capacity per slot vs demand, gaps per category."""
    vendors = seeded_session.exec(select(Vendor)).all()
    slots = seeded_session.exec(select(MealSlot).where(MealSlot.date == "2026-10-30")).all()
    participants = seeded_session.exec(select(Participant)).all()
    assignments = seeded_session.exec(select(VendorAssignment)).all()

    result = evaluate_dietary_matrix(participants, vendors, slots, assignments, target_date=date(2026, 10, 30))

    assert "matrix" in result
    assert len(result["matrix"]) > 0
    # Make sure every slot on that day has rows for dietary categories
    slots_in_matrix = set(r["meal_slot"] for r in result["matrix"])
    assert "BREAKFAST" in slots_in_matrix
    assert "LUNCH" in slots_in_matrix
    assert "DINNER" in slots_in_matrix


# ===========================================================================
# 3. Shutdown Analysis and Replacement Engine Tests
# ===========================================================================

def test_shutdown_picks_only_compliant_valid_open_spare_capacity(seeded_session: Session):
    """Requirement: shutdown response filters candidates by compliance, validity, hours, and capacity."""
    target_vendor = seeded_session.get(Vendor, "VND03")
    assert target_vendor is not None

    slots = seeded_session.exec(select(MealSlot).where(MealSlot.date == "2026-10-31")).all()
    vendors = seeded_session.exec(select(Vendor)).all()
    assignments = seeded_session.exec(select(VendorAssignment).where(VendorAssignment.vendor_id == "VND03")).all()

    analysis = vendor_shutdown_analysis(
        vendor=target_vendor,
        all_vendors=vendors,
        meal_slots=slots,
        assignments=assignments,
        from_time=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert analysis["vendor_id"] == "VND03"
    assert analysis["lost_capacity"] > 0
    assert len(analysis["replacement_candidates"]) > 0

    # Ensure all ranked candidates have valid certificates and spare capacity
    for cand in analysis["replacement_candidates"]:
        assert cand["compliance_status"] in ("VALID_THROUGHOUT", "EXPIRES_DURING_FESTIVAL")
        assert cand["spare_capacity"] > 0


def test_backup_vendor_that_cannot_absorb_load_is_flagged(seeded_session: Session):
    """Requirement: Backup vendor that cannot absorb the load must be flagged."""
    # Target vendor has capacity 500
    target_vendor = Vendor(
        id="V_BIG",
        name="Massive Food Corp",
        capacity=500,
        hours="07:00-23:00",
        hygiene_certificate_expiry="2026-11-05",
        status="ACTIVE",
        base_rate_per_meal_inr=150.0,
        dietary_options="vegetarian, vegan",
    )
    # Small backup vendor with only 100 capacity
    small_backup = Vendor(
        id="V_SMALL",
        name="Small Backup Stalls",
        capacity=100,
        hours="07:00-23:00",
        hygiene_certificate_expiry="2026-11-05",
        status="ACTIVE",
        base_rate_per_meal_inr=160.0,
        dietary_options="vegetarian, vegan",
    )

    slot = MealSlot(
        id="SLOT_TEST_1",
        name="Dinner",
        date="2026-10-31",
        start_time="19:30",
        end_time="22:00",
        venue="Main Dining Hall",
        expected_headcount=500,
    )

    assignment = VendorAssignment(
        id="ASGN_TEST",
        vendor_id="V_BIG",
        meal_slot_id="SLOT_TEST_1",
        venue="Main Dining Hall",
        allocated_capacity=500,
        status="ACTIVE",
    )

    analysis = vendor_shutdown_analysis(
        vendor=target_vendor,
        all_vendors=[target_vendor, small_backup],
        meal_slots=[slot],
        assignments=[assignment],
        from_time=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
    )

    backup_check = analysis["backup_capacity_check"]
    assert backup_check["can_absorb_load"] is False
    assert backup_check["deficit"] > 0
    assert "cannot absorb" in backup_check["warning"].lower()


# ===========================================================================
# 4. API & Acceptance Tests (Shutdown -> Lost Meals -> Approve -> Updates)
# ===========================================================================

def test_acceptance_vendor_shutdown_and_drafts_generation(client: TestClient, seeded_session: Session):
    """ACCEPTANCE: shut down a vendor, see lost meals by slot and dietary gaps,

    receive ranked replacements with cost delta, approve, and watch capacity and drafts update.
    """
    # 1. Inspect vendor VND03
    resp = client.get("/api/v1/vendors/VND03", headers={"X-Actor-Role": Role.FOOD_OPS_MANAGER.value})
    assert resp.status_code == 200
    vendor_data = resp.json()["data"]
    assert vendor_data["status"] == "ACTIVE"

    # 2. Run Shutdown Analysis
    analysis_payload = {
        "from_time": "2026-10-31T12:00:00Z",
        "reason": "Severe hygiene failure during morning inspection",
    }
    resp_analysis = client.post(
        "/api/v1/vendors/VND03/shutdown-analysis",
        json=analysis_payload,
        headers={"X-Actor-Role": Role.FOOD_OPS_MANAGER.value},
    )
    assert resp_analysis.status_code == 200
    analysis_res = resp_analysis.json()["data"]

    assert analysis_res["vendor_id"] == "VND03"
    assert len(analysis_res["affected_meal_slots"]) > 0
    assert analysis_res["lost_capacity"] > 0
    assert "replacement_candidates" in analysis_res
    assert len(analysis_res["replacement_candidates"]) > 0

    best_replacement = analysis_res["replacement_candidates"][0]
    replacement_id = best_replacement["vendor_id"]
    cost_delta = analysis_res["cost_change_inr"]
    assert isinstance(cost_delta, (int, float))

    # 3. Execute Shutdown through ChangeService handler vendors.shutdown
    exec_payload = {
        "from_time": "2026-10-31T12:00:00Z",
        "replacement_vendor_id": replacement_id,
        "reason": "Immediate emergency shutdown following health inspector notice",
    }
    resp_exec = client.post(
        "/api/v1/vendors/VND03/shutdown-execute",
        json=exec_payload,
        headers={"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value},
    )
    assert resp_exec.status_code == 200
    exec_res = resp_exec.json()["data"]

    assert exec_res["status"] == "APPLIED"
    assert exec_res["new_status"] == "SHUT_DOWN"
    assert exec_res["vendor_id"] == "VND03"
    assert exec_res["change_set_id"] is not None
    assert exec_res["drafts_created"] == 5

    # 4. Verify Vendor is now SHUT_DOWN in DB
    v_db = seeded_session.get(Vendor, "VND03")
    assert v_db.status == "SHUT_DOWN"

    # 5. Verify NotificationDraft rows were created across all 5 audiences
    drafts = seeded_session.exec(select(NotificationDraft)).all()
    audiences = {d.audience for d in drafts}
    expected_audiences = {
        "contingent_leaders",
        "volunteers",
        "vendors",
        "accommodation_coordinators",
        "event_organisers",
    }
    assert expected_audiences.issubset(audiences)


# ===========================================================================
# 5. Public Interface & Export Tests
# ===========================================================================

def test_vendors_public_interface(seeded_session: Session):
    """Verify summary, risks, dependents, and CSV exports in public.py."""
    s = summary(seeded_session)
    assert s["total_vendors"] == 14
    assert s["active_vendors_count"] == 14
    assert s["valid_capacity"] == 1590

    r = risks(seeded_session)
    assert len(r) > 0
    expired_risks = [item for item in r if item.kind == "EXPIRED_HYGIENE_CERTIFICATE"]
    assert len(expired_risks) == 4  # VND05, VND08, VND11, VND13
    expiring_soon = [item for item in r if item.kind == "CERTIFICATE_EXPIRES_MID_FESTIVAL"]
    assert len(expiring_soon) == 4  # VND01, VND02, VND04, VND07

    d = dependents(seeded_session, "VND01")
    assert len(d) > 0
    meal_slot_deps = [dep for dep in d if dep.type == "meal_slot"]
    assert len(meal_slot_deps) > 0
    diet_deps = [dep for dep in d if dep.type == "dietary_category"]
    assert len(diet_deps) > 0

    cov_csv = generate_vendor_coverage_csv(seeded_session)
    assert "Date,Meal Slot,Dietary Category" in cov_csv
    assert "Confirmed Demand" in cov_csv

    comp_csv = generate_vendor_compliance_csv(seeded_session)
    assert "Vendor ID,Vendor Name" in comp_csv
    assert "Validity Status" in comp_csv
