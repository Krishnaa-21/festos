# OWNER: P1
"""Acceptance Tests for Feature 5 and 6 (Inventory and Merchandise).

ACCEPTANCE:
1. Scan a QR twice and see the second rejected with the first transaction details.
2. Move a camera between venues and see availability change by time and location.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.core.db import get_engine, init_db
from app.main import app
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.participants import Participant
from app.seed.registry import run_seeders
from sqlmodel import Session
from starlette.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_acceptance_db():
    init_db()
    run_seeders(reset=False)


def test_acceptance_scan_qr_twice_rejected_with_first_transaction():
    """Acceptance Flow 1: Scan a QR twice and see the second rejected with the first transaction."""
    # 1. Fetch QR token for a fresh participant with no claims
    pid = f"p_acc_qr_{uuid.uuid4().hex[:8]}"
    with Session(get_engine()) as session:
        p = Participant(id=pid, name="Acceptance Attendee", status="ARRIVED", tshirt_size="XL")
        session.add(p)
        session.commit()

    qr_res = client.get(f"/api/v1/merchandise/qr/{pid}")
    assert qr_res.status_code == 200
    qr_data = qr_res.json()["data"]
    token = qr_data["token"]
    assert "svg" in qr_data

    headers_desk1 = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_desk_1",
        "Idempotency-Key": f"idemp_acc_scan_1_{uuid.uuid4().hex[:6]}",
    }

    # 2. First scan with auto_issue
    scan_res1 = client.post(
        "/api/v1/merchandise/scan",
        json={
            "token": token,
            "counter_id": "DESK_NORTH_01",
            "auto_issue_items": ["mch_lanyard_na"],
        },
        headers=headers_desk1,
    )
    assert scan_res1.status_code == 200
    scan_data1 = scan_res1.json()["data"]
    assert scan_data1["valid"] is True
    assert len(scan_data1["issued_results"]) == 1
    assert scan_data1["issued_results"][0]["status"] == "APPLIED"

    # 3. Second scan with auto_issue on the same item -> rejected as ALREADY_ISSUED
    headers_desk2 = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_desk_2",
        "Idempotency-Key": f"idemp_acc_scan_2_{uuid.uuid4().hex[:6]}",
    }
    scan_res2 = client.post(
        "/api/v1/merchandise/scan",
        json={
            "token": token,
            "counter_id": "DESK_SOUTH_02",
            "auto_issue_items": ["mch_lanyard_na"],
        },
        headers=headers_desk2,
    )
    assert scan_res2.status_code == 200
    scan_data2 = scan_res2.json()["data"]
    assert len(scan_data2["issued_results"]) == 1
    second_issue_result = scan_data2["issued_results"][0]
    assert second_issue_result["status"] == "REJECTED"
    violation_codes = [v["code"] for v in second_issue_result["violations"]]
    assert "ALREADY_ISSUED" in violation_codes


def test_acceptance_move_camera_between_venues_availability_change():
    """Acceptance Flow 2: Move a camera between venues and see availability change by time and location."""
    unique_suffix = uuid.uuid4().hex[:6]
    cam_id = f"itm_cam_acc_{unique_suffix}"
    cam_name = f"camera_pro_{unique_suffix}"
    cam_code = f"L13-{unique_suffix}"
    with Session(get_engine()) as session:
        # Create a working camera unit at Store Room A
        cam_working = InventoryItem(
            id=cam_id,
            name=cam_name,
            code=cam_code,
            kind="equipment",
            category="video",
            condition="good",
            quantity=2,
            available_quantity=2,
            location="Store Room A",
            location_id="loc_store_a",
        )
        session.add(cam_working)
        mvt = InventoryMovement(
            item_id=cam_working.id,
            to_location_id="loc_store_a",
            quantity=2,
            movement_type="RECEIVE",
        )
        session.add(mvt)
        session.commit()

    start_window = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    end_window = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()

    # Step A: Query camera availability at Main Stage (loc_main_stage)
    # The camera is at Store Room A, so it requires transfer
    find_before = client.get(
        f"/api/v1/logistics/equipment/find?item_name={cam_name}&venue_id=loc_main_stage&start_at={start_window}&end_at={end_window}&quantity_needed=2"
    )
    assert find_before.status_code == 200
    data_before = find_before.json()["data"]
    assert len(data_before["available_on_site"]) == 0
    assert len(data_before["transfer_needed"]) > 0

    # Step B: Transfer camera to Main Stage
    headers = {
        "X-Actor-Role": "LOGISTICS_MANAGER",
        "X-Actor-Id": "usr_logistics_lead",
        "Idempotency-Key": f"idemp_move_cam_01_{unique_suffix}",
    }
    trf_res = client.post(
        "/api/v1/logistics/transfers",
        json={
            "payload": {
                "item_id": cam_id,
                "from_location_id": "loc_store_a",
                "to_location_id": "loc_main_stage",
                "quantity": 2,
                "eta": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
                "reason": "Transfer camera to Main Stage for evening band",
            }
        },
        headers=headers,
    )
    assert trf_res.status_code == 200
    trf_data = trf_res.json()["data"]["data"]
    transfer_id = trf_data["transfer_id"]

    # In transit: neither Store Room A nor Main Stage has it on-hand
    complete_res = client.post(
        f"/api/v1/logistics/transfers/{transfer_id}/complete",
        headers=headers,
    )
    assert complete_res.status_code == 200

    # Step C: Query camera availability at Main Stage again
    # Now it is available ON-SITE at Main Stage!
    find_after = client.get(
        f"/api/v1/logistics/equipment/find?item_name={cam_name}&venue_id=loc_main_stage&start_at={start_window}&end_at={end_window}&quantity_needed=2"
    )
    assert find_after.status_code == 200
    data_after = find_after.json()["data"]
    assert len(data_after["available_on_site"]) > 0
    assert data_after["available_on_site"][0]["available_units"] >= 2
    assert data_after["is_satisfied"] is True
