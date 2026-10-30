# OWNER: P1
"""Tests for double-entry inventory ledger math and stock bucket projections.

Verifies:
1. Available stock formula:
   available = on_hand - reserved - damaged - under_repair - awaiting_return
2. In-transit stock counts at neither endpoint.
3. Damaged stock is unavailable.
4. Returned items sit in awaiting_return until inspected.
5. Consistency check proves movements balance across the festival.
"""


from app.engines.inventory_ledger import PureInventoryLedger


def test_stock_bucket_projection_formula():
    """Verifies that available stock is accurately computed from all non-available buckets."""
    movements = [
        # Receive 100 units at loc_store
        {
            "id": "m1",
            "item_id": "itm_mic_01",
            "from_location_id": None,
            "to_location_id": "loc_store",
            "quantity": 100,
            "movement_type": "RECEIVE",
        },
        # Reserve 20 units
        {
            "id": "m2",
            "item_id": "itm_mic_01",
            "from_location_id": "loc_store",
            "to_location_id": "loc_store",
            "quantity": 20,
            "movement_type": "RESERVE",
        },
        # Mark 5 units damaged
        {
            "id": "m3",
            "item_id": "itm_mic_01",
            "from_location_id": "loc_store",
            "to_location_id": None,
            "quantity": 5,
            "movement_type": "DAMAGE",
        },
        # Send 10 units to repair
        {
            "id": "m4",
            "item_id": "itm_mic_01",
            "from_location_id": "loc_store",
            "to_location_id": "loc_repair",
            "quantity": 10,
            "movement_type": "SEND_REPAIR",
        },
        # Return 2 units (awaiting inspection)
        {
            "id": "m5",
            "item_id": "itm_mic_01",
            "from_location_id": None,
            "to_location_id": "loc_store",
            "quantity": 2,
            "movement_type": "RETURN",
        },
    ]

    proj = PureInventoryLedger.calculate_projection(movements, target_item_id="itm_mic_01")
    # on_hand = physical stock at location: 100 received + 2 returned = 102
    # reserved = 20
    # damaged = 5
    # under_repair = 10
    # awaiting_return = 2
    # available = on_hand (102) - reserved (20) - damaged (5) - under_repair (10) - awaiting_return (2) = 65
    assert proj.on_hand == 102
    assert proj.reserved == 20
    assert proj.damaged == 5
    assert proj.under_repair == 10
    assert proj.awaiting_return == 2
    assert proj.available == 65


def test_in_transit_counted_at_neither_endpoint():
    """Verifies that items in transit are not counted in on_hand at either origin or destination."""
    movements = [
        # Store Room A receives 50 mixers
        {
            "id": "m1",
            "item_id": "itm_mix_01",
            "from_location_id": None,
            "to_location_id": "loc_store_a",
            "quantity": 50,
            "movement_type": "RECEIVE",
        },
        # Transfer 20 mixers from Store Room A towards Main Stage (TRANSFER_OUT)
        {
            "id": "m2",
            "reference_id": "trf_001",
            "item_id": "itm_mix_01",
            "from_location_id": "loc_store_a",
            "to_location_id": "loc_main_stage",
            "quantity": 20,
            "movement_type": "TRANSFER_OUT",
        },
    ]

    # Check origin location (Store Room A)
    origin_proj = PureInventoryLedger.calculate_projection(
        movements, target_item_id="itm_mix_01", target_location_id="loc_store_a"
    )
    assert origin_proj.on_hand == 30
    assert origin_proj.available == 30

    # Check destination location (Main Stage) - transfer has NOT arrived yet!
    dest_proj = PureInventoryLedger.calculate_projection(
        movements, target_item_id="itm_mix_01", target_location_id="loc_main_stage"
    )
    assert dest_proj.on_hand == 0
    assert dest_proj.available == 0

    # Check global projection across festival
    global_proj = PureInventoryLedger.calculate_projection(movements, target_item_id="itm_mix_01")
    assert global_proj.on_hand == 30
    assert global_proj.in_transit == 20

    # Now complete transfer (TRANSFER_IN)
    movements.append({
        "id": "m3",
        "reference_id": "trf_001",
        "item_id": "itm_mix_01",
        "from_location_id": "loc_store_a",
        "to_location_id": "loc_main_stage",
        "quantity": 20,
        "movement_type": "TRANSFER_IN",
    })

    # Check destination after arrival
    dest_proj_after = PureInventoryLedger.calculate_projection(
        movements, target_item_id="itm_mix_01", target_location_id="loc_main_stage"
    )
    assert dest_proj_after.on_hand == 20
    assert dest_proj_after.available == 20

    global_proj_after = PureInventoryLedger.calculate_projection(movements, target_item_id="itm_mix_01")
    assert global_proj_after.on_hand == 50
    assert global_proj_after.in_transit == 0


def test_damaged_stock_unavailable():
    """Verifies that stock marked damaged reduces available units."""
    movements = [
        {
            "id": "m1",
            "item_id": "itm_spk_01",
            "to_location_id": "loc_stage",
            "quantity": 10,
            "movement_type": "RECEIVE",
        },
        {
            "id": "m2",
            "item_id": "itm_spk_01",
            "from_location_id": "loc_stage",
            "quantity": 3,
            "movement_type": "DAMAGE",
        },
    ]

    proj = PureInventoryLedger.calculate_projection(movements, target_item_id="itm_spk_01")
    assert proj.damaged == 3
    assert proj.on_hand == 10
    assert proj.available == 7


def test_ledger_balance_consistency_check():
    """Verifies the double-entry consistency check across multiple items and locations."""
    items = [
        {"id": "itm_1", "name": "Item One"},
        {"id": "itm_2", "name": "Item Two"},
    ]
    locations = [
        {"id": "loc_a", "name": "Location A"},
        {"id": "loc_b", "name": "Location B"},
    ]
    movements = [
        {"id": "m1", "item_id": "itm_1", "to_location_id": "loc_a", "quantity": 100, "movement_type": "RECEIVE"},
        {"id": "m2", "item_id": "itm_1", "from_location_id": "loc_a", "to_location_id": "loc_b", "quantity": 30, "movement_type": "TRANSFER_OUT", "reference_id": "t1"},
        {"id": "m3", "item_id": "itm_1", "from_location_id": "loc_a", "to_location_id": "loc_b", "quantity": 30, "movement_type": "TRANSFER_IN", "reference_id": "t1"},
        {"id": "m4", "item_id": "itm_1", "from_location_id": "loc_b", "quantity": 10, "movement_type": "ISSUE"},
        {"id": "m5", "item_id": "itm_2", "to_location_id": "loc_b", "quantity": 50, "movement_type": "RECEIVE"},
    ]

    res = PureInventoryLedger.check_consistency(movements=movements, items=items, locations=locations)
    assert res["consistent"] is True
    assert len(res["discrepancies"]) == 0
    assert res["total_movements"] == 5
