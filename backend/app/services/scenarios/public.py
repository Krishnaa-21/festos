# OWNER: P1
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.change import Scenario
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    scenarios = session.exec(select(Scenario)).all()
    active_count = sum(1 for s in scenarios if s.status == "DRAFT")
    committed_count = sum(1 for s in scenarios if s.status == "COMMITTED")
    discarded_count = sum(1 for s in scenarios if s.status == "DISCARDED")

    return {
        "module": "scenarios",
        "status": "OPERATIONAL",
        "active_scenarios_count": active_count,
        "committed_scenarios_count": committed_count,
        "discarded_scenarios_count": discarded_count,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    risk_items: List[RiskItem] = []
    scenarios = session.exec(select(Scenario).where(Scenario.status == "DRAFT")).all()

    old_threshold = now - timedelta(hours=24)
    old_drafts = [s for s in scenarios if s.created_at < old_threshold]
    if old_drafts:
        risk_items.append(RiskItem(
            id="risk_stale_scenarios",
            module="scenarios",
            kind="SCENARIO_AWAITING_DECISION",
            title=f"{len(old_drafts)} simulation scenarios are older than 24h awaiting commit or discard",
            severity=Severity.LOW,
            people_affected=0,
            hours_to_impact=24.0,
            uncertainty=0.0,
            resource_criticality=1,
            entity_refs=[EntityRef(type="scenario", id=s.id, label=s.name) for s in old_drafts[:3]],
            action=ActionRef(
                label="Review Scenarios",
                route="/scenarios",
                api="/api/v1/scenarios",
            ),
            explanation="Uncommitted scenarios consume sandbox disk resources and diverge from production state.",
        ))

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
