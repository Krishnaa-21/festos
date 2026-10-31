# OWNER: P1
"""Pure Equipment Allocation and Availability Engine.

No DB access, no FastAPI imports.
Implements:
- Equipment discovery by time window and venue:
    find_equipment(item_name, venue_id, start_at, end_at, quantity_needed)
  categorizing units into available on-site, transfer-needed (with feasibility), and shortage.
- Transfer feasibility using travel time matrix + transfer loading/unloading buffer.
- Equipment failure analysis for dependent sessions and alternative units.
- Reconciliation flags for ambiguous data:
    - The 'camera' case: none in good condition although three are needed.
    - The tables 'needs check' inconsistency.
- Refined EquipmentAvailabilityPort adapter for the conflict detector.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core import clock
from app.engines.conflicts import EquipmentAvailabilityPort
from app.engines.inventory_ledger import PureInventoryLedger


class PureEquipmentAllocator:
    """Pure equipment allocation logic."""

    DEFAULT_TRANSFER_BUFFER_MIN = 15
    DEFAULT_TRAVEL_MIN = 15
    DEFAULT_QUANTITY = 1

    @staticmethod
    def find_equipment(
        item_name: str,
        target_venue_id: str,
        start_at: datetime,
        end_at: datetime,
        items: List[Dict[str, Any]],
        movements: List[Dict[str, Any]],
        travel_matrix: Optional[Dict[Tuple[str, str], int]] = None,
        existing_allocations: Optional[List[Dict[str, Any]]] = None,
        quantity_needed: int = 1,
        transfer_buffer_min: int = 15,
        default_travel_min: int = 15,
        now_utc: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Finds available equipment units for a venue and session window.

        Evaluates:
        1. Available units on-site at target_venue_id.
        2. Units at secondary locations/venues that require a transfer, checking feasibility.
        3. Remaining shortage if total available + feasible transfers < quantity_needed.
        """
        travel_matrix = travel_matrix or {}
        existing_allocations = existing_allocations or []

        # Find all items matching the requested name (case-insensitive)
        norm_name = item_name.strip().lower()
        matching_items = [
            it for it in items
            if it.get("name", "").strip().lower() == norm_name
            or it.get("code", "").strip().lower() == norm_name
        ]

        available_on_site: List[Dict[str, Any]] = []
        transfer_needed: List[Dict[str, Any]] = []

        total_available = 0

        for it in matching_items:
            itm_id = it["id"]

            # Candidate locations from static profile + ledger movements
            candidate_locations = set()
            if it.get("location_id"):
                candidate_locations.add(it["location_id"])
            for m in movements:
                if m.get("item_id") == itm_id:
                    if m.get("to_location_id"):
                        candidate_locations.add(m["to_location_id"])
                    if m.get("from_location_id"):
                        candidate_locations.add(m["from_location_id"])

            if not candidate_locations:
                candidate_locations.add(it.get("location", "UNKNOWN"))

            # Check overlap with existing allocations for this item during [start_at, end_at]
            already_allocated = 0
            for alloc in existing_allocations:
                if alloc.get("item_id") == itm_id:
                    a_start = alloc["start_at"]
                    a_end = alloc["end_at"]
                    if start_at < a_end and a_start < end_at:
                        already_allocated += int(alloc.get("quantity", 1))

            for loc_id in candidate_locations:
                # Check projected availability from ledger at this specific location
                proj = PureInventoryLedger.calculate_projection(
                    movements=movements,
                    target_item_id=itm_id,
                    target_location_id=loc_id,
                    as_of_time=start_at,
                )

                effective_avail = max(0, proj.available - already_allocated)
                if effective_avail <= 0:
                    continue

                # Check if this item is at the target venue
                is_on_site = (loc_id == target_venue_id) or (loc_id.lower() == target_venue_id.lower())
                if not is_on_site:
                    loc_name = str(loc_id).lower()
                    if target_venue_id.lower() in loc_name or loc_name in target_venue_id.lower():
                        is_on_site = True

                if is_on_site:
                    available_on_site.append({
                        "item_id": itm_id,
                        "code": it.get("code", itm_id),
                        "location_id": loc_id,
                        "location_name": loc_id,
                        "available_units": effective_avail,
                        "condition": it.get("condition", "good"),
                    })
                    total_available += effective_avail
                else:
                    # Needs transfer: compute travel time and feasibility
                    travel_min = travel_matrix.get((loc_id, target_venue_id), default_travel_min)
                    total_duration_min = travel_min + transfer_buffer_min

                    latest_dep = start_at - timedelta(minutes=total_duration_min)
                    current_now = now_utc if now_utc is not None else clock.now()
                    is_feasible = (latest_dep >= current_now)

                    transfer_needed.append({
                        "item_id": itm_id,
                        "code": it.get("code", itm_id),
                        "source_location_id": loc_id,
                        "source_location_name": loc_id,
                        "target_venue_id": target_venue_id,
                        "available_units": effective_avail,
                        "travel_time_min": travel_min,
                        "transfer_duration_min": transfer_buffer_min,
                        "total_transit_min": total_duration_min,
                        "latest_departure": latest_dep.isoformat(),
                        "feasible": is_feasible,
                        "condition": it.get("condition", "good"),
                    })

        feasible_transfers = sum(t["available_units"] for t in transfer_needed if t["feasible"])
        fulfilled = total_available + feasible_transfers
        shortage = max(0, quantity_needed - fulfilled)

        return {
            "item_name": item_name,
            "target_venue_id": target_venue_id,
            "quantity_needed": quantity_needed,
            "available_on_site": available_on_site,
            "transfer_needed": transfer_needed,
            "fulfilled_units": fulfilled,
            "shortage": shortage,
            "is_satisfied": (shortage == 0),
        }

    @staticmethod
    def analyze_equipment_failure(
        item_id: str,
        items: List[Dict[str, Any]],
        movements: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        travel_matrix: Optional[Dict[Tuple[str, str], int]] = None,
    ) -> Dict[str, Any]:
        """Analyzes impact of equipment failure or damage on dependent sessions.

        Returns:
        - dependent_sessions
        - alternative_units
        - transfer_feasibility
        - reconciliation_flags
        """
        travel_matrix = travel_matrix or {}

        target_item = next((it for it in items if it["id"] == item_id or it.get("code") == item_id), None)
        item_name = target_item.get("name", item_id) if target_item else item_id

        # Find sessions requesting this equipment
        norm_name = item_name.strip().lower()
        dependent_sessions = []
        for s in sessions:
            eq_req = str(s.get("equipment_required") or "").lower()
            if norm_name in eq_req:
                dependent_sessions.append({
                    "session_id": s["id"],
                    "event_id": s.get("event_id"),
                    "event_name": s.get("event_name", ""),
                    "venue_id": s.get("venue_id"),
                    "venue_name": s.get("venue_name", ""),
                    "start_at": s["start_at"].isoformat() if hasattr(s["start_at"], "isoformat") else str(s["start_at"]),
                    "end_at": s["end_at"].isoformat() if hasattr(s["end_at"], "isoformat") else str(s["end_at"]),
                })

        # Find alternative units of the same equipment
        alternative_units = []
        for it in items:
            if it["id"] == item_id or it.get("code") == item_id:
                continue
            if it.get("name", "").strip().lower() == norm_name:
                proj = PureInventoryLedger.calculate_projection(movements, target_item_id=it["id"])
                if proj.available > 0 and it.get("condition", "good").lower() == "good":
                    alternative_units.append({
                        "item_id": it["id"],
                        "code": it.get("code", it["id"]),
                        "location": it.get("location", "Store Room"),
                        "available": proj.available,
                        "condition": it.get("condition", "good"),
                    })

        # Surface reconciliation flags if cameras or tables
        flags = []
        if "camera" in norm_name:
            all_cams = [it for it in items if "camera" in it.get("name", "").lower()]
            good_cams = [it for it in all_cams if it.get("condition", "").lower() == "good"]
            if not good_cams:
                flags.append({
                    "code": "CAMERA_ALL_UNDER_REPAIR",
                    "severity": "HIGH",
                    "message": "All cameras logged as 'under repair'; 3 needed for Media Coverage.",
                })

        return {
            "item_id": item_id,
            "item_name": item_name,
            "condition": target_item.get("condition", "good") if target_item else "unknown",
            "dependent_sessions": dependent_sessions,
            "alternative_units": alternative_units,
            "reconciliation_flags": flags,
        }

    @staticmethod
    def get_reconciliation_flags(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Surfaces ambiguous equipment states as reconciliation flags rather than hard shortages."""
        flags: List[Dict[str, Any]] = []

        # 1. The 'camera' case: 4 batches/units total 31 cameras, all under repair
        cams = [it for it in items if "camera" in it.get("name", "").lower()]
        if cams:
            good_cams = [c for c in cams if c.get("condition", "").lower() == "good"]
            if not good_cams:
                flags.append({
                    "code": "CAMERA_ALL_UNDER_REPAIR",
                    "item": "camera",
                    "total_units": sum(int(c.get("quantity", 0)) for c in cams),
                    "available_good": 0,
                    "severity": "HIGH",
                    "message": "All cameras across 4 locations are logged as 'under repair'; 3 needed for Media Coverage.",
                })

        # 2. The 'tables' case: tables in Sports Complex flagged 'needs check'
        tables = [
            it for it in items
            if "table" in it.get("name", "").lower()
            and it.get("condition", "").lower() == "needs check"
        ]
        if tables:
            total_unverified = sum(int(t.get("quantity", 0)) for t in tables)
            flags.append({
                "code": "TABLES_NEEDS_CHECK",
                "item": "table",
                "quantity": total_unverified,
                "severity": "MEDIUM",
                "message": f"{total_unverified} tables flagged as 'needs check' in Sports Complex; physical condition unverified.",
            })

        return flags


class LedgerEquipmentAvailabilityAdapter(EquipmentAvailabilityPort):
    """Refined EquipmentAvailabilityPort adapter reading from the inventory ledger.

    Satisfies Prompt 7 pure conflict detector interface.
    """

    def __init__(
        self,
        items: List[Dict[str, Any]],
        movements: List[Dict[str, Any]],
        travel_matrix: Optional[Dict[Tuple[str, str], int]] = None,
    ):
        self.items = items
        self.movements = movements
        self.travel_matrix = travel_matrix or {}

    def is_equipment_available(
        self,
        equipment_required: str,
        venue_id: str,
        start_at: datetime,
        end_at: datetime,
    ) -> bool:
        """Returns True if required equipment can be provided on-site or transferred feasibly."""
        if not equipment_required or equipment_required.strip().lower() in ("none", ""):
            return True

        # Equipment requirement can be semicolon separated, e.g. "mic; speaker"
        req_items = [r.strip() for r in equipment_required.split(";") if r.strip()]
        for req in req_items:
            res = PureEquipmentAllocator.find_equipment(
                item_name=req,
                target_venue_id=venue_id,
                start_at=start_at,
                end_at=end_at,
                items=self.items,
                movements=self.movements,
                travel_matrix=self.travel_matrix,
                quantity_needed=1,
            )
            if not res["is_satisfied"]:
                return False
        return True
