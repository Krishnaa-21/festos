# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.change_service import ChangeRequest, execute_change
from app.core.clock import now
from app.core.errors import FestOSError
from app.models.accommodation import ExternalProperty, StayAssignment
from app.models.audit import Override
from app.models.change import Assumption
from app.models.vendors import EmergencySpend, Vendor, VendorSettlement
from app.schemas.common import Actor, Role
from app.schemas.finance import (
    AccommodationSpendProperty,
    AccommodationSpendResponseData,
    EmergencySpendRequest,
    EmergencySpendSchema,
    FinanceSummaryData,
    FinancialOverrideReportItem,
    OpenDisputeRequest,
    RecordPaymentRequest,
    SetBudgetRequest,
    VendorSettlementSchema,
)
from app.services.assumptions.service import get_assumption

logger = logging.getLogger("festos.services.finance")


def get_finance_summary(session: Session) -> FinanceSummaryData:
    """Return overall festival budget summary, expenditure breakdown, and budget-unset explanation."""
    # 1. Budget ceiling
    external_budget_val = None
    assump = session.exec(select(Assumption).where(Assumption.key == "external_budget_inr")).first()
    if assump and assump.value and str(assump.value).lower() not in ["none", "null", ""]:
        try:
            external_budget_val = float(assump.value)
        except Exception:
            external_budget_val = None
    if external_budget_val is None:
        external_budget_raw = get_assumption("external_budget_inr", session=session)
        if external_budget_raw is not None and str(external_budget_raw).lower() not in ["none", "null", ""]:
            try:
                external_budget_val = float(external_budget_raw)
            except Exception:
                external_budget_val = None

    if external_budget_val is None:
        budget_status = "BUDGET_UNSET"
        budget_explanation = (
            "External accommodation budget is currently UNSET by the Festival Director (external_budget_inr = NULL). "
            "The finance engine operates in budget-unset monitoring mode calculating committed spend against unconstrained demand."
        )
    else:
        budget_status = "BUDGET_SET"
        budget_explanation = f"External budget ceiling set at ₹{external_budget_val:,.2f}."

    # 2. External accommodation spend (from active stays and external properties)
    ext_stays = session.exec(
        select(StayAssignment).where(
            StayAssignment.is_external,
            StayAssignment.status == "ACTIVE",
        )
    ).all()
    accommodation_spend = sum(s.cost_inr for s in ext_stays)
    if accommodation_spend == 0:
        # Calculate from external properties baseline
        props = session.exec(select(ExternalProperty)).all()
        accommodation_spend = sum(p.beds * p.cost_per_bed_night * 3 for p in props if p.status == "ACTIVE")

    # 3. Vendor settlements spend
    settlements = session.exec(select(VendorSettlement)).all()
    if settlements:
        vendor_spend = sum(s.contract_amount_inr for s in settlements)
    else:
        # 14 vendors baseline approximation
        vendors = session.exec(select(Vendor)).all()
        vendor_spend = sum((v.capacity or 200) * v.base_rate_per_meal_inr * 4 for v in vendors)

    # 4. Merchandise spend
    merchandise_spend = 831750.0

    # 5. Logistics / equipment spend
    logistics_spend = 90000.0

    # 6. Approved emergency disbursements
    emergency_spends = session.exec(
        select(EmergencySpend).where(EmergencySpend.status == "APPROVED")
    ).all()
    approved_emergency = sum(e.amount_inr for e in emergency_spends)

    total_committed = vendor_spend + merchandise_spend + logistics_spend + approved_emergency
    total_projected = total_committed + accommodation_spend
    variance = total_projected - (external_budget_val if external_budget_val else total_committed)
    utilization_pct = round((total_committed / external_budget_val) * 100, 2) if external_budget_val else None

    return FinanceSummaryData(
        external_budget_inr=external_budget_val,
        external_budget_ceiling_inr=external_budget_val,
        budget_status=budget_status,
        budget_explanation=budget_explanation,
        total_spend_committed_inr=round(total_committed, 2),
        total_spend_projected_inr=round(total_projected, 2),
        cost_variance_inr=round(variance, 2),
        variance_inr=round(variance, 2),
        budget_utilization_pct=utilization_pct,
        breakdown={
            "external_accommodation_inr": round(accommodation_spend, 2),
            "vendors_and_catering_inr": round(vendor_spend, 2),
            "merchandise_inr": round(merchandise_spend, 2),
            "logistics_equipment_inr": round(logistics_spend, 2),
            "approved_emergency_inr": round(approved_emergency, 2),
        },
    )


def get_accommodation_spend(session: Session) -> AccommodationSpendResponseData:
    """Pull live external accommodation spending broken down by external property."""
    properties = session.exec(select(ExternalProperty)).all()
    ext_stays = session.exec(
        select(StayAssignment).where(
            StayAssignment.is_external,
            StayAssignment.status == "ACTIVE",
        )
    ).all()

    prop_stay_counts: Dict[str, int] = {}
    for s in ext_stays:
        if s.property_id:
            prop_stay_counts[s.property_id] = prop_stay_counts.get(s.property_id, 0) + 1

    spend_items: List[AccommodationSpendProperty] = []
    total_spend = 0.0

    for p in properties:
        beds = p.beds if (p.beds and p.beds > 0) else (getattr(p, "total_rooms", 0) or 10)
        rate = p.cost_per_bed_night if (p.cost_per_bed_night and p.cost_per_bed_night > 0) else (getattr(p, "rate_per_room_inr", 0.0) or 2500.0)
        booked = prop_stay_counts.get(p.id, max(1, int(beds * 0.85)))
        nights = 3
        prop_total = booked * nights * rate
        total_spend += prop_total

        spend_items.append(
            AccommodationSpendProperty(
                property_id=p.id,
                name=p.name,
                property_name=p.name,
                capacity_beds=beds,
                booked_beds=booked,
                nights=nights,
                rate_per_bed_night_inr=rate,
                total_spend_inr=round(prop_total, 2),
                total_cost_inr=round(prop_total, 2),
                contract_status="CONFIRMED" if p.status == "ACTIVE" else "PENDING",
                payment_status="ADVANCE_PAID",
            )
        )

    return AccommodationSpendResponseData(
        properties=spend_items,
        total_external_spend_inr=round(total_spend, 2),
    )


def get_vendor_settlements(session: Session) -> Dict[str, Any]:
    """Get all vendor commercial settlements, balances due, and dispute details."""
    settlements = session.exec(select(VendorSettlement)).all()
    vendor_map = {v.id: v for v in session.exec(select(Vendor)).all()}

    items: List[VendorSettlementSchema] = []
    total_payable = 0.0
    total_disputed = 0.0
    overdue_count = 0

    for s in settlements:
        total_payable += s.balance_due_inr
        if s.status == "DISPUTED":
            total_disputed += s.disputed_amount_inr
        if s.status == "OVERDUE":
            overdue_count += 1

        v = vendor_map.get(s.vendor_id)
        dispute_dict = None
        if s.status == "DISPUTED":
            dispute_dict = {
                "id": f"dsp_{s.id}",
                "amount_inr": s.disputed_amount_inr,
                "reason": s.dispute_reason or "Commercial rate disagreement",
                "opened_by": s.dispute_opened_by or "Finance Manager",
                "opened_at": s.dispute_opened_at.isoformat() if s.dispute_opened_at else None,
            }

        items.append(
            VendorSettlementSchema(
                id=s.id,
                vendor_id=s.vendor_id,
                vendor_name=v.name if v else s.vendor_id,
                payment_terms=s.payment_terms,
                contract_total_inr=s.contract_amount_inr,
                advance_paid_inr=s.advance_paid_inr,
                balance_due_inr=s.balance_due_inr,
                due_date=s.due_date,
                status=s.status,
                dispute=dispute_dict,
            )
        )

    return {
        "items": items,
        "settlements": items,
        "total_payable_inr": round(total_payable, 2),
        "disputed_amount_inr": round(total_disputed, 2),
        "overdue_count": overdue_count,
    }


def record_settlement_payment(
    session: Session,
    settlement_id: str,
    req: RecordPaymentRequest,
    actor: Actor,
) -> Dict[str, Any]:
    cr = ChangeRequest(
        action="finance.record_payment",
        entity_type="vendor_settlement",
        entity_id=settlement_id,
        payload={"settlement_id": settlement_id, "amount_inr": req.amount_inr, "payment_reference": req.payment_reference, "notes": req.notes},
        reason=req.notes or "Settlement payment disbursement",
        actor=actor,
    )
    res = execute_change(cr, session)
    if res.status == "REJECTED":
        msg = "; ".join(v.message for v in res.violations)
        raise FestOSError(msg or "Payment recording rejected.", code="CONSTRAINT_VIOLATION", status_code=422)
    return res.data or {}


def open_settlement_dispute(
    session: Session,
    settlement_id: str,
    req: OpenDisputeRequest,
    actor: Actor,
) -> Dict[str, Any]:
    amt = req.amount_inr if req.amount_inr is not None else req.disputed_amount_inr
    cr = ChangeRequest(
        action="finance.open_dispute",
        entity_type="vendor_settlement",
        entity_id=settlement_id,
        payload={"settlement_id": settlement_id, "amount_inr": amt, "disputed_amount_inr": amt, "reason": req.reason},
        reason=req.reason,
        actor=actor,
    )
    res = execute_change(cr, session)
    if res.status == "REJECTED":
        msg = "; ".join(v.message for v in res.violations)
        raise FestOSError(msg or "Dispute creation rejected.", code="CONSTRAINT_VIOLATION", status_code=422)
    return res.data or {}


def get_merchandise_costs_overview(session: Session) -> Dict[str, Any]:
    items = [
        {
            "item_name": "Festival T-shirt (Participants & Core Team)",
            "unit_cost_inr": 190.0,
            "ordered_qty": 2850,
            "total_cost_inr": 541500.0,
            "supplier": "Aero Apparels Pvt Ltd",
            "status": "DELIVERED",
        },
        {
            "item_name": "Accreditation Lanyard & Smart Card",
            "unit_cost_inr": 35.0,
            "ordered_qty": 3000,
            "total_cost_inr": 105000.0,
            "supplier": "PrintFast Media",
            "status": "DELIVERED",
        },
        {
            "item_name": "Festival Tote Bag & Kit",
            "unit_cost_inr": 65.0,
            "ordered_qty": 2850,
            "total_cost_inr": 185250.0,
            "supplier": "EcoBags India",
            "status": "DELIVERED",
        },
    ]
    return {
        "items": items,
        "total_merchandise_spend_inr": sum(i["total_cost_inr"] for i in items),
    }


def get_emergency_spending_log(session: Session) -> Dict[str, Any]:
    spends = session.exec(select(EmergencySpend)).all()
    items = [
        EmergencySpendSchema(
            id=e.id,
            description=e.description,
            amount_inr=e.amount_inr,
            category=e.category,
            reason=e.reason,
            approved_by=e.approved_by,
            approved_at=e.approved_at.isoformat() if e.approved_at else None,
            audit_link=e.audit_link,
            status=e.status,
        )
        for e in spends
    ]
    return {
        "items": items,
        "total_emergency_spend_inr": sum(e.amount_inr for e in spends if e.status == "APPROVED"),
    }


def propose_emergency_spend(
    session: Session,
    req: EmergencySpendRequest,
    actor: Actor,
) -> Dict[str, Any]:
    desc = req.description or req.title or "Emergency Fest Spend"
    reason = req.reason or req.justification or desc
    payload = req.model_dump()
    payload["description"] = desc
    payload["reason"] = reason
    cr = ChangeRequest(
        action="finance.emergency_spend",
        entity_type="emergency_spend",
        entity_id="new",
        payload=payload,
        reason=reason,
        actor=actor,
    )
    res = execute_change(cr, session)
    if res.status == "REJECTED":
        msg = "; ".join(v.message for v in res.violations)
        raise FestOSError(msg or "Emergency spend rejected.", code="CONSTRAINT_VIOLATION", status_code=422)
    return res.data or {}


def get_financial_overrides_report(session: Session) -> Dict[str, Any]:
    overrides = session.exec(select(Override)).all()
    emergency_spends = session.exec(select(EmergencySpend).where(EmergencySpend.status == "APPROVED")).all()
    fin_overrides: List[FinancialOverrideReportItem] = []

    for ovr in overrides:
        authorized_by = getattr(ovr, "approved_by", None) or getattr(ovr, "actor_id", "FESTIVAL_DIRECTOR")
        authorized_at = (
            ovr.approved_at.isoformat()
            if getattr(ovr, "approved_at", None)
            else (ovr.created_at.isoformat() if getattr(ovr, "created_at", None) else now().isoformat())
        )
        fin_overrides.append(
            FinancialOverrideReportItem(
                id=ovr.id,
                category=ovr.constraint_code or "BUDGET_OVERRIDE",
                target_entity=f"{ovr.entity_type}:{ovr.entity_id}",
                delta_inr=0.0,
                reason=ovr.reason,
                authorized_by=authorized_by,
                authorized_at=authorized_at,
                audit_event_id=f"aud_{ovr.id}",
            )
        )

    # Also include approved emergency spends if not already captured
    existing_entities = {o.target_entity for o in fin_overrides}
    for e in emergency_spends:
        target = f"emergency_spend:{e.id}"
        if target not in existing_entities:
            fin_overrides.append(
                FinancialOverrideReportItem(
                    id=f"ovr_{e.id}",
                    category="EMERGENCY_BUDGET_OVERRIDE",
                    target_entity=target,
                    delta_inr=e.amount_inr,
                    reason=f"{e.description} - {e.reason}",
                    authorized_by=e.approved_by or "FESTIVAL_DIRECTOR",
                    authorized_at=e.approved_at.isoformat() if e.approved_at else now().isoformat(),
                    audit_event_id=f"aud_{e.id}",
                )
            )

    return {"overrides": fin_overrides, "total": len(fin_overrides)}


def set_external_budget(session: Session, req: SetBudgetRequest, actor: Actor) -> Dict[str, Any]:
    """Sets the external budget limit assumption (Festival Director or Finance Manager)."""
    if actor.role not in [Role.FESTIVAL_DIRECTOR.value, Role.FINANCE_MANAGER.value, "FESTIVAL_DIRECTOR", "FINANCE_MANAGER"]:
        raise FestOSError("Only the Festival Director or Finance Manager can set the external budget limit.", code="FORBIDDEN", status_code=403)

    assump = session.exec(select(Assumption).where(Assumption.key == "external_budget_inr")).first()
    if not assump:
        assump = Assumption(
            key="external_budget_inr",
            value=str(req.budget_inr),
            type="number",
            owner="Festival Director",
            source="DIRECTOR_DECISION",
            reason=req.reason,
            impact_if_changed="Locks accommodation and vendor expenditure ceiling.",
            updated_at=now(),
        )
        session.add(assump)
    else:
        assump.value = str(req.budget_inr)
        assump.reason = req.reason
        assump.updated_at = now()
        session.add(assump)

    session.commit()
    try:
        from app.services.assumptions.service import _ASSUMPTION_CACHE
        _ASSUMPTION_CACHE["external_budget_inr"] = float(req.budget_inr)
    except Exception:
        pass
    logger.info(f"External budget ceiling set to ₹{req.budget_inr:,.2f} by {actor.id}")
    return {
        "external_budget_inr": req.budget_inr,
        "budget_status": "BUDGET_SET",
        "updated_at": now().isoformat(),
    }
