# OWNER: P1
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.engines.inventory_ledger import PureInventoryLedger
from app.models.inventory import (
    InventoryItem,
    InventoryMovement,
    Transfer,
)
from app.schemas.common import Violation

logger = logging.getLogger("festos.logistics.handlers")


@register_change_handler("logistics.record_movement")
class LogisticsRecordMovementHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        item_id = p.get("item_id")
        qty = int(p.get("quantity", 0))
        mtype = p.get("movement_type", "").upper()

        if not item_id:
            return [Violation(code="MISSING_ITEM", severity=4, hard=True, message="item_id is required")]
        item = session.get(InventoryItem, item_id)
        if not item:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Item {item_id} not found")]
        if qty <= 0 and mtype != "ADJUST":
            return [Violation(code="INVALID_QUANTITY", severity=3, hard=True, message="Quantity must be positive")]

        # If reducing stock, check available
        from_loc = p.get("from_location_id")
        if from_loc and mtype in ("TRANSFER_OUT", "ISSUE", "DAMAGE", "SEND_REPAIR"):
            movements = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == item_id)).all()]
            proj = PureInventoryLedger.calculate_projection(movements, target_item_id=item_id, target_location_id=from_loc)
            if proj.on_hand < qty:
                return [Violation(
                    code="INSUFFICIENT_STOCK",
                    severity=4,
                    hard=True,
                    message=f"Insufficient physical stock at location ({proj.on_hand} on-hand vs {qty} requested)",
                )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        item_id = req.payload.get("item_id")
        item = session.get(InventoryItem, item_id) if item_id else None
        return item.model_dump(mode="json") if item else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        item_id = p["item_id"]
        qty = int(p["quantity"])
        mtype = p.get("movement_type", "RECEIVE").upper()

        mvt = InventoryMovement(
            item_id=item_id,
            from_location_id=p.get("from_location_id"),
            to_location_id=p.get("to_location_id"),
            quantity=qty,
            movement_type=mtype,
            reason=req.reason or p.get("reason"),
            reference_id=p.get("reference_id"),
            moved_by=req.actor.id,
            moved_at=now(),
        )
        session.add(mvt)
        session.flush()

        # Update item cached values for convenience
        all_mvts = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == item_id)).all()]
        proj = PureInventoryLedger.calculate_projection(all_mvts, target_item_id=item_id)
        item = session.get(InventoryItem, item_id)
        if item:
            item.quantity = proj.on_hand
            item.reserved_quantity = proj.reserved
            item.available_quantity = proj.available
            item.updated_at = now()
            session.add(item)
            session.flush()

        return {
            "movement_id": mvt.id,
            "item_id": item_id,
            "movement_type": mtype,
            "quantity": qty,
            "projected_buckets": proj.to_dict(),
        }


@register_change_handler("logistics.create_transfer")
class LogisticsCreateTransferHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        item_id = p.get("item_id")
        from_loc = p.get("from_location_id")
        to_loc = p.get("to_location_id")
        qty = int(p.get("quantity", 1))

        if not item_id or not from_loc or not to_loc:
            return [Violation(code="INVALID_PAYLOAD", severity=4, hard=True, message="item_id, from_location_id, and to_location_id are required")]
        if from_loc == to_loc:
            return [Violation(code="SAME_LOCATION", severity=3, hard=True, message="Cannot transfer to the same location")]

        item = session.get(InventoryItem, item_id)
        if not item:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Item {item_id} not found")]

        # Check source available stock
        movements = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == item_id)).all()]
        proj = PureInventoryLedger.calculate_projection(movements, target_item_id=item_id, target_location_id=from_loc)
        if proj.available < qty:
            return [Violation(
                code="INSUFFICIENT_AVAILABLE",
                severity=4,
                hard=True,
                message=f"Insufficient available stock at source location ({proj.available} available vs {qty} requested)",
            )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        item = session.get(InventoryItem, req.payload.get("item_id"))
        return item.model_dump(mode="json") if item else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        trf = Transfer(
            item_id=p["item_id"],
            from_location_id=p["from_location_id"],
            to_location_id=p["to_location_id"],
            quantity=int(p.get("quantity", 1)),
            eta=datetime.fromisoformat(p["eta"]).replace(tzinfo=timezone.utc) if p.get("eta") else None,
            vehicle=p.get("vehicle"),
            status="IN_TRANSIT",
            reason=req.reason or p.get("reason"),
            initiated_by=req.actor.id,
            initiated_at=now(),
        )
        session.add(trf)
        session.flush()

        # Write TRANSFER_OUT movement (departs from_location, counted in neither endpoint)
        mvt = InventoryMovement(
            item_id=trf.item_id,
            from_location_id=trf.from_location_id,
            to_location_id=trf.to_location_id,
            quantity=trf.quantity,
            movement_type="TRANSFER_OUT",
            reason=f"Transfer {trf.id} to {trf.to_location_id}",
            reference_id=trf.id,
            eta=trf.eta,
            status="PENDING",
            moved_by=req.actor.id,
            moved_at=now(),
        )
        session.add(mvt)
        session.flush()

        return {
            "transfer_id": trf.id,
            "status": "IN_TRANSIT",
            "item_id": trf.item_id,
            "from_location_id": trf.from_location_id,
            "to_location_id": trf.to_location_id,
            "quantity": trf.quantity,
            "eta": trf.eta.isoformat() if trf.eta else None,
        }


@register_change_handler("logistics.complete_transfer")
class LogisticsCompleteTransferHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        trf = session.get(Transfer, req.entity_id)
        if not trf:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Transfer {req.entity_id} not found")]
        if trf.status != "IN_TRANSIT":
            return [Violation(code="INVALID_STATUS", severity=3, hard=True, message=f"Transfer is already {trf.status}")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        trf = session.get(Transfer, req.entity_id)
        return trf.model_dump(mode="json") if trf else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        trf = session.get(Transfer, req.entity_id)
        trf.status = "COMPLETED"
        trf.completed_by = req.actor.id
        trf.completed_at = now()
        session.add(trf)

        # Write TRANSFER_IN movement (arrives at to_location)
        mvt = InventoryMovement(
            item_id=trf.item_id,
            from_location_id=trf.from_location_id,
            to_location_id=trf.to_location_id,
            quantity=trf.quantity,
            movement_type="TRANSFER_IN",
            reason=f"Completed arrival of transfer {trf.id}",
            reference_id=trf.id,
            status="COMPLETED",
            moved_by=req.actor.id,
            moved_at=now(),
        )
        session.add(mvt)
        session.flush()

        return {
            "transfer_id": trf.id,
            "status": "COMPLETED",
            "completed_at": trf.completed_at.isoformat(),
            "destination_location_id": trf.to_location_id,
            "quantity": trf.quantity,
        }


@register_change_handler("logistics.stocktake_adjust")
class LogisticsStocktakeAdjustHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        item_id = p.get("item_id")
        reason = req.reason or p.get("reason")
        if not item_id:
            return [Violation(code="MISSING_ITEM", severity=4, hard=True, message="item_id is required")]
        if not reason or not reason.strip():
            return [Violation(code="MANDATORY_REASON", severity=4, hard=True, message="Mandatory justification reason required for stocktake adjustment")]
        item = session.get(InventoryItem, item_id)
        if not item:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Item {item_id} not found")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        item = session.get(InventoryItem, req.payload.get("item_id"))
        return item.model_dump(mode="json") if item else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        item_id = p["item_id"]
        loc_id = p.get("location_id")
        delta = int(p.get("delta", 0))

        mvt = InventoryMovement(
            item_id=item_id,
            from_location_id=loc_id if delta < 0 else None,
            to_location_id=loc_id if delta > 0 else None,
            quantity=delta,
            movement_type="ADJUST",
            reason=req.reason or p.get("reason"),
            moved_by=req.actor.id,
            moved_at=now(),
        )
        session.add(mvt)
        session.flush()

        return {
            "item_id": item_id,
            "delta": delta,
            "reason": mvt.reason,
            "movement_id": mvt.id,
        }
