# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session

from app.engines.premortem.disruptions import find_single_points_of_failure
from app.engines.premortem.resilience import calculate_resilience_score
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    res = calculate_resilience_score(session)
    spofs = find_single_points_of_failure(session)
    return {
        "module": "premortem",
        "resilience_score": res["festival_resilience_score"],
        "rating": res["rating"],
        "total_spofs": len(spofs),
        "status": "OPERATIONAL",
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now` based on top Single Points of Failure (SPOFs)."""
    spofs = find_single_points_of_failure(session)
    items: List[RiskItem] = []

    for spof in spofs[:5]:
        items.append(
            RiskItem(
                id=f"risk_spof_{spof['entity_id']}",
                module="premortem",
                kind="SPOF",
                severity=Severity.CRITICAL if spof["people_at_risk"] >= 100 else Severity.HIGH,
                people_affected=spof["people_at_risk"],
                title=f"Single Point of Failure: {spof['name']}",
                explanation=spof["impact_summary"],
                hours_to_impact=12.0,
                action=ActionRef(
                    label="View Mitigation",
                    route="/premortem",
                    api=f"/api/v1/premortem/spofs",
                ),
            )
        )
    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
