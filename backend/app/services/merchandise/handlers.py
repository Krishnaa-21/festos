# OWNER: P1
import logging
from typing import Any, Dict, List, Literal

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.engines.inventory_ledger import PureInventoryLedger
from app.models.inventory import (
    InventoryItem,
    InventoryMovement,
    MerchClaim,
)
from app.models.participants import Participant
from app.schemas.common import Violation

logger = logging.getLogger("festos.merchandise.handlers")


@register_change_handler("merchandise.issue")
class MerchandiseIssueHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        part_id = p.get("participant_id")
        item_id = p.get("item_id")

        if not part_id or not item_id:
            return [Violation(code="INVALID_PAYLOAD", severity=4, hard=True, message="participant_id and item_id are required")]

        participant = session.get(Participant, part_id)
        if not participant:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Participant {part_id} not found")]

        # Resolve merged duplicates to canonical record
        canonical_id = participant.canonical_id or participant.id

        item = session.get(InventoryItem, item_id)
        if not item:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Item {item_id} not found")]

        # Check if already issued to this canonical participant
        existing_claim = session.exec(
            select(MerchClaim).where(
                MerchClaim.canonical_participant_id == canonical_id,
                MerchClaim.item_id == item_id,
                MerchClaim.status != "VOIDED",
            )
        ).first()

        if existing_claim:
            claimed_str = existing_claim.claimed_at.isoformat() if existing_claim.claimed_at else "previously"
            return [Violation(
                code="ALREADY_ISSUED",
                severity=4,
                hard=True,
                message=f"Item '{item.name}' already issued to participant at {claimed_str} by {existing_claim.issued_by}",
                entity_refs=[{"type": "merch_claim", "id": existing_claim.id, "label": existing_claim.id}],
            )]

        # Check stock availability
        all_mvts = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == item_id)).all()]
        proj = PureInventoryLedger.calculate_projection(all_mvts, target_item_id=item_id)
        if proj.available <= 0:
            return [Violation(
                code="OUT_OF_STOCK",
                severity=4,
                hard=True,
                message=f"Item '{item.name}' is out of stock (available: {proj.available})",
            )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        item = session.get(InventoryItem, req.payload.get("item_id"))
        return item.model_dump(mode="json") if item else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        part_id = p["participant_id"]
        item_id = p["item_id"]
        counter_id = p.get("counter_id", "DESK_CENTRAL")

        participant = session.get(Participant, part_id)
        canonical_id = (participant.canonical_id or participant.id) if participant else part_id

        item = session.get(InventoryItem, item_id)
        item_name = item.name if item else "merch"
        size = p.get("size_override") or (item.size if item else None) or (participant.tshirt_size if participant else None)

        claim = MerchClaim(
            canonical_participant_id=canonical_id,
            item_id=item_id,
            item_name=item_name,
            size=size,
            counter_id=counter_id,
            claimed_at=now(),
            issued_by=req.actor.id,
            status="ISSUED",
        )
        session.add(claim)
        session.flush()

        # Write ISSUE ledger movement
        loc_id = item.location_id if item else "loc_merch_warehouse"
        mvt = InventoryMovement(
            item_id=item_id,
            from_location_id=loc_id,
            to_location_id=None,
            quantity=1,
            movement_type="ISSUE",
            reason=f"Merch claim {claim.id} issued to participant {canonical_id}",
            reference_id=claim.id,
            moved_by=req.actor.id,
            moved_at=now(),
        )
        session.add(mvt)
        session.flush()

        # Update item cached values
        all_mvts = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == item_id)).all()]
        proj = PureInventoryLedger.calculate_projection(all_mvts, target_item_id=item_id)
        if item:
            item.quantity = proj.on_hand
            item.reserved_quantity = proj.reserved
            item.available_quantity = proj.available
            item.updated_at = now()
            session.add(item)
            session.flush()

        return {
            "claim_id": claim.id,
            "canonical_participant_id": canonical_id,
            "item_id": item_id,
            "item_name": item_name,
            "size": size,
            "counter_id": counter_id,
            "issued_at": claim.claimed_at.isoformat(),
            "issued_by": req.actor.id,
            "status": "ISSUED",
        }


@register_change_handler("merchandise.void")
class MerchandiseVoidHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        claim_id = p.get("claim_id") or req.entity_id
        reason = req.reason or p.get("reason")

        if not claim_id:
            return [Violation(code="MISSING_CLAIM", severity=4, hard=True, message="claim_id is required")]
        if not reason or not reason.strip():
            return [Violation(code="MANDATORY_REASON", severity=4, hard=True, message="Voiding an issue requires a recorded justification reason")]

        claim = session.get(MerchClaim, claim_id)
        if not claim:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Claim {claim_id} not found")]
        if claim.status == "VOIDED":
            return [Violation(code="ALREADY_VOIDED", severity=2, hard=True, message=f"Claim {claim_id} is already voided")]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        claim_id = req.payload.get("claim_id") or req.entity_id
        claim = session.get(MerchClaim, claim_id)
        return claim.model_dump(mode="json") if claim else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        claim_id = p.get("claim_id") or req.entity_id
        claim = session.get(MerchClaim, claim_id)

        claim.status = "VOIDED"
        claim.void_reason = req.reason or p.get("reason")
        claim.voided_by = req.actor.id
        claim.voided_at = now()
        session.add(claim)
        session.flush()

        # Write RETURN movement to awaiting_return
        mvt = InventoryMovement(
            item_id=claim.item_id,
            from_location_id=None,
            to_location_id="loc_merch_warehouse",
            quantity=1,
            movement_type="RETURN",
            reason=f"Claim {claim.id} voided: {claim.void_reason}",
            reference_id=claim.id,
            moved_by=req.actor.id,
            moved_at=now(),
        )
        session.add(mvt)
        session.flush()

        return {
            "claim_id": claim.id,
            "status": "VOIDED",
            "voided_at": claim.voided_at.isoformat(),
            "reason": claim.void_reason,
            "inventory_movement_type": "RETURN",
            "item_status": "AWAITING_RETURN",
        }

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        return "HIGH"
