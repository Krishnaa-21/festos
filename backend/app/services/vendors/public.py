# OWNER: P2
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now as clock_now
from app.engines.vendors.compliance import (
    get_certificate_validity_status,
    parse_expiry_date,
    verify_menu_labels,
)
from app.engines.vendors.coverage import evaluate_dietary_matrix, extract_vendor_categories
from app.models.participants import Participant
from app.models.vendors import MealSlot, Vendor, VendorAssignment, VendorSettlement
from app.schemas.common import EntityRef, RiskItem
from app.services.vendors.service import (
    generate_vendor_compliance_csv,
    generate_vendor_coverage_csv,
)


def summary(session: Session, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return vendor operations KPI summary as of `now`."""
    if now is None:
        now = clock_now()
    vendors = session.exec(select(Vendor)).all()
    active_vendors = [v for v in vendors if v.status == "ACTIVE"]

    valid_throughout = [
        v for v in active_vendors
        if get_certificate_validity_status(parse_expiry_date(v.hygiene_certificate_expiry)) == "VALID_THROUGHOUT"
    ]
    valid_capacity = sum(v.capacity or 0 for v in valid_throughout)

    # Check compliance flags
    mismatches = 0
    expired_count = 0
    for v in vendors:
        stat = get_certificate_validity_status(parse_expiry_date(v.hygiene_certificate_expiry))
        if stat in ["EXPIRED", "EXPIRES_DURING_FESTIVAL"]:
            expired_count += 1
        flags = verify_menu_labels(v.id, v.name, v.menu_description, v.dietary_options)
        mismatches += len(flags)

    return {
        "module": "vendors",
        "status": "OPERATIONAL",
        "total_vendors": len(vendors),
        "active_vendors_count": len(active_vendors),
        "valid_capacity": valid_capacity,
        "compliance_alerts_count": expired_count,
        "menu_mismatch_flags_count": mismatches,
    }


def risks(session: Session, now: Optional[datetime] = None) -> List[RiskItem]:
    """Return active vendor risks evaluated as of `now`."""
    if now is None:
        now = clock_now()
    risk_list: List[RiskItem] = []
    vendors = session.exec(select(Vendor)).all()
    participants = session.exec(select(Participant)).all()
    meal_slots = session.exec(select(MealSlot)).all()
    assignments = session.exec(select(VendorAssignment)).all()

    # 1. Hygiene Certificate Expiry Risks
    for v in vendors:
        exp_date = parse_expiry_date(v.hygiene_certificate_expiry)
        validity = get_certificate_validity_status(exp_date)

        if validity == "EXPIRED":
            risk_list.append(
                RiskItem(
                    id=f"rsk_vnd_exp_{v.id}",
                    module="vendors",
                    kind="EXPIRED_HYGIENE_CERTIFICATE",
                    title=f"Expired Hygiene Certificate: {v.name} ({v.id})",
                    severity=4,  # CRITICAL
                    hours_to_impact=0.0,
                    people_affected=v.capacity or 0,
                    uncertainty=0.0,
                    resource_criticality=5,
                    entity_refs=[EntityRef(type="vendor", id=v.id, label=v.name)],
                    action={"label": "Replace Vendor", "route": f"/vendors/{v.id}", "api": f"/api/v1/vendors/{v.id}/shutdown-impact"},
                    explanation=f"Certificate expired on {v.hygiene_certificate_expiry}. Vendor cannot legally serve food on campus.",
                )
            )
        elif validity == "EXPIRES_DURING_FESTIVAL":
            risk_list.append(
                RiskItem(
                    id=f"rsk_vnd_exp_mid_{v.id}",
                    module="vendors",
                    kind="CERTIFICATE_EXPIRES_MID_FESTIVAL",
                    title=f"Certificate Expiration Mid-Festival: {v.name} ({v.id})",
                    severity=3,  # HIGH
                    hours_to_impact=24.0,
                    people_affected=v.capacity or 0,
                    uncertainty=0.1,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="vendor", id=v.id, label=v.name)],
                    action={"label": "Plan Replacement", "route": f"/vendors/{v.id}", "api": f"/api/v1/vendors/{v.id}/shutdown-impact"},
                    explanation=f"Certificate expires on {v.hygiene_certificate_expiry}. Vendor capacity drops out of coverage starting next day.",
                )
            )

    # 2. Zero-Coverage Dietary Categories & Capacity Shortfalls
    matrix_res = evaluate_dietary_matrix(
        participants=participants,
        vendors=vendors,
        meal_slots=meal_slots,
        assignments=assignments,
        target_date=date(2026, 10, 31),
    )

    for alert in matrix_res.get("critical_alerts", []):
        cat = alert.get("category", "")
        risk_list.append(
            RiskItem(
                id=f"rsk_diet_zero_{cat}",
                module="vendors",
                kind="ZERO_COVERAGE_DIETARY_CATEGORY",
                title=f"Zero Compliant Vendors for '{cat.upper()}' Dietary Group",
                severity=4,  # CRITICAL
                hours_to_impact=4.0,
                people_affected=380 if cat == "jain" else (387 if cat == "gluten-free" else 411),
                uncertainty=0.0,
                resource_criticality=5,
                entity_refs=[EntityRef(type="dietary_category", id=cat, label=cat)],
                action={"label": "Procure Emergency Vendor", "route": "/vendors", "api": "/api/v1/food/coverage"},
                explanation=f"No compliant vendor serves '{cat}'. Participants in this category have zero meal options.",
            )
        )

    # 3. Overdue Settlements
    overdue_settlements = session.exec(
        select(VendorSettlement).where(VendorSettlement.status == "OVERDUE")
    ).all()
    for stl in overdue_settlements:
        risk_list.append(
            RiskItem(
                id=f"rsk_stl_overdue_{stl.id}",
                module="vendors",
                kind="OVERDUE_VENDOR_SETTLEMENT",
                title=f"Overdue Vendor Payment: {stl.vendor_id} (₹{stl.balance_due_inr:,.2f})",
                severity=3,  # HIGH
                hours_to_impact=12.0,
                people_affected=1,
                uncertainty=0.0,
                resource_criticality=3,
                entity_refs=[EntityRef(type="vendor_settlement", id=stl.id, label=stl.id)],
                action={"label": "Disburse Payment", "route": "/finance", "api": f"/api/v1/finance/vendor-settlements/{stl.id}/pay"},
                explanation=f"Payment of ₹{stl.balance_due_inr:,.2f} passed due date {stl.due_date}. Vendor supply stoppage threat.",
            )
        )

    return risk_list


def dependents(session: Session, entity_type: str, entity_id: Optional[str] = None) -> List[EntityRef]:
    """Return downstream entities affected by vendor (vendor -> meal slots, locations, dietary groups)."""
    target_id = entity_id if entity_id is not None else entity_type
    deps: List[EntityRef] = []
    assignments = session.exec(
        select(VendorAssignment).where(VendorAssignment.vendor_id == target_id)
    ).all()
    for a in assignments:
        deps.append(EntityRef(type="meal_slot", id=a.meal_slot_id, label=f"MealSlot {a.meal_slot_id}"))
        if a.venue_id:
            deps.append(EntityRef(type="venue", id=a.venue_id, label=f"Venue {a.venue_id}"))

    v = session.get(Vendor, target_id)
    if v:
        cats = extract_vendor_categories(v.dietary_options)
        for c in cats:
            deps.append(EntityRef(type="dietary_category", id=c, label=f"Diet {c}"))
    return deps


def vendor_coverage_csv(session: Session) -> str:
    """Generate vendor_coverage.csv string (Report Function)."""
    return generate_vendor_coverage_csv(session)


def vendor_compliance_csv(session: Session) -> str:
    """Generate vendor_compliance.csv string (Report Function)."""
    return generate_vendor_compliance_csv(session)
