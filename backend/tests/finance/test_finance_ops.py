# OWNER: P2
import pytest
from app.core.db import get_session
from app.main import app
from app.models.accommodation import ExternalProperty
from app.models.vendors import VendorSettlement
from app.schemas.common import Role
from app.seed.vendors import seed_vendors
from app.services.finance.public import dependents, risks, summary
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

        # Seed an external property for accommodation spend calculation
        prop = ExternalProperty(
            id="PROP_HOTEL_TEST",
            name="Hotel Grand Indore",
            category="HOTEL",
            address="Ring Road, Indore",
            contact_name="Mr. Sharma",
            contact_phone="+91-9876543210",
            total_rooms=20,
            rate_per_room_inr=3500.0,
            status="ACTIVE",
        )
        session.add(prop)
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


def test_finance_role_gating(client: TestClient):
    """Requirement: Finance Manager role gates all of it (unauthorized role receives 403 Forbidden)."""
    # 1. Volunteer attempt -> 403 Forbidden
    resp = client.get(
        "/api/v1/finance/summary",
        headers={"X-Actor-Role": Role.VOLUNTEER.value},
    )
    assert resp.status_code == 403

    # 2. Finance Manager attempt -> 200 OK
    resp_fm = client.get(
        "/api/v1/finance/summary",
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp_fm.status_code == 200


def test_finance_summary_budget_unset_and_set_modes(client: TestClient):
    """Requirement: budget utilisation vs external_budget_inr (handles budget-unset mode)."""
    # 1. Budget is initially unset
    resp_init = client.get(
        "/api/v1/finance/summary",
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp_init.status_code == 200
    data_init = resp_init.json()["data"]
    assert data_init["budget_status"] == "BUDGET_UNSET"
    assert data_init["external_budget_ceiling_inr"] is None
    assert data_init["total_spend_committed_inr"] > 0

    # 2. Set external budget ceiling
    resp_set = client.post(
        "/api/v1/finance/budget/set",
        json={"budget_inr": 1500000.0, "reason": "Approved executive sponsor budget"},
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp_set.status_code == 200

    # 3. Verify budget utilisation in budget-set mode
    resp_after = client.get(
        "/api/v1/finance/summary",
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp_after.status_code == 200
    data_after = resp_after.json()["data"]
    assert data_after["budget_status"] == "BUDGET_SET"
    assert data_after["external_budget_ceiling_inr"] == 1500000.0
    assert data_after["budget_utilization_pct"] is not None
    assert data_after["variance_inr"] is not None


def test_accommodation_spending_breakdown(client: TestClient):
    """Verify live external accommodation spending breakdown endpoint."""
    resp = client.get(
        "/api/v1/finance/accommodation-spend",
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert "properties" in data
    assert len(data["properties"]) >= 1
    hotel = next(p for p in data["properties"] if p["property_id"] == "PROP_HOTEL_TEST")
    assert hotel["property_name"] == "Hotel Grand Indore"
    assert hotel["total_cost_inr"] > 0


def test_vendor_settlements_and_record_payment(client: TestClient, seeded_session: Session):
    """Verify settlement payment recording, remaining balance update, and status change."""
    # 1. List settlements
    resp = client.get(
        "/api/v1/finance/vendor-settlements",
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    settlements = data["items"]
    assert len(settlements) > 0

    target = settlements[0]
    settlement_id = target["id"]
    initial_balance = target["balance_due_inr"]
    pay_amount = 50000.0

    # 2. Record payment via ChangeService handler finance.record_payment
    pay_payload = {
        "amount_inr": pay_amount,
        "payment_method": "NEFT",
        "reference_number": "TXN_NEFT_98765432",
        "notes": "Advance tranche 1",
    }
    resp_pay = client.post(
        f"/api/v1/finance/vendor-settlements/{settlement_id}/pay",
        json=pay_payload,
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp_pay.status_code == 200
    pay_data = resp_pay.json()["data"]

    assert pay_data["paid_amount_inr"] == pay_amount
    assert pay_data["remaining_balance_inr"] == initial_balance - pay_amount
    assert pay_data["status"] in ("PARTIALLY_PAID", "PAID")


def test_open_vendor_settlement_dispute(client: TestClient, seeded_session: Session):
    """Verify logging a billing dispute updates settlement status to DISPUTED."""
    settlement = seeded_session.exec(select(VendorSettlement)).first()
    assert settlement is not None

    dispute_payload = {
        "disputed_amount_inr": 25000.0,
        "reason": "Counter tally discrepancy for Oct 31 dinner headcounts",
    }
    resp = client.post(
        f"/api/v1/finance/vendor-settlements/{settlement.id}/dispute",
        json=dispute_payload,
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "DISPUTED"
    assert data["disputed_amount_inr"] == 25000.0


def test_emergency_spending_and_override_report(client: TestClient):
    """Verify emergency spend proposal, Director auto-approval, and budgetoverride report."""
    # 1. Propose emergency spend with Festival Director role (auto-approves)
    spend_payload = {
        "title": "Emergency Backup Generator Fuel",
        "category": "FACILITIES",
        "amount_inr": 45000.0,
        "justification": "Grid power outage at Quadrangle dining counters",
    }
    resp_spend = client.post(
        "/api/v1/finance/emergency-spend",
        json=spend_payload,
        headers={"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value},
    )
    assert resp_spend.status_code == 200
    spend_data = resp_spend.json()["data"]
    assert spend_data["status"] == "APPROVED"
    assert spend_data["amount_inr"] == 45000.0

    # 2. Check overrides report
    resp_rep = client.get(
        "/api/v1/finance/budget-overrides-report",
        headers={"X-Actor-Role": Role.FINANCE_MANAGER.value},
    )
    assert resp_rep.status_code == 200
    report_data = resp_rep.json()["data"]
    assert "overrides" in report_data
    assert len(report_data["overrides"]) >= 1


def test_finance_public_interface(seeded_session: Session):
    """Verify finance.public summary, risks, and dependents."""
    s = summary(seeded_session)
    assert s["module"] == "finance"
    assert s["status"] == "OPERATIONAL"

    r = risks(seeded_session)
    assert isinstance(r, list)

    settlement = seeded_session.exec(select(VendorSettlement)).first()
    assert settlement is not None
    d = dependents(seeded_session, "vendor_settlement", settlement.id)
    assert len(d) > 0
