# OWNER: P1
"""Tests for equipment allocation, transfer feasibility, and failure analysis."""
from datetime import datetime, timezone

from app.engines.equipment_allocation import (
    LedgerEquipmentAvailabilityAdapter,
    PureEquipmentAllocator,
)


def test_find_equipment_on_site_and_transfers():
    """Verifies that find_equipment identifies on-site units and feasible transfers with travel buffer."""
    session_start = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    session_end = datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc)

    items = [
        # 2 projectors at V01 (on-site)
        {"id": "itm_proj_v01", "name": "projector", "code": "P01", "location_id": "V01", "location": "Auditorium", "condition": "good"},
        # 5 projectors at V02 (needs transfer)
        {"id": "itm_proj_v02", "name": "projector", "code": "P02", "location_id": "V02", "location": "Seminar Hall", "condition": "good"},
    ]

    movements = [
        {"id": "m1", "item_id": "itm_proj_v01", "to_location_id": "V01", "quantity": 2, "movement_type": "RECEIVE"},
        {"id": "m2", "item_id": "itm_proj_v02", "to_location_id": "V02", "quantity": 5, "movement_type": "RECEIVE"},
    ]

    travel_matrix = {
        ("V02", "V01"): 20,  # 20 min travel time
    }

    # Request 4 projectors at V01
    res = PureEquipmentAllocator.find_equipment(
        item_name="projector",
        target_venue_id="V01",
        start_at=session_start,
        end_at=session_end,
        items=items,
        movements=movements,
        travel_matrix=travel_matrix,
        quantity_needed=4,
        transfer_buffer_min=15,
    )

    assert len(res["available_on_site"]) == 1
    assert res["available_on_site"][0]["available_units"] == 2

    assert len(res["transfer_needed"]) == 1
    transfer_info = res["transfer_needed"][0]
    assert transfer_info["available_units"] == 5
    assert transfer_info["travel_time_min"] == 20
    assert transfer_info["transfer_duration_min"] == 15
    assert transfer_info["total_transit_min"] == 35
    assert transfer_info["feasible"] is True

    # 2 on-site + 5 feasible transfer >= 4 needed
    assert res["is_satisfied"] is True
    assert res["shortage"] == 0


def test_camera_case_and_tables_reconciliation_flags():
    """Verifies that the 31 cameras under repair and tables 'needs check' surface as reconciliation flags."""
    items = [
        {"id": "cam_1", "name": "camera", "quantity": 7, "condition": "under repair"},
        {"id": "cam_2", "name": "camera", "quantity": 11, "condition": "under repair"},
        {"id": "cam_3", "name": "camera", "quantity": 8, "condition": "under repair"},
        {"id": "cam_4", "name": "camera", "quantity": 5, "condition": "under repair"},
        {"id": "tbl_1", "name": "table", "quantity": 15, "condition": "needs check"},
        {"id": "tbl_2", "name": "table", "quantity": 27, "condition": "needs check"},
    ]

    flags = PureEquipmentAllocator.get_reconciliation_flags(items)
    codes = [f["code"] for f in flags]
    assert "CAMERA_ALL_UNDER_REPAIR" in codes
    assert "TABLES_NEEDS_CHECK" in codes

    cam_flag = next(f for f in flags if f["code"] == "CAMERA_ALL_UNDER_REPAIR")
    assert cam_flag["available_good"] == 0
    assert cam_flag["total_units"] == 31


def test_equipment_failure_analysis():
    """Verifies that equipment_failure_analysis returns dependent sessions and alternative units."""
    items = [
        {"id": "mic_1", "name": "mic", "condition": "damaged"},
        {"id": "mic_2", "name": "mic", "condition": "good", "location": "Store Room A"},
    ]
    movements = [
        {"id": "m1", "item_id": "mic_1", "quantity": 1, "movement_type": "RECEIVE"},
        {"id": "m2", "item_id": "mic_2", "quantity": 4, "movement_type": "RECEIVE"},
    ]
    sessions = [
        {
            "id": "ses_001",
            "event_id": "EV_VOCAL",
            "event_name": "Solo Vocals",
            "venue_id": "V01",
            "equipment_required": "mic; sound system",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
        }
    ]

    analysis = PureEquipmentAllocator.analyze_equipment_failure(
        item_id="mic_1",
        items=items,
        movements=movements,
        sessions=sessions,
    )

    assert len(analysis["dependent_sessions"]) == 1
    assert analysis["dependent_sessions"][0]["session_id"] == "ses_001"
    assert len(analysis["alternative_units"]) == 1
    assert analysis["alternative_units"][0]["item_id"] == "mic_2"


def test_ledger_equipment_availability_adapter():
    """Verifies the refined EquipmentAvailabilityPort adapter satisfies conflict detector interface."""
    items = [
        {"id": "itm_spk", "name": "speaker", "location_id": "V01", "condition": "good"},
    ]
    movements = [
        {"id": "m1", "item_id": "itm_spk", "to_location_id": "V01", "quantity": 2, "movement_type": "RECEIVE"},
    ]
    adapter = LedgerEquipmentAvailabilityAdapter(items=items, movements=movements)

    # V01 needs speaker
    is_avail = adapter.is_equipment_available(
        equipment_required="speaker",
        venue_id="V01",
        start_at=datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
    )
    assert is_avail is True

    # V01 needs synthesizer (not in inventory)
    is_not_avail = adapter.is_equipment_available(
        equipment_required="synthesizer",
        venue_id="V01",
        start_at=datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
    )
    assert is_not_avail is False
