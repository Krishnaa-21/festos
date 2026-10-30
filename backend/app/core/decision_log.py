# OWNER: P1
import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from app.core.clock import now
from app.models.decisions import DecisionCard

logger = logging.getLogger("festos.core.decision_log")


def add(
    session: Session,
    module: str,
    decision_type: str,
    title: str,
    summary: str,
    why: str,
    hard_constraints_satisfied: Optional[List[str]] = None,
    soft_constraints_relaxed: Optional[List[Dict[str, Any]]] = None,
    alternatives_rejected: Optional[List[Dict[str, Any]]] = None,
    cost_impact_inr: float = 0.0,
    people_affected: int = 0,
    approved_by: Optional[str] = None,
    override_id: Optional[str] = None,
    entity_refs: Optional[List[Dict[str, Any]]] = None,
) -> DecisionCard:
    """Helper to record an explainable decision card across festival modules.

    Standardizes transparent reason logging, constraint tracking, and rejected alternatives.
    """
    card = DecisionCard(
        module=module,
        decision_type=decision_type,
        title=title,
        summary=summary,
        why=why,
        hard_constraints_satisfied=hard_constraints_satisfied or [],
        soft_constraints_relaxed=soft_constraints_relaxed or [],
        alternatives_rejected=alternatives_rejected or [],
        cost_impact_inr=cost_impact_inr,
        people_affected=people_affected,
        approved_by=approved_by or "SYSTEM",
        approved_at=now(),
        override_id=override_id,
        entity_refs=entity_refs or [],
    )
    session.add(card)
    session.flush()
    logger.info(f"Recorded decision card [{card.id}] for module '{module}': {title}")
    return card


# Convenience alias for handlers
add_decision_card = add

