# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.db import get_session
from app.core.deps import require_permission
from app.schemas.common import Actor, Envelope
from app.schemas.food import FoodCoverageResponseData, MealSlotSchema
from app.services.food.service import (
    get_food_compliance_flags,
    get_food_coverage,
    list_meal_slots,
)
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

router = APIRouter(prefix="/food", tags=["Food Operations"])


@router.get("/coverage", response_model=Envelope[FoodCoverageResponseData])
def get_food_coverage_endpoint(
    date: Optional[str] = Query(None, description="Target festival date (YYYY-MM-DD), defaults to 2026-10-31"),
    meal_slot: Optional[str] = Query(None, description="Filter by slot (BREAKFAST, LUNCH, SNACKS, DINNER, LATE_NIGHT)"),
    venue_id: Optional[str] = Query(None, description="Filter by venue"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("food:read")),
):
    """Return 3D dietary coverage matrix (category x meal_slot x venue) with demand range for UNKNOWN."""
    res = get_food_coverage(
        session=session,
        date_str=date,
        meal_slot=meal_slot,
        venue_id=venue_id,
    )
    return Envelope(data=res)


@router.get("/compliance", response_model=Envelope[Dict[str, Any]])
@router.get("/compliance-flags", response_model=Envelope[Dict[str, Any]])
def get_food_compliance_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("food:read")),
):
    """Return all menu-label mismatches and unverified dietary claims detected across menus."""
    res = get_food_compliance_flags(session)
    return Envelope(data=res)


@router.get("/slots", response_model=Envelope[List[MealSlotSchema]])
@router.get("/meal-slots", response_model=Envelope[List[MealSlotSchema]])
def list_meal_slots_endpoint(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("food:read")),
):
    """List all configured festival meal slots and vendor capacity distribution."""
    res = list_meal_slots(session=session, date_str=date)
    return Envelope(data=res)
