# OWNER: P2
from io import BytesIO
import pytest
from fastapi.testclient import TestClient

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.db import get_session
from app.main import app
from app.services.assumptions.service import seed_all_assumptions


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        seed_all_assumptions(s)
        s.commit()
    return engine


@pytest.fixture
def client(test_db):
    def get_test_session():
        with Session(test_db) as s:
            yield s

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_assumptions_api_crud(client: TestClient):
    """Test assumptions API: GET list, GET key, PUT key, history, and dependents."""


    # 1. GET list
    resp = client.get("/api/v1/assumptions")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 25

    # 2. GET specific assumption
    resp = client.get("/api/v1/assumptions/cleaning_buffer_minutes")
    assert resp.status_code == 200
    item = resp.json()["data"]
    assert item["key"] == "cleaning_buffer_minutes"

    # 3. PUT update
    update_payload = {
        "value": "150",
        "reason": "Updated by Director during briefing",
    }
    resp = client.put("/api/v1/assumptions/cleaning_buffer_minutes", json=update_payload)
    assert resp.status_code == 200
    res_data = resp.json()["data"]
    assert res_data["status"] == "APPLIED"

    # Verify updated value
    resp_check = client.get("/api/v1/assumptions/cleaning_buffer_minutes")
    assert resp_check.json()["data"]["value"] == "150"

    # 4. GET history
    resp = client.get("/api/v1/assumptions/cleaning_buffer_minutes/history")
    assert resp.status_code == 200
    hist = resp.json()["data"]["history"]
    assert len(hist) >= 1
    assert hist[0]["action"] == "assumptions.update"

    # 5. GET dependents
    resp = client.get("/api/v1/assumptions/cleaning_buffer_minutes/dependents")
    assert resp.status_code == 200
    deps = resp.json()["data"]["dependent_modules"]
    assert "accommodation" in deps


def test_imports_api_upload_and_promote(client: TestClient):
    """Test imports endpoints: upload CSV, list, inspect, issues, and promote."""
    csv_bytes = (
        b"contingent_id,name,declared_strength,contact_phone\n"
        b"C88,API Test College,45,9876543210\n"
    )
    
    # 1. POST /imports (upload)
    files = {"file": ("contingents.csv", BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/api/v1/imports", files=files)
    assert resp.status_code == 200
    res_data = resp.json()["data"]
    batch_id = res_data["batch_id"]
    assert res_data["total_rows"] == 1
    assert res_data["status"] == "STAGED"

    # 2. GET /imports (list)
    resp = client.get("/api/v1/imports")
    assert resp.status_code == 200
    batches = resp.json()["data"]["items"]
    assert any(b["id"] == batch_id for b in batches)

    # 3. GET /imports/{id}
    resp = client.get(f"/api/v1/imports/{batch_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == batch_id

    # 4. GET /imports/{id}/issues
    resp = client.get(f"/api/v1/imports/{batch_id}/issues")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0

    # 5. POST /imports/{id}/promote
    resp = client.post(f"/api/v1/imports/{batch_id}/promote", json={"reason": "Approved by testing"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "APPLIED"


def test_data_quality_endpoint(client: TestClient):
    """Test /api/v1/data-quality endpoint in both JSON and CSV format."""
    # JSON
    resp = client.get("/api/v1/data-quality")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "summary" in data
    assert "unknown_fields" in data
    assert "issues" in data

    # CSV export
    resp_csv = client.get("/api/v1/data-quality?format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "RECONCILIATION SUMMARY" in resp_csv.text


