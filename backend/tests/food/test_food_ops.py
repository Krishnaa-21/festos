# OWNER: P2
from datetime import datetime, timezone

import pytest
from app.core.db import get_session
from app.main import app
from app.models.participants import Participant
from app.models.vendors import MealSlot
from app.schemas.common import Role
from app.seed.vendors import seed_vendors
from app.services.food.public import dependents, risks, summary
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

        # Seed sample participants with diverse dietary needs
        sample_participants = [
            Participant(
                id="P_FOOD_VEG_1",
                name="Veg User 1",
                contingent_id="CONT_DELHI",
                college="IIT Delhi",
                gender="MALE",
                age=20,
                diet="Vegetarian",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            ),
            Participant(
                id="P_FOOD_VEG_2",
                name="Veg User 2",
                contingent_id="CONT_DELHI",
                college="IIT Delhi",
                gender="FEMALE",
                age=21,
                diet="Vegetarian",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            ),
            Participant(
                id="P_FOOD_JAIN_1",
                name="Jain User 1",
                contingent_id="CONT_MUMBAI",
                college="IIT Bombay",
                gender="FEMALE",
                age=22,
                diet="Jain",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            ),
            Participant(
                id="P_FOOD_UNK_1",
                name="Unknown User 1",
                contingent_id="CONT_BLR",
                college="IISc",
                gender="UNKNOWN",
                age=22,
                diet="UNKNOWN",
                status="CHECKED_IN",
                arrival_at=datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
            ),
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


def test_food_coverage_matrix_endpoint(client: TestClient):
    """Verify GET /api/v1/food/coverage returns 3D matrix and preserves UNKNOWN as a demand range."""
    resp = client.get(
        "/api/v1/food/coverage?date=2026-10-31",
        headers={"X-Actor-Role": Role.FOOD_OPS_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["date"] == "2026-10-31"
    assert "categories" in data
    assert "vegetarian" in data["categories"]
    assert "jain" in data["categories"]
    assert "unknown" in data["categories"]
    assert len(data["meal_slots"]) > 0

    # Verify summary metrics
    summary = data["summary"]
    assert summary["on_site_headcount"] >= 4
    assert summary["unknown_dietary_headcount"] >= 1

    # Verify matrix structure
    matrix = data["matrix"]
    assert len(matrix) > 0

    # Ensure UNKNOWN is represented as a range (demand_confirmed vs demand_max_with_unknown)
    veg_cells = [cell for cell in matrix if cell["category"] == "vegetarian"]
    assert len(veg_cells) > 0
    for cell in veg_cells:
        assert cell["demand_max_with_unknown"] >= cell["demand_confirmed"]


def test_food_compliance_mismatch_flags_endpoint(client: TestClient):
    """Verify GET /api/v1/food/compliance-flags identifies VND09 and VND11 menu mismatches."""
    resp = client.get(
        "/api/v1/food/compliance-flags",
        headers={"X-Actor-Role": Role.FOOD_OPS_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    flags = data["flags"]
    assert len(flags) > 0

    # VND09: Jain thali on menu without declared Jain
    vnd09_flag = next((f for f in flags if f["vendor_id"] == "VND09"), None)
    assert vnd09_flag is not None
    assert vnd09_flag["requires_human_confirmation"] is True
    assert "Jain" in vnd09_flag["message"]

    # VND11: Vegan bowls on menu with conflicting declared options
    vnd11_flag = next((f for f in flags if f["vendor_id"] == "VND11"), None)
    assert vnd11_flag is not None
    assert vnd11_flag["requires_human_confirmation"] is True
    assert "Vegan" in vnd11_flag["message"]


def test_list_meal_slots_endpoint(client: TestClient):
    """Verify GET /api/v1/food/meal-slots returns all 20 festival slots."""
    resp = client.get(
        "/api/v1/food/meal-slots",
        headers={"X-Actor-Role": Role.FOOD_OPS_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 20  # 4 days * 5 slots
    slot_names = {s["name"] for s in items}
    assert {"BREAKFAST", "LUNCH", "SNACKS", "DINNER", "LATE_NIGHT"}.issubset(slot_names)


def test_food_public_interface(seeded_session: Session):
    """Verify food.public summary, risks, and dependents."""
    s = summary(seeded_session)
    assert s["module"] == "food"
    assert s["status"] == "OPERATIONAL"
    assert s["on_site_headcount"] >= 4

    r = risks(seeded_session)
    assert len(r) > 0
    mismatch_risks = [item for item in r if item.kind == "MENU_LABEL_MISMATCH"]
    assert len(mismatch_risks) >= 2

    # Verify dependents on a meal slot
    slot = seeded_session.exec(select(MealSlot)).first()
    assert slot is not None
    d = dependents(seeded_session, "meal_slot", slot.id)
    assert len(d) > 0
