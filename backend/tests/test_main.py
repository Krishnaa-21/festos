# OWNER: P1
import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "now" in data
    assert "X-Request-ID" in response.headers

def test_meta_endpoint(client: TestClient):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "modules" in data
    assert len(data["modules"]) == 32
    assert "auth_disabled" in data

def test_example_router_and_change_service_integration(client: TestClient):
    payload = {
        "id": "ex_item_999",
        "name": "Team Welcome Kit",
        "role": "LEADER",
        "age": 22,
        "is_high_risk": False,
        "reason": "Test kit allocation"
    }
    response = client.post(
        "/api/v1/_example/items",
        json=payload,
        headers={"Idempotency-Key": "test-idem-999"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert "data" in res_json
    assert res_json["data"]["status"] == "APPLIED"
    assert res_json["data"]["change_set_id"] is not None

def test_validation_error_envelope(client: TestClient):
    # Missing required 'name' field
    response = client.post("/api/v1/_example/items", json={"id": "bad_req"})
    assert response.status_code == 422
    err_json = response.json()
    assert "error" in err_json
    assert err_json["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in err_json["error"]
