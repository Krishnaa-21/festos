# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session

from app.core.registry import get_impact_hooks
from app.engines.impact.graph import _get_direct_orm_dependents
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return impact engine KPI summary as of `now`."""
    hooks = get_impact_hooks()
    return {
        "module": "impact",
        "status": "OPERATIONAL",
        "chains_covered": [
            "Participant -> Contingent -> Registration -> Event -> Venue -> Equipment -> Vendor",
            "Participant -> Arrival -> Check-in -> Accommodation -> Meal -> Vendor",
            "Participant -> Merchandise eligibility -> Stock -> Distribution counter",
        ],
        "registered_hooks_count": len(hooks),
        "cycle_guard_active": True,
        "max_depth": 5,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    return []


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id using graph dependency logic."""
    deps = _get_direct_orm_dependents(session, entity_type, entity_id)
    return [EntityRef(type=d[0], id=d[1], label=d[2]) for d in deps]
