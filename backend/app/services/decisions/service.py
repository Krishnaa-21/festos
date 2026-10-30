# OWNER: P1
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session, col, select

from app.core import decision_log
from app.models.audit import Override
from app.models.decisions import DecisionCard


def list_decisions(
    session: Session,
    module: Optional[str] = None,
    approver: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Lists recorded decision cards with filtering and pagination."""
    query = select(DecisionCard).order_by(col(DecisionCard.approved_at).desc())

    if module:
        query = query.where(DecisionCard.module == module)
    if approver:
        query = query.where(
            (col(DecisionCard.approved_by).ilike(f"%{approver}%"))
        )

    all_cards = session.exec(query).all()

    # Filter date range if specified
    if from_date:
        try:
            f_dt = datetime.fromisoformat(from_date)
            all_cards = [c for c in all_cards if c.approved_at and c.approved_at >= f_dt]
        except Exception:
            pass
    if to_date:
        try:
            t_dt = datetime.fromisoformat(to_date)
            all_cards = [c for c in all_cards if c.approved_at and c.approved_at <= t_dt]
        except Exception:
            pass

    total = len(all_cards)
    start_idx = (page - 1) * page_size
    paged = all_cards[start_idx : start_idx + page_size]

    items = []
    for c in paged:
        items.append({
            "id": c.id,
            "module": c.module,
            "decision_type": c.decision_type,
            "title": c.title,
            "summary": c.summary,
            "cost_impact_inr": c.cost_impact_inr,
            "people_affected": c.people_affected,
            "approved_by": c.approved_by,
            "approved_at": c.approved_at.isoformat() if c.approved_at else None,
            "override_id": c.override_id,
        })

    return {
        "decisions": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_decision(session: Session, decision_id: str) -> Optional[Dict[str, Any]]:
    """Returns full details of a specific decision card."""
    card = session.get(DecisionCard, decision_id)
    if not card:
        return None

    override_details = None
    if card.override_id:
        ovr = session.get(Override, card.override_id)
        if ovr:
            override_details = {
                "id": ovr.id,
                "constraint_code": ovr.constraint_code,
                "reason": ovr.reason,
                "approved_by": ovr.approved_by,
                "risk_level": ovr.risk_level,
            }

    return {
        "id": card.id,
        "module": card.module,
        "decision_type": card.decision_type,
        "title": card.title,
        "summary": card.summary,
        "why": card.why,
        "hard_constraints_satisfied": card.hard_constraints_satisfied or [],
        "soft_constraints_relaxed": card.soft_constraints_relaxed or [],
        "alternatives_rejected": card.alternatives_rejected or [],
        "cost_impact_inr": card.cost_impact_inr,
        "people_affected": card.people_affected,
        "approved_by": card.approved_by,
        "approved_at": card.approved_at.isoformat() if card.approved_at else None,
        "override_id": card.override_id,
        "override_details": override_details,
        "entity_refs": card.entity_refs or [],
    }


def get_why_explanation(session: Session, decision_id: str) -> Optional[Dict[str, Any]]:
    """One-click explainability breakdown for a decision."""
    card = session.get(DecisionCard, decision_id)
    if not card:
        return None

    return {
        "decision_id": card.id,
        "title": card.title,
        "explanation": card.why,
        "hard_constraints_satisfied": card.hard_constraints_satisfied or [],
        "soft_constraints_relaxed": card.soft_constraints_relaxed or [],
        "alternatives_rejected": card.alternatives_rejected or [],
        "cost_impact_inr": card.cost_impact_inr,
        "people_affected": card.people_affected,
        "approver": card.approved_by,
        "timestamp": card.approved_at.isoformat() if card.approved_at else None,
    }


def create_decision(session: Session, payload: Dict[str, Any], actor_id: Optional[str] = None) -> DecisionCard:
    """Creates a new decision card record."""
    return decision_log.add(
        session=session,
        module=payload.get("module", "operations"),
        decision_type=payload.get("decision_type", "GENERAL_DECISION"),
        title=payload.get("title", "Operational Decision"),
        summary=payload.get("summary", ""),
        why=payload.get("why", ""),
        hard_constraints_satisfied=payload.get("hard_constraints_satisfied"),
        soft_constraints_relaxed=payload.get("soft_constraints_relaxed"),
        alternatives_rejected=payload.get("alternatives_rejected"),
        cost_impact_inr=float(payload.get("cost_impact_inr", 0.0)),
        people_affected=int(payload.get("people_affected", 0)),
        approved_by=actor_id or payload.get("approved_by") or "SYSTEM",
        override_id=payload.get("override_id"),
        entity_refs=payload.get("entity_refs"),
    )
