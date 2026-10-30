# OWNER: P2
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now as clock_now
from app.engines.vendors.compliance import verify_menu_labels
from app.engines.vendors.coverage import evaluate_dietary_matrix
from app.models.participants import Participant
from app.models.vendors import MealSlot, Vendor, VendorAssignment
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return food operations summary as of `now`."""
    if now is None:
        now = clock_now()
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
    s = matrix_res["summary"]
    return {
        "module": "food",
        "status": "OPERATIONAL",
        "on_site_headcount": s["on_site_headcount"],
        "valid_capacity": s["valid_aggregate_capacity"],
        "shortfall": s["aggregate_shortfall"],
        "zero_coverage_count": len(s["zero_coverage_categories"]),
        "unknown_dietary_count": s["unknown_dietary_headcount"],
    }


def risks(session: Session, now: Optional[datetime] = None) -> List[RiskItem]:
    """Return food and dietary risks evaluated as of `now`."""
    if now is None:
        now = clock_now()
    risk_list: List[RiskItem] = []
    vendors = session.exec(select(Vendor)).all()

    for v in vendors:
        flags = verify_menu_labels(v.id, v.name, v.menu_description, v.dietary_options)
        for f in flags:
            risk_list.append(
                RiskItem(
                    id=f["id"],
                    module="food",
                    kind=f["flag_type"],
                    title=f"Menu Label Mismatch: {v.name} ({f['menu_keyword']})",
                    severity=3,
                    hours_to_impact=6.0,
                    people_affected=v.capacity or 100,
                    uncertainty=0.2,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="vendor", id=v.id, label=v.name)],
                    action={"label": "Audit Menu", "route": "/food", "api": "/api/v1/food/compliance"},
                    explanation=f["message"],
                )
            )

    return risk_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by food/dietary entity."""
    deps: List[EntityRef] = []
    if entity_type == "meal_slot":
        assignments = session.exec(
            select(VendorAssignment).where(VendorAssignment.meal_slot_id == entity_id)
        ).all()
        for a in assignments:
            deps.append(EntityRef(type="vendor", id=a.vendor_id, label=f"Vendor {a.vendor_id}"))
            if a.venue_id:
                deps.append(EntityRef(type="venue", id=a.venue_id, label=f"Venue {a.venue_id}"))
    return deps
