# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.decisions import DecisionCard
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    cards = session.exec(select(DecisionCard)).all()
    total_cost = sum(c.cost_impact_inr for c in cards)
    total_people = sum(c.people_affected for c in cards)
    return {
        "module": "decisions",
        "status": "OPERATIONAL",
        "total_decisions_logged": len(cards),
        "total_cost_impact_inr": total_cost,
        "total_people_affected": total_people,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    return []


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    deps: List[EntityRef] = []
    if entity_type == "decision_card":
        card = session.get(DecisionCard, entity_id)
        if card and card.override_id:
            deps.append(EntityRef(type="override", id=card.override_id, label=f"Override {card.override_id}"))
    return deps
