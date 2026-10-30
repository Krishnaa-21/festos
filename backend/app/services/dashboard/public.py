# OWNER: P1
"""Public contract for Dashboard module.

Exposes summary metrics, detects stale cache anomalies, and surfaces scenarios awaiting operational decisions.
"""
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.change import Scenario
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity
from app.services.dashboard import service as dashboard_service


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return dashboard KPI summary as of `now`."""
    is_cached = dashboard_service._metrics_cache is not None
    cache_age_sec = (
        (now - dashboard_service._cache_timestamp).total_seconds()
        if dashboard_service._cache_timestamp
        else None
    )

    scenarios_draft_count = len(
        session.exec(select(Scenario).where(Scenario.status == "DRAFT")).all()
    )

    return {
        "module": "dashboard",
        "status": "OPERATIONAL",
        "metrics_cached": is_cached,
        "cache_age_seconds": round(cache_age_sec, 1) if cache_age_sec is not None else None,
        "scenarios_awaiting_decision": scenarios_draft_count,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`: stale caches and scenarios awaiting decisions."""
    items: List[RiskItem] = []

    # 1. Stale Metrics Cache Risk
    if dashboard_service._cache_timestamp is not None:
        age_sec = (now - dashboard_service._cache_timestamp).total_seconds()
        if age_sec > 60:  # Older than 4x TTL
            items.append(
                RiskItem(
                    id="risk_dashboard_stale_cache",
                    module="dashboard",
                    kind="STALE_METRICS_CACHE",
                    title=f"Dashboard metrics cache stale ({int(age_sec)}s old)",
                    severity=Severity.LOW,
                    hours_to_impact=0.5,
                    people_affected=1,
                    uncertainty=0.1,
                    resource_criticality=2,
                    entity_refs=[EntityRef(type="system", id="dashboard_cache", label="Metrics In-Memory Cache")],
                    action=ActionRef(
                        label="Invalidate Cache",
                        route="/dashboard",
                        api="/api/v1/dashboard/metrics?bypass_cache=true",
                    ),
                    explanation="Cache has not refreshed within expected TTL window; downstream decisions may view out-of-date metrics.",
                )
            )

    # 2. Scenarios Awaiting Decision
    draft_scenarios = session.exec(
        select(Scenario).where(Scenario.status == "DRAFT")
    ).all()

    for scn in draft_scenarios:
        action_count = len(scn.recorded_actions or [])
        age_hours = (now - scn.created_at).total_seconds() / 3600.0 if scn.created_at else 0.0
        # Alert if scenario has actions or is older than 6 hours
        if action_count > 0 or age_hours > 6.0:
            items.append(
                RiskItem(
                    id=f"risk_scenario_awaiting_decision_{scn.id}",
                    module="scenarios",
                    kind="SCENARIO_AWAITING_DECISION",
                    title=f"Scenario '{scn.name}' awaiting decision ({action_count} actions recorded)",
                    severity=Severity.MEDIUM if action_count > 0 else Severity.LOW,
                    hours_to_impact=max(1.0, 24.0 - age_hours),
                    people_affected=15 if action_count > 0 else 5,
                    uncertainty=0.1,
                    resource_criticality=3,
                    entity_refs=[EntityRef(type="scenario", id=scn.id, label=scn.name)],
                    action=ActionRef(
                        label="Compare & Review Scenario",
                        route=f"/scenarios/{scn.id}",
                        api=f"/api/v1/scenarios/{scn.id}/compare",
                    ),
                    explanation=f"Sandbox scenario created {age_hours:.1f}h ago has uncommitted mutations. Needs commit or discard.",
                )
            )

    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
