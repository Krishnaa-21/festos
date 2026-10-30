# OWNER: P2
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.engines.vendors.compliance import verify_menu_labels
from app.engines.vendors.coverage import evaluate_dietary_matrix
from app.models.participants import Participant
from app.models.vendors import MealSlot, Vendor, VendorAssignment
from app.schemas.food import (
    DietaryCoverageSummary,
    FoodCoverageResponseData,
    MealSlotSchema,
    MenuLabelMismatchFlag,
)

logger = logging.getLogger("festos.services.food")


def get_food_coverage(
    session: Session,
    date_str: Optional[str] = None,
    meal_slot: Optional[str] = None,
    venue_id: Optional[str] = None,
) -> FoodCoverageResponseData:
    """Calculate and return 3D dietary coverage matrix."""
    target_date = date(2026, 10, 31)
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    participants = session.exec(select(Participant)).all()
    vendors = session.exec(select(Vendor)).all()
    meal_slots = session.exec(select(MealSlot)).all()
    assignments = session.exec(select(VendorAssignment)).all()

    matrix_data = evaluate_dietary_matrix(
        participants=participants,
        vendors=vendors,
        meal_slots=meal_slots,
        assignments=assignments,
        target_date=target_date,
    )

    rows = matrix_data["matrix"]
    if meal_slot:
        rows = [r for r in rows if r["meal_slot"].upper() == meal_slot.upper()]

    summary_obj = DietaryCoverageSummary(**matrix_data["summary"])

    return FoodCoverageResponseData(
        date=matrix_data["date"],
        categories=matrix_data["categories"],
        meal_slots=matrix_data["meal_slots"],
        summary=summary_obj,
        matrix=rows,
        critical_alerts=matrix_data["critical_alerts"],
    )


def get_food_compliance_flags(session: Session) -> Dict[str, Any]:
    """Return all menu-label mismatches detected across vendors."""
    vendors = session.exec(select(Vendor)).all()
    all_flags: List[MenuLabelMismatchFlag] = []

    for v in vendors:
        flags = verify_menu_labels(v.id, v.name, v.menu_description, v.dietary_options)
        for f in flags:
            all_flags.append(MenuLabelMismatchFlag(**f))

    return {"flags": all_flags, "total": len(all_flags)}


def list_meal_slots(session: Session, date_str: Optional[str] = None) -> List[MealSlotSchema]:
    query = select(MealSlot)
    if date_str:
        query = query.where(MealSlot.date == date_str)
    slots = session.exec(query.order_by(MealSlot.date, MealSlot.start_time)).all()

    assignments = session.exec(select(VendorAssignment)).all()
    slot_counts: Dict[str, int] = {}
    for a in assignments:
        slot_counts[a.meal_slot_id] = slot_counts.get(a.meal_slot_id, 0) + 1

    return [
        MealSlotSchema(
            id=s.id,
            name=s.name,
            date=s.date,
            start_time=s.start_time,
            end_time=s.end_time,
            assigned_vendors_count=slot_counts.get(s.id, 0),
        )
        for s in slots
    ]
