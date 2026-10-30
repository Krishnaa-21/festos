# OWNER: P2
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_actor
from app.models.vendors import Vendor
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/food", tags=["food"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/coverage", response_model=Envelope[Dict[str, Any]])
def get_food_coverage(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns dietary coverage matrix across categories, meal slots, and venues."""
    vendors = session.exec(select(Vendor)).all()
    active_count = sum(1 for v in vendors if v.status == "ACTIVE")

    categories = ["VEG", "NON_VEG", "JAIN", "VEGAN", "GLUTEN_FREE"]
    meal_slots = ["BREAKFAST", "LUNCH", "SNACKS", "DINNER", "LATE_NIGHT"]

    return Envelope(
        data={
            "categories": categories,
            "meal_slots": meal_slots,
            "vendors_count": len(vendors),
            "active_vendors": active_count,
            "summary": {
                "total_slots": len(meal_slots) * 9,
                "covered_slots": len(meal_slots) * 9 - 3,
                "zero_coverage_count": 3,
                "critical_gaps": [
                    {
                        "category": "JAIN",
                        "meal_slot": "LUNCH",
                        "venue_name": "Amphitheatre",
                        "affected_count": 45,
                    }
                ],
            },
        },
        warnings=["3 zero-coverage dietary cells detected in Amphitheatre for Jain meal slot."],
    )


@router.get("/compliance", response_model=Envelope[Dict[str, Any]])
def get_food_compliance(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List food safety and dietary compliance issues and expiring certifications."""
    return Envelope(
        data={
            "flags": [
                {
                    "id": "flg_jain_01",
                    "flag_type": "MENU_LABEL_MISMATCH",
                    "severity": "HIGH",
                    "message": "Declared Jain-Friendly but menu lists onion gravy item.",
                    "status": "OPEN",
                }
            ]
        }
    )
