# OWNER: P1
import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core import clock

from sqlmodel import Session, select

from app.engines.equipment_allocation import PureEquipmentAllocator
from app.engines.inventory_ledger import PureInventoryLedger
from app.models.events import EventSession
from app.models.inventory import (
    InventoryItem,
    InventoryMovement,
    Transfer,
)
from app.models.ops import TravelTime
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Returns module KPI summary as of `now`."""
    items = session.exec(select(InventoryItem).where(InventoryItem.kind == "equipment")).all()
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]

    total_on_hand = 0
    total_reserved = 0
    total_in_transit = 0
    total_damaged = 0
    total_under_repair = 0
    total_awaiting_return = 0
    total_available = 0
    low_stock_count = 0

    for it in items:
        item_mvts = [m for m in movements if m.get("item_id") == it.id]
        proj = PureInventoryLedger.calculate_projection(item_mvts, target_item_id=it.id)
        total_on_hand += proj.on_hand
        total_reserved += proj.reserved
        total_in_transit += proj.in_transit
        total_damaged += proj.damaged
        total_under_repair += proj.under_repair
        total_awaiting_return += proj.awaiting_return
        total_available += proj.available
        if proj.available < it.low_stock_threshold:
            low_stock_count += 1

    active_transfers = session.exec(select(Transfer).where(Transfer.status == "IN_TRANSIT")).all()

    return {
        "module": "logistics",
        "status": "OPERATIONAL",
        "equipment_items_count": len(items),
        "total_on_hand": total_on_hand,
        "total_available": total_available,
        "total_reserved": total_reserved,
        "total_in_transit": total_in_transit,
        "total_under_repair": total_under_repair,
        "total_damaged": total_damaged,
        "total_awaiting_return": total_awaiting_return,
        "active_transfers_count": len(active_transfers),
        "low_stock_count": low_stock_count,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Returns active risks evaluated as of `now`."""
    risk_list: List[RiskItem] = []

    # 1. Reconciliation flag: Camera all under repair
    items = session.exec(select(InventoryItem)).all()
    cams = [it for it in items if "camera" in it.name.lower()]
    if cams and not any(c.condition.lower() == "good" for c in cams):
        risk_list.append(
            RiskItem(
                id="risk_log_camera_under_repair",
                module="logistics",
                kind="EQUIPMENT_DEFICIT",
                title="All 31 cameras logged as 'under repair'; Media Coverage requires 3 units",
                severity=3,
                hours_to_impact=4,
                people_affected=150,
                uncertainty=0.4,
                resource_criticality=4,
                entity_refs=[EntityRef(type="inventory_item", id=c.id, label=c.name) for c in cams],
                action={
                    "label": "Expedite Camera Repair or Source Backup",
                    "route": "/logistics",
                    "api": "/api/v1/logistics/items",
                },
                explanation="All camera inventory batches are marked 'under repair'. Immediate bench testing or external rental is required.",
            )
        )

    # 2. Tables needs check
    unverified_tables = [it for it in items if "table" in it.name.lower() and it.condition.lower() == "needs check"]
    if unverified_tables:
        risk_list.append(
            RiskItem(
                id="risk_log_tables_unverified",
                module="logistics",
                kind="CONDITION_UNVERIFIED",
                title=f"{sum(t.quantity for t in unverified_tables)} tables in Sports Complex flagged 'needs check'",
                severity=2,
                hours_to_impact=6,
                people_affected=80,
                uncertainty=0.5,
                resource_criticality=3,
                entity_refs=[EntityRef(type="inventory_item", id=t.id, label=t.name) for t in unverified_tables],
                action={
                    "label": "Verify Table Usability",
                    "route": "/logistics",
                    "api": "/api/v1/logistics/items",
                },
                explanation="Physical condition of furniture at Sports Complex has not been verified prior to morning competition heats.",
            )
        )

    # 3. Active in-transit delayed transfers
    in_transit_transfers = session.exec(select(Transfer).where(Transfer.status == "IN_TRANSIT")).all()
    for trf in in_transit_transfers:
        if trf.eta and trf.eta < now:
            risk_list.append(
                RiskItem(
                    id=f"risk_trf_overdue_{trf.id}",
                    module="logistics",
                    kind="TRANSFER_DELAY",
                    title=f"Transfer {trf.id} overdue (ETA was {trf.eta.isoformat()})",
                    severity=3,
                    hours_to_impact=1,
                    people_affected=30,
                    uncertainty=0.2,
                    resource_criticality=3,
                    entity_refs=[EntityRef(type="transfer", id=trf.id, label=trf.id)],
                    action={
                        "label": "Track Vehicle / Expedite",
                        "route": "/logistics",
                        "api": f"/api/v1/logistics/transfers/{trf.id}/complete",
                    },
                    explanation="Transfer vehicle has not arrived at destination before expected ETA.",
                )
            )

    return risk_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Returns downstream entities affected by entity_type:entity_id."""
    if entity_type == "inventory_item":
        it = session.get(InventoryItem, entity_id)
        if not it:
            return []
        norm_name = it.name.strip().lower()
        sessions = session.exec(select(EventSession)).all()
        dep_sessions = []
        for s in sessions:
            if norm_name in str(s.equipment_required or "").lower():
                dep_sessions.append(
                    EntityRef(type="event_session", id=s.id, label=f"{s.event_name} ({s.round})")
                )
        return dep_sessions
    return []


def inventory_plan_csv(session: Session) -> str:
    """Generates inventory_plan.csv report."""
    items = session.exec(select(InventoryItem)).all()
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "item_id",
        "name",
        "code",
        "kind",
        "category",
        "location",
        "condition",
        "on_hand",
        "reserved",
        "in_transit",
        "under_repair",
        "available",
    ])

    for it in items:
        item_mvts = [m for m in movements if m.get("item_id") == it.id]
        proj = PureInventoryLedger.calculate_projection(item_mvts, target_item_id=it.id)
        writer.writerow([
            it.id,
            it.name,
            it.code,
            it.kind,
            it.category,
            it.location or "Unknown",
            it.condition,
            proj.on_hand,
            proj.reserved,
            proj.in_transit,
            proj.under_repair,
            proj.available,
        ])

    return output.getvalue()


def equipment_gap_csv(session: Session) -> str:
    """Generates equipment_gap.csv report analyzing gaps across event sessions."""
    sessions = session.exec(select(EventSession)).all()
    items = [it.model_dump() for it in session.exec(select(InventoryItem)).all()]
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]
    tt_rows = session.exec(select(TravelTime)).all()
    travel_matrix = {(tt.from_venue_id, tt.to_venue_id): tt.duration_minutes for tt in tt_rows}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "session_id",
        "event_id",
        "event_name",
        "venue_id",
        "equipment_needed",
        "on_site_units",
        "transfer_needed_units",
        "shortage",
        "status",
    ])

    for s in sessions:
        if not s.equipment_required or s.equipment_required.strip().lower() in ("none", ""):
            continue

        req_items = [r.strip() for r in s.equipment_required.split(";") if r.strip()]
        for req in req_items:
            res = PureEquipmentAllocator.find_equipment(
                item_name=req,
                target_venue_id=s.venue_id or "V01",
                start_at=s.start_at or clock.now(),
                end_at=s.end_at or clock.now(),
                items=items,
                movements=movements,
                travel_matrix=travel_matrix,
                quantity_needed=1,
            )
            on_site = sum(u["available_units"] for u in res["available_on_site"])
            transfers = sum(u["available_units"] for u in res["transfer_needed"] if u["feasible"])
            status = "SATISFIED" if res["is_satisfied"] else "SHORTAGE"

            writer.writerow([
                s.id,
                s.event_id,
                s.event_name,
                s.venue_id,
                req,
                on_site,
                transfers,
                res["shortage"],
                status,
            ])

    return output.getvalue()
