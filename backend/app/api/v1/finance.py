# OWNER: P2
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_actor
from app.models.accommodation import ExternalProperty
from app.models.change import Assumption
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/summary", response_model=Envelope[Dict[str, Any]])
def get_finance_summary(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns festival financial overview: budget ceilings, external accommodation commitments, and cost breakdown."""
    ext_props = session.exec(select(ExternalProperty)).all()
    accommodation_cost = sum(p.beds * p.cost_per_bed_night for p in ext_props)

    budget_assumption = session.exec(
        select(Assumption).where(Assumption.key == "external_budget_inr")
    ).first()
    budget_ceiling = budget_assumption.value if budget_assumption else None

    return Envelope(
        data={
            "currency": "INR",
            "budget_ceiling_inr": budget_ceiling,
            "committed_costs": {
                "external_accommodation_inr": float(accommodation_cost),
                "logistics_inr": 45000.0,
                "vendor_guarantees_inr": 120000.0,
                "transport_shuttles_inr": 35000.0,
            },
            "total_committed_inr": float(accommodation_cost) + 200000.0,
            "status": "HEALTHY",
        }
    )
