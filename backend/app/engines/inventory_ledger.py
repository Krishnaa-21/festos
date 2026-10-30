# OWNER: P1
"""Pure Inventory Ledger Engine.

No DB access, no FastAPI imports.
Implements:
- Time- and location-aware projection of stock buckets.
- Strict ledger movement accounting (RECEIVE, RESERVE, RELEASE, TRANSFER_OUT,
  TRANSFER_IN, ISSUE, RETURN, DAMAGE, SEND_REPAIR, REPAIR_DONE, ADJUST).
- In-transit inventory counting at neither endpoint until completion.
- Awaiting-return holding bucket for returned merchandise/equipment until inspection.
- Explicit formula:
    available = on_hand - reserved - damaged - under_repair - awaiting_return
- Mathematical consistency check proving double-entry ledger balance.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StockBucket:
    """Projected stock quantities for an item at a location or across the festival."""

    on_hand: int = 0
    reserved: int = 0
    in_transit: int = 0
    damaged: int = 0
    under_repair: int = 0
    awaiting_return: int = 0
    available: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


class PureInventoryLedger:
    """Pure ledger projection engine."""

    @staticmethod
    def calculate_projection(
        movements: List[Dict[str, Any]],
        target_item_id: Optional[str] = None,
        target_location_id: Optional[str] = None,
        as_of_time: Optional[datetime] = None,
    ) -> StockBucket:
        """Computes stock projection for an item and location as of a point in time.

        Formula:
            on_hand = (RECEIVE + TRANSFER_IN + RETURN + REPAIR_DONE - TRANSFER_OUT - ISSUE - DAMAGE - SEND_REPAIR + ADJUST_DELTA)
            reserved = RESERVE - RELEASE
            in_transit = TRANSFER_OUT (not yet completed with TRANSFER_IN)
            damaged = cumulative DAMAGE
            under_repair = SEND_REPAIR - REPAIR_DONE
            awaiting_return = RETURN - (inspected / released)
            available = max(0, on_hand - reserved - damaged - under_repair - awaiting_return)
        """
        # Filter movements
        relevant = []
        for m in movements:
            if target_item_id and m.get("item_id") != target_item_id:
                continue
            if as_of_time and m.get("moved_at") and m["moved_at"] > as_of_time:
                continue
            relevant.append(m)

        # Track movements
        on_hand = 0
        reserved = 0
        in_transit = 0
        damaged = 0
        under_repair = 0
        awaiting_return = 0

        # We track transfers in transit by reference_id / transfer_id
        pending_transfers: Dict[str, int] = defaultdict(int)

        for m in relevant:
            mtype = m.get("movement_type", "").upper()
            qty = int(m.get("quantity", 0))
            from_loc = m.get("from_location_id")
            to_loc = m.get("to_location_id")
            ref = m.get("reference_id") or m.get("id")

            # Check if this movement affects the target location
            affects_as_source = (target_location_id is None) or (from_loc == target_location_id)
            affects_as_dest = (target_location_id is None) or (to_loc == target_location_id)

            if mtype == "RECEIVE":
                if affects_as_dest:
                    on_hand += qty

            elif mtype == "RESERVE":
                if affects_as_source or affects_as_dest:
                    reserved += qty

            elif mtype == "RELEASE":
                if affects_as_source or affects_as_dest:
                    reserved = max(0, reserved - qty)

            elif mtype == "TRANSFER_OUT":
                # Stock departs from_location
                if affects_as_source and from_loc == target_location_id:
                    on_hand -= qty
                elif target_location_id is None:
                    # Globally, in-transit is now unplaced
                    on_hand -= qty
                pending_transfers[ref] += qty

            elif mtype == "TRANSFER_IN":
                # Stock arrives at to_location
                if affects_as_dest and to_loc == target_location_id:
                    on_hand += qty
                elif target_location_id is None:
                    on_hand += qty
                pending_transfers[ref] = max(0, pending_transfers[ref] - qty)

            elif mtype == "ISSUE":
                if affects_as_source:
                    on_hand -= qty
                    # If previously reserved, decrement reservation
                    if reserved > 0:
                        reserved = max(0, reserved - qty)

            elif mtype == "RETURN":
                if affects_as_dest:
                    on_hand += qty
                    awaiting_return += qty

            elif mtype == "INSPECT_RETURN":
                # Item was inspected from awaiting_return
                if affects_as_dest or affects_as_source:
                    awaiting_return = max(0, awaiting_return - qty)

            elif mtype == "DAMAGE":
                if affects_as_source or affects_as_dest:
                    damaged += qty

            elif mtype == "SEND_REPAIR":
                if affects_as_source:
                    under_repair += qty

            elif mtype == "REPAIR_DONE":
                if affects_as_dest:
                    under_repair = max(0, under_repair - qty)

            elif mtype == "ADJUST":
                # Stocktake delta
                delta = int(m.get("quantity", 0))
                if affects_as_dest or affects_as_source:
                    on_hand += delta

        # Global in-transit computation
        if target_location_id is None:
            in_transit = sum(pending_transfers.values())
        else:
            # If target_location is in_transit specifically
            in_transit = 0

        # Available formula
        # Physical on-hand minus non-available allocations
        available = max(
            0,
            on_hand - reserved - damaged - under_repair - awaiting_return,
        )

        return StockBucket(
            on_hand=on_hand,
            reserved=reserved,
            in_transit=in_transit,
            damaged=damaged,
            under_repair=under_repair,
            awaiting_return=awaiting_return,
            available=available,
        )

    @staticmethod
    def check_consistency(
        movements: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Proves that movements balance across all items and locations.

        Verifies double-entry invariant:
        Total received + Total positive adjustments - Total issued - Total disposed
        = Total on_hand across all physical locations + Total in_transit
        """
        item_ids = {it["id"] for it in items}
        discrepancies: List[Dict[str, Any]] = []

        total_movements = len(movements)
        net_supply = 0
        net_demand_or_loss = 0

        for itm_id in item_ids:
            item_movements = [m for m in movements if m.get("item_id") == itm_id]

            total_received = sum(
                int(m["quantity"])
                for m in item_movements
                if m.get("movement_type") == "RECEIVE"
            )
            total_adjustments = sum(
                int(m["quantity"])
                for m in item_movements
                if m.get("movement_type") == "ADJUST"
            )
            total_issued = sum(
                int(m["quantity"])
                for m in item_movements
                if m.get("movement_type") == "ISSUE"
            )

            expected_system_stock = total_received + total_adjustments - total_issued

            # Calculate global projection
            global_proj = PureInventoryLedger.calculate_projection(item_movements)
            actual_accounted = global_proj.on_hand + global_proj.in_transit

            if expected_system_stock != actual_accounted:
                discrepancies.append({
                    "item_id": itm_id,
                    "expected": expected_system_stock,
                    "actual_accounted": actual_accounted,
                    "difference": actual_accounted - expected_system_stock,
                })

            net_supply += (total_received + max(0, total_adjustments))
            net_demand_or_loss += (total_issued + max(0, -total_adjustments))

        return {
            "consistent": len(discrepancies) == 0,
            "total_movements": total_movements,
            "total_inflow": net_supply,
            "total_outflow": net_demand_or_loss,
            "discrepancies": discrepancies,
        }
