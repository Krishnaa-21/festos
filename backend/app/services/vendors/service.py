# OWNER: P2
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.change_service import ChangeRequest, execute_change
from app.core.errors import FestOSError, NotFoundError
from app.engines.vendors.compliance import (
    get_certificate_validity_status,
    parse_expiry_date,
    verify_menu_labels,
)
from app.engines.vendors.coverage import (
    evaluate_dietary_matrix,
    extract_vendor_categories,
)
from app.engines.vendors.shutdown import vendor_shutdown_analysis
from app.models.participants import Participant
from app.models.vendors import MealSlot, Vendor, VendorAssignment
from app.schemas.common import Actor
from app.schemas.vendors import (
    VendorDetailSchema,
    VendorShutdownAnalysisRequest,
    VendorShutdownAnalysisResult,
    VendorShutdownExecuteRequest,
    VendorSummarySchema,
)

logger = logging.getLogger("festos.services.vendors")


def list_vendors(
    session: Session,
    status: Optional[str] = None,
    dietary_option: Optional[str] = None,
    compliance_status: Optional[str] = None,
) -> Dict[str, Any]:
    """List vendors with compliance status, capacities, and slot counts."""
    query = select(Vendor)
    if status:
        query = query.where(Vendor.status == status)
    vendors = session.exec(query).all()

    assignments = session.exec(select(VendorAssignment)).all()
    assign_counts: Dict[str, int] = {}
    for a in assignments:
        assign_counts[a.vendor_id] = assign_counts.get(a.vendor_id, 0) + 1

    items: List[VendorSummarySchema] = []
    for v in vendors:
        exp_date = parse_expiry_date(v.hygiene_certificate_expiry)
        comp_stat = get_certificate_validity_status(exp_date)

        if compliance_status and comp_stat != compliance_status:
            continue

        declared_cats = sorted(extract_vendor_categories(v.dietary_options))
        if dietary_option and dietary_option.lower() not in [c.lower() for c in declared_cats]:
            continue

        flags = verify_menu_labels(v.id, v.name, v.menu_description, v.dietary_options)
        unverified = [f["menu_keyword"].lower() for f in flags if f.get("status") == "UNVERIFIED"]

        items.append(
            VendorSummarySchema(
                id=v.id,
                name=v.name,
                status=v.status,
                menu_description=v.menu_description,
                dietary_options=v.dietary_options,
                declared_categories=declared_cats,
                unverified_categories=unverified,
                hours=v.hours,
                capacity=v.capacity,
                hygiene_certificate_expiry=v.hygiene_certificate_expiry,
                compliance_status=comp_stat,
                payment_terms=v.payment_terms,
                base_rate_per_meal_inr=v.base_rate_per_meal_inr,
                contact_phone=v.contact_phone,
                assigned_slots_count=assign_counts.get(v.id, 0),
            )
        )

    return {"items": items, "total": len(items)}


def get_vendor_detail(session: Session, vendor_id: str) -> VendorDetailSchema:
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise NotFoundError(f"Vendor '{vendor_id}' not found.")

    assignments = session.exec(
        select(VendorAssignment).where(VendorAssignment.vendor_id == vendor_id)
    ).all()
    slot_map = {s.id: s for s in session.exec(select(MealSlot)).all()}

    assign_dicts: List[Dict[str, Any]] = [
        {
            "id": a.id,
            "meal_slot_id": a.meal_slot_id,
            "meal_slot_name": slot_map[a.meal_slot_id].name if a.meal_slot_id in slot_map else "SLOT",
            "date": a.date,
            "venue_id": a.venue_id,
            "location_name": a.location_name or a.venue_id or "Food Court",
            "allocated_capacity": a.allocated_capacity,
            "rate_per_meal_inr": a.rate_per_meal_inr,
            "status": a.status,
        }
        for a in assignments
    ]

    exp_date = parse_expiry_date(vendor.hygiene_certificate_expiry)
    comp_stat = get_certificate_validity_status(exp_date)
    declared_cats = sorted(extract_vendor_categories(vendor.dietary_options))
    flags = verify_menu_labels(vendor.id, vendor.name, vendor.menu_description, vendor.dietary_options)
    unverified = [f["menu_keyword"].lower() for f in flags if f.get("status") == "UNVERIFIED"]

    return VendorDetailSchema(
        id=vendor.id,
        name=vendor.name,
        status=vendor.status,
        menu_description=vendor.menu_description,
        dietary_options=vendor.dietary_options,
        declared_categories=declared_cats,
        unverified_categories=unverified,
        hours=vendor.hours,
        capacity=vendor.capacity,
        hygiene_certificate_expiry=vendor.hygiene_certificate_expiry,
        compliance_status=comp_stat,
        payment_terms=vendor.payment_terms,
        base_rate_per_meal_inr=vendor.base_rate_per_meal_inr,
        contact_phone=vendor.contact_phone,
        assignments=assign_dicts,
        compliance_flags=flags,
    )


def simulate_shutdown_impact(
    session: Session,
    vendor_id: str,
    req: VendorShutdownAnalysisRequest,
) -> VendorShutdownAnalysisResult:
    """Simulate the 10 steps of Feature 7 for shutting down a vendor."""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise NotFoundError(f"Vendor '{vendor_id}' not found.")

    all_vendors = session.exec(select(Vendor)).all()
    meal_slots = session.exec(select(MealSlot)).all()
    assignments = session.exec(select(VendorAssignment)).all()

    result = vendor_shutdown_analysis(
        vendor=vendor,
        all_vendors=all_vendors,
        meal_slots=meal_slots,
        assignments=assignments,
        from_time=req.from_time,
        reason=req.reason,
    )
    return VendorShutdownAnalysisResult(**result)


def execute_shutdown(
    session: Session,
    vendor_id: str,
    req: VendorShutdownExecuteRequest,
    actor: Actor,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute vendor shutdown through ChangeService (`vendors.shutdown`)."""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise NotFoundError(f"Vendor '{vendor_id}' not found.")

    cr = ChangeRequest(
        action="vendors.shutdown",
        entity_type="vendor",
        entity_id=vendor_id,
        payload={
            "vendor_id": vendor_id,
            "replacement_vendor_id": req.replacement_vendor_id,
            "from_time": req.from_time.isoformat() if req.from_time else None,
            "dispatch_notifications": req.dispatch_notifications,
        },
        reason=req.reason,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(cr, session)
    if res.status == "REJECTED":
        msg = "; ".join(v.message for v in res.violations)
        raise FestOSError(msg or "Vendor shutdown rejected.", code="CONSTRAINT_VIOLATION", status_code=422)

    data = dict(res.data or {"status": "APPLIED"})
    data["change_set_id"] = res.change_set_id
    return data


def get_vendor_compliance_overview(session: Session) -> Dict[str, Any]:
    """Get full compliance breakdown and menu-label mismatches."""
    vendors = session.exec(select(Vendor)).all()
    vendor_reports: List[Dict[str, Any]] = []
    all_flags: List[Dict[str, Any]] = []

    for v in vendors:
        exp_date = parse_expiry_date(v.hygiene_certificate_expiry)
        validity = get_certificate_validity_status(exp_date)

        rep = {
            "id": v.id,
            "name": v.name,
            "certificate_expiry": v.hygiene_certificate_expiry,
            "validity_period": validity,
            "capacity": v.capacity,
        }
        if validity == "EXPIRED":
            rep["capacity_allowed"] = 0
        elif validity == "EXPIRES_DURING_FESTIVAL":
            rep["capacity_allowed_before_expiry"] = v.capacity
            rep["capacity_allowed_after_expiry"] = 0
        else:
            rep["capacity_allowed"] = v.capacity

        vendor_reports.append(rep)

        flags = verify_menu_labels(v.id, v.name, v.menu_description, v.dietary_options)
        all_flags.extend(flags)

    return {
        "vendors": vendor_reports,
        "menu_mismatches": all_flags,
    }


def generate_vendor_coverage_csv(session: Session) -> str:
    """Generate vendor_coverage.csv report string."""
    participants = session.exec(select(Participant)).all()
    vendors = session.exec(select(Vendor)).all()
    meal_slots = session.exec(select(MealSlot)).all()
    assignments = session.exec(select(VendorAssignment)).all()

    matrix_res = evaluate_dietary_matrix(
        participants=participants,
        vendors=vendors,
        meal_slots=meal_slots,
        assignments=assignments,
        target_date=date(2026, 10, 31),
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Meal Slot",
        "Dietary Category",
        "Confirmed Demand",
        "Max Demand (with UNKNOWN)",
        "Valid Capacity",
        "Deficit",
        "Zero Coverage Alert",
        "Active Vendors",
    ])
    for row in matrix_res["matrix"]:
        writer.writerow([
            row["date"],
            row["meal_slot"],
            row["category"],
            row["demand_confirmed"],
            row["demand_max_with_unknown"],
            row["valid_capacity"],
            row["deficit"],
            "YES" if row["is_zero_coverage"] else "NO",
            "; ".join(row["active_vendors"]),
        ])
    return output.getvalue()


def generate_vendor_compliance_csv(session: Session) -> str:
    """Generate vendor_compliance.csv report string."""
    vendors = session.exec(select(Vendor)).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Vendor ID",
        "Vendor Name",
        "Hygiene Expiry",
        "Validity Status",
        "Capacity",
        "Menu Description",
        "Declared Options",
        "Menu Label Flags",
    ])
    for v in vendors:
        exp_date = parse_expiry_date(v.hygiene_certificate_expiry)
        validity = get_certificate_validity_status(exp_date)
        flags = verify_menu_labels(v.id, v.name, v.menu_description, v.dietary_options)
        flag_summary = "; ".join(f["message"] for f in flags) if flags else "COMPLIANT"
        writer.writerow([
            v.id,
            v.name,
            v.hygiene_certificate_expiry,
            validity,
            v.capacity,
            v.menu_description,
            v.dietary_options,
            flag_summary,
        ])
    return output.getvalue()
