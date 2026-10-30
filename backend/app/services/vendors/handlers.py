# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.decision_log import add_decision_card
from app.core.errors import NotFoundError
from app.core.registry import register_change_handler
from app.models.vendors import MealSlot, Vendor, VendorAssignment
from app.schemas.common import Severity, Violation
from app.services.notifications.service import generate_drafts

logger = logging.getLogger("festos.services.vendors.handlers")


@register_change_handler("vendors.shutdown")
class VendorShutdownHandler(ChangeHandler):
    """Executes emergency vendor shutdown, slot reassignment, and notification drafting."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        vendor_id = req.entity_id or req.payload.get("vendor_id")
        replacement_id = req.payload.get("replacement_vendor_id")

        vendor = session.get(Vendor, vendor_id)
        if not vendor:
            violations.append(
                Violation(
                    code="VENDOR_NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Vendor '{vendor_id}' not found.",
                )
            )
            return violations

        if vendor.status == "SHUT_DOWN":
            violations.append(
                Violation(
                    code="VENDOR_ALREADY_SHUT_DOWN",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Vendor '{vendor_id}' is already shut down.",
                )
            )

        if replacement_id:
            replacement = session.get(Vendor, replacement_id)
            if not replacement:
                violations.append(
                    Violation(
                        code="REPLACEMENT_VENDOR_NOT_FOUND",
                        severity=Severity.HIGH,
                        hard=True,
                        message=f"Replacement vendor '{replacement_id}' not found.",
                    )
                )
            elif replacement.status != "ACTIVE":
                violations.append(
                    Violation(
                        code="REPLACEMENT_NOT_ACTIVE",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message=f"Replacement vendor '{replacement_id}' is not in ACTIVE status ({replacement.status}).",
                    )
                )

        if not req.reason or not req.reason.strip():
            violations.append(
                Violation(
                    code="REASON_REQUIRED",
                    severity=Severity.CRITICAL,
                    hard=True,
                    message="A recorded operational reason is required to shut down a vendor.",
                )
            )

        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        vendor_id = req.entity_id or req.payload.get("vendor_id")
        vendor = session.get(Vendor, vendor_id)
        assignments = session.exec(
            select(VendorAssignment).where(
                VendorAssignment.vendor_id == vendor_id,
                VendorAssignment.status.in_(["SCHEDULED", "ACTIVE"]),
            )
        ).all()
        return {
            "vendor_id": vendor_id,
            "previous_status": vendor.status if vendor else "UNKNOWN",
            "active_assignments": [
                {
                    "assignment_id": a.id,
                    "meal_slot_id": a.meal_slot_id,
                    "venue_id": a.venue_id,
                    "date": a.date,
                    "allocated_capacity": a.allocated_capacity,
                }
                for a in assignments
            ],
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        vendor_id = req.entity_id or req.payload.get("vendor_id")
        replacement_id = req.payload.get("replacement_vendor_id")
        reason = req.reason or "Emergency health/compliance shutdown"
        dispatch_notifications = req.payload.get("dispatch_notifications", True)

        vendor = session.get(Vendor, vendor_id)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_id}' not found.")

        # 1. Update vendor status
        vendor.status = "SHUT_DOWN"
        vendor.updated_at = now()
        session.add(vendor)

        # 2. Reassign active assignments to replacement vendor
        replacement = session.get(Vendor, replacement_id) if replacement_id else None
        reassigned_count = 0
        affected_locations: List[str] = []
        affected_slots: List[str] = []

        assignments = session.exec(
            select(VendorAssignment).where(
                VendorAssignment.vendor_id == vendor_id,
                VendorAssignment.status.in_(["SCHEDULED", "ACTIVE"]),
            )
        ).all()

        slot_map = {s.id: s for s in session.exec(select(MealSlot)).all()}

        for a in assignments:
            if getattr(a, "venue_id", None):
                affected_locations.append(a.venue_id)
            if a.meal_slot_id in slot_map:
                affected_slots.append(slot_map[a.meal_slot_id].name)

            if replacement:
                a.vendor_id = replacement.id
                a.rate_per_meal_inr = replacement.base_rate_per_meal_inr
                a.status = "REASSIGNED"
                a.updated_at = now()
                session.add(a)
                reassigned_count += 1
            else:
                a.status = "CANCELLED"
                a.updated_at = now()
                session.add(a)

        # 3. Stage notification drafts across all 5 audiences (Spec 6.14)
        drafts_created = 0
        if dispatch_notifications:
            context = {
                "vendor_name": vendor.name,
                "replacement_name": replacement.name if replacement else "an alternative counter",
                "location": ", ".join(sorted(set(affected_locations))) or "Main Campus Dining Hall",
                "affected_slots": sorted(set(affected_slots)) or ["LUNCH", "DINNER"],
                "lost_capacity": vendor.capacity or 200,
                "reason": reason,
            }
            drafts = generate_drafts(
                event_type="VENDOR_SHUTDOWN",
                context=context,
                change_set_id=getattr(req, "change_set_id", None),
                session=session,
            )
            drafts_created = len(drafts)

        # 4. Record Decision Card
        add_decision_card(
            session=session,
            module="vendors",
            decision_type="VENDOR_SHUTDOWN",
            title=f"Emergency Shutdown: {vendor.name} ({vendor.id})",
            summary=f"Shut down {vendor.name} due to '{reason}'. Reassigned {reassigned_count} slots to {replacement.name if replacement else 'None'}.",
            why=reason,
            hard_constraints_satisfied=["Food safety compliance enforced"],
            soft_constraints_relaxed=[{"constraint": "Original vendor allocation", "reason": reason}],
            cost_impact_inr=(
                ((replacement.base_rate_per_meal_inr - vendor.base_rate_per_meal_inr) * (vendor.capacity or 0))
                if replacement
                else 0.0
            ),
            people_affected=vendor.capacity or 0,
            approved_by=req.actor.name or req.actor.id,
            entity_refs=[
                {"type": "vendor", "id": vendor.id},
                *([{"type": "vendor", "id": replacement.id}] if replacement else []),
            ],
        )

        session.flush()
        logger.info(f"Vendor '{vendor.id}' shut down successfully. Reassigned: {reassigned_count}, Drafts: {drafts_created}")

        return {
            "status": "APPLIED",
            "vendor_id": vendor.id,
            "new_status": "SHUT_DOWN",
            "replacement_assigned": replacement.id if replacement else None,
            "slots_reassigned": reassigned_count,
            "drafts_created": drafts_created,
        }
