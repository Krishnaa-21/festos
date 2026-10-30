# OWNER: P1
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, col, func, select

from app.engines.equipment_allocation import PureEquipmentAllocator
from app.engines.inventory_ledger import PureInventoryLedger
from app.models.events import EventSession
from app.models.inventory import (
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
    Transfer,
)
from app.models.ops import TravelTime

logger = logging.getLogger("festos.logistics.service")


def list_items(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    kind: Optional[str] = None,
    q: Optional[str] = None,
    location_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists inventory items with computed ledger stock buckets."""
    query = select(InventoryItem)
    if kind and kind != "all":
        query = query.where(InventoryItem.kind == kind)
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    if q:
        search = f"%{q.strip().lower()}%"
        query = query.where(
            func.lower(InventoryItem.name).like(search) | func.lower(InventoryItem.code).like(search)
        )

    all_items = session.exec(query).all()
    total = len(all_items)

    start = (page - 1) * page_size
    items_slice = all_items[start : start + page_size]

    # Batch calculate stock projections
    result_items = []
    for it in items_slice:
        movements = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == it.id)).all()]
        proj = PureInventoryLedger.calculate_projection(movements, target_item_id=it.id)

        loc_name = it.location
        if not loc_name and it.location_id:
            loc = session.get(InventoryLocation, it.location_id)
            loc_name = loc.name if loc else it.location_id

        result_items.append({
            "id": it.id,
            "name": it.name,
            "code": it.code,
            "kind": it.kind,
            "category": it.category,
            "size": it.size,
            "condition": it.condition,
            "location_id": it.location_id,
            "location_name": loc_name,
            "on_hand": proj.on_hand,
            "reserved": proj.reserved,
            "in_transit": proj.in_transit,
            "damaged": proj.damaged,
            "under_repair": proj.under_repair,
            "awaiting_return": proj.awaiting_return,
            "available": proj.available,
            "low_stock_threshold": it.low_stock_threshold,
            "low_stock_alert": (proj.available < it.low_stock_threshold),
            "status": it.status,
        })

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_item(session: Session, item_id: str) -> Optional[Dict[str, Any]]:
    """Gets item profile with movement projection and location breakdown."""
    it = session.get(InventoryItem, item_id)
    if not it:
        return None

    movements = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == it.id)).all()]
    proj = PureInventoryLedger.calculate_projection(movements, target_item_id=it.id)

    # Location breakdown
    locations = session.exec(select(InventoryLocation)).all()
    loc_breakdown = []
    for loc in locations:
        loc_proj = PureInventoryLedger.calculate_projection(movements, target_item_id=it.id, target_location_id=loc.id)
        if loc_proj.on_hand > 0 or loc_proj.available > 0:
            loc_breakdown.append({
                "location_id": loc.id,
                "location_name": loc.name,
                "building": loc.building,
                "on_hand": loc_proj.on_hand,
                "available": loc_proj.available,
            })

    return {
        "id": it.id,
        "name": it.name,
        "code": it.code,
        "kind": it.kind,
        "category": it.category,
        "size": it.size,
        "condition": it.condition,
        "location_id": it.location_id,
        "location_name": it.location,
        "projection": proj.to_dict(),
        "locations": loc_breakdown,
        "status": it.status,
    }


def list_locations(session: Session) -> List[Dict[str, Any]]:
    locs = session.exec(select(InventoryLocation)).all()
    return [loc.model_dump() for loc in locs]


def list_movements(
    session: Session,
    item_id: Optional[str] = None,
    location_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    query = select(InventoryMovement)
    if item_id:
        query = query.where(InventoryMovement.item_id == item_id)
    if location_id:
        query = query.where(
            (InventoryMovement.from_location_id == location_id)
            | (InventoryMovement.to_location_id == location_id)
        )
    query = query.order_by(col(InventoryMovement.moved_at).desc())

    all_mvts = session.exec(query).all()
    total = len(all_mvts)
    start = (page - 1) * page_size
    slice_mvts = all_mvts[start : start + page_size]

    return {
        "items": [
            {
                "id": m.id,
                "item_id": m.item_id,
                "from_location_id": m.from_location_id,
                "to_location_id": m.to_location_id,
                "quantity": m.quantity,
                "movement_type": m.movement_type,
                "reason": m.reason,
                "reference_id": m.reference_id,
                "moved_by": m.moved_by,
                "moved_at": m.moved_at.isoformat() if m.moved_at else None,
            }
            for m in slice_mvts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_transfers(session: Session) -> List[Dict[str, Any]]:
    trfs = session.exec(select(Transfer).order_by(col(Transfer.initiated_at).desc())).all()
    return [
        {
            "id": t.id,
            "item_id": t.item_id,
            "from_location_id": t.from_location_id,
            "to_location_id": t.to_location_id,
            "quantity": t.quantity,
            "eta": t.eta.isoformat() if t.eta else None,
            "vehicle": t.vehicle,
            "status": t.status,
            "initiated_by": t.initiated_by,
            "initiated_at": t.initiated_at.isoformat() if t.initiated_at else None,
            "completed_by": t.completed_by,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in trfs
    ]


def find_equipment(
    session: Session,
    item_name: str,
    venue_id: str,
    start_at: datetime,
    end_at: datetime,
    quantity_needed: int = 1,
) -> Dict[str, Any]:
    """Finds equipment availability and computes transfer feasibility."""
    items = [it.model_dump() for it in session.exec(select(InventoryItem)).all()]
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]

    # Load travel times
    tt_rows = session.exec(select(TravelTime)).all()
    travel_matrix = {
        (tt.from_venue_id, tt.to_venue_id): (getattr(tt, "travel_time_min", None) or getattr(tt, "duration_minutes", 15))
        for tt in tt_rows
    }

    return PureEquipmentAllocator.find_equipment(
        item_name=item_name,
        target_venue_id=venue_id,
        start_at=start_at,
        end_at=end_at,
        items=items,
        movements=movements,
        travel_matrix=travel_matrix,
        quantity_needed=quantity_needed,
    )


def analyze_failure(session: Session, item_id: str) -> Dict[str, Any]:
    """Analyzes dependent sessions and alternatives for equipment failure."""
    items = [it.model_dump() for it in session.exec(select(InventoryItem)).all()]
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]
    sessions = [s.model_dump() for s in session.exec(select(EventSession)).all()]

    tt_rows = session.exec(select(TravelTime)).all()
    travel_matrix = {
        (tt.from_venue_id, tt.to_venue_id): (getattr(tt, "travel_time_min", None) or getattr(tt, "duration_minutes", 15))
        for tt in tt_rows
    }

    return PureEquipmentAllocator.analyze_equipment_failure(
        item_id=item_id,
        items=items,
        movements=movements,
        sessions=sessions,
        travel_matrix=travel_matrix,
    )


def verify_balance(session: Session) -> Dict[str, Any]:
    """Runs pure double-entry ledger consistency check across all items and locations."""
    items = [it.model_dump() for it in session.exec(select(InventoryItem)).all()]
    locations = [loc.model_dump() for loc in session.exec(select(InventoryLocation)).all()]
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]

    return PureInventoryLedger.check_consistency(movements=movements, items=items, locations=locations)


def get_reconciliation_flags(session: Session) -> List[Dict[str, Any]]:
    """Surfaces the camera and tables reconciliation flags."""
    items = [it.model_dump() for it in session.exec(select(InventoryItem)).all()]
    return PureEquipmentAllocator.get_reconciliation_flags(items)
