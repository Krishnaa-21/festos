# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlmodel import Session

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.decision_log import add_decision_card
from app.core.errors import NotFoundError
from app.core.registry import register_change_handler
from app.models.audit import Override
from app.models.vendors import EmergencySpend, VendorSettlement
from app.schemas.common import Role, Severity, Violation

logger = logging.getLogger("festos.services.finance.handlers")


@register_change_handler("finance.record_payment")
class RecordPaymentHandler(ChangeHandler):
    """Records a payment against a vendor settlement."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        settlement_id = req.entity_id or req.payload.get("settlement_id")
        amount = req.payload.get("amount_inr", 0.0)

        settlement = session.get(VendorSettlement, settlement_id)
        if not settlement:
            violations.append(
                Violation(
                    code="SETTLEMENT_NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Vendor settlement '{settlement_id}' not found.",
                )
            )
            return violations

        if amount <= 0:
            violations.append(
                Violation(
                    code="INVALID_PAYMENT_AMOUNT",
                    severity=Severity.HIGH,
                    hard=True,
                    message="Payment amount must be greater than zero.",
                )
            )

        if amount > (settlement.balance_due_inr + 0.01):
            violations.append(
                Violation(
                    code="OVERPAYMENT_NOT_ALLOWED",
                    severity=Severity.MEDIUM,
                    hard=False,
                    message=f"Payment amount (₹{amount}) exceeds balance due (₹{settlement.balance_due_inr}).",
                )
            )

        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        settlement_id = req.entity_id or req.payload.get("settlement_id")
        settlement = session.get(VendorSettlement, settlement_id)
        return {
            "settlement_id": settlement_id,
            "advance_paid_inr": settlement.advance_paid_inr if settlement else 0.0,
            "balance_due_inr": settlement.balance_due_inr if settlement else 0.0,
            "status": settlement.status if settlement else "UNKNOWN",
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        settlement_id = req.entity_id or req.payload.get("settlement_id")
        amount = float(req.payload.get("amount_inr", 0.0))
        ref = req.payload.get("payment_reference", "DIRECT_TRANSFER")
        notes = req.reason or req.payload.get("notes", "Settlement payment")

        settlement = session.get(VendorSettlement, settlement_id)
        if not settlement:
            raise NotFoundError(f"Settlement '{settlement_id}' not found.")

        settlement.advance_paid_inr += amount
        settlement.balance_due_inr = max(0.0, settlement.contract_amount_inr - settlement.advance_paid_inr)

        if settlement.balance_due_inr == 0:
            settlement.status = "PAID"
        else:
            settlement.status = "PARTIALLY_PAID"

        settlement.updated_at = now()
        session.add(settlement)

        add_decision_card(
            session=session,
            module="finance",
            decision_type="VENDOR_PAYMENT",
            title=f"Disbursed ₹{amount:,.2f} for Vendor Settlement {settlement.vendor_id}",
            summary=f"Payment of ₹{amount:,.2f} recorded (Ref: {ref}). Balance: ₹{settlement.balance_due_inr:,.2f}.",
            why=notes,
            hard_constraints_satisfied=["Payment terms satisfied"],
            soft_constraints_relaxed=[],
            cost_impact_inr=amount,
            people_affected=1,
            approved_by=req.actor.name or req.actor.id,
            entity_refs=[{"type": "vendor_settlement", "id": settlement.id}, {"type": "vendor", "id": settlement.vendor_id}],
        )

        session.flush()
        return {
            "settlement_id": settlement.id,
            "vendor_id": settlement.vendor_id,
            "paid_amount_inr": amount,
            "remaining_balance_inr": settlement.balance_due_inr,
            "status": settlement.status,
        }


@register_change_handler("finance.open_dispute")
class OpenDisputeHandler(ChangeHandler):
    """Opens a commercial dispute on a vendor settlement invoice."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        settlement_id = req.entity_id or req.payload.get("settlement_id")
        reason = req.reason or req.payload.get("reason")

        settlement = session.get(VendorSettlement, settlement_id)
        if not settlement:
            violations.append(
                Violation(
                    code="SETTLEMENT_NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Vendor settlement '{settlement_id}' not found.",
                )
            )
            return violations

        if not reason or not reason.strip():
            violations.append(
                Violation(
                    code="DISPUTE_REASON_REQUIRED",
                    severity=Severity.HIGH,
                    hard=True,
                    message="A recorded dispute reason is required to dispute an invoice.",
                )
            )

        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        settlement_id = req.entity_id or req.payload.get("settlement_id")
        settlement = session.get(VendorSettlement, settlement_id)
        return {
            "settlement_id": settlement_id,
            "status": settlement.status if settlement else "UNKNOWN",
            "dispute_reason": settlement.dispute_reason if settlement else None,
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        settlement_id = req.entity_id or req.payload.get("settlement_id")
        reason = req.reason or req.payload.get("reason", "Commercial billing dispute")
        raw_amount = req.payload.get("amount_inr")
        if raw_amount is None:
            raw_amount = req.payload.get("disputed_amount_inr", 0.0)
        amount = float(raw_amount or 0.0)

        settlement = session.get(VendorSettlement, settlement_id)
        if not settlement:
            raise NotFoundError(f"Settlement '{settlement_id}' not found.")

        settlement.status = "DISPUTED"
        settlement.dispute_reason = reason
        settlement.disputed_amount_inr = amount if amount > 0 else settlement.balance_due_inr
        settlement.dispute_opened_by = req.actor.name or req.actor.id
        settlement.dispute_opened_at = now()
        settlement.updated_at = now()
        session.add(settlement)

        session.flush()
        return {
            "settlement_id": settlement.id,
            "vendor_id": settlement.vendor_id,
            "status": "DISPUTED",
            "disputed_amount_inr": settlement.disputed_amount_inr,
            "reason": reason,
        }


@register_change_handler("finance.emergency_spend")
class EmergencySpendHandler(ChangeHandler):
    """Records or approves emergency expenditure."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        amount = float(req.payload.get("amount_inr", 0.0))

        if amount <= 0:
            violations.append(
                Violation(
                    code="INVALID_AMOUNT",
                    severity=Severity.HIGH,
                    hard=True,
                    message="Emergency spend amount must be positive.",
                )
            )

        if not req.reason or not req.reason.strip():
            violations.append(
                Violation(
                    code="REASON_REQUIRED",
                    severity=Severity.HIGH,
                    hard=True,
                    message="Emergency expenditure requires a mandatory recorded reason.",
                )
            )

        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {"action": "emergency_spend"}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        amount = float(req.payload.get("amount_inr", 0.0))
        desc = req.payload.get("description", "Emergency fest procurement")
        category = req.payload.get("category", "VENDOR_BACKUP")
        reason = req.reason or "Unforeseen operational requirement"

        # Festival Director approval is required for emergency spend > 25,000 INR unless approved by Director
        is_director = req.actor.role in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]
        spend_status = "APPROVED" if (is_director or amount <= 25000) else "PENDING_APPROVAL"

        spend = EmergencySpend(
            description=desc,
            amount_inr=amount,
            category=category,
            reason=reason,
            approved_by=req.actor.name or req.actor.id if spend_status == "APPROVED" else None,
            approved_at=now() if spend_status == "APPROVED" else None,
            status=spend_status,
            created_at=now(),
        )
        session.add(spend)
        if spend_status == "APPROVED":
            ovr = Override(
                entity_type="emergency_spend",
                entity_id=spend.id,
                constraint_code="BUDGET_OVERRIDE",
                reason=f"Emergency spend: {desc} (₹{amount:,.2f}) - {reason}",
                approved_by=req.actor.name or req.actor.id,
                approved_at=now(),
                risk_level="HIGH",
                status="ACTIVE",
            )
            session.add(ovr)
        session.flush()

        return {
            "id": spend.id,
            "status": spend.status,
            "amount_inr": spend.amount_inr,
            "description": spend.description,
        }
