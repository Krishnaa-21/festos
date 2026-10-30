# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.engines.premortem.disruptions import (
    find_single_points_of_failure,
    run_seeded_multi_disruptions,
    run_targeted_disruption,
)
from app.engines.premortem.resilience import calculate_resilience_score
from app.engines.premortem.timeline import generate_hourly_timeline
from app.models.change import Scenario


def get_timeline(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    step_hours: int = 1,
) -> Dict[str, Any]:
    """Retrieves hourly pre-mortem operational scrubber across the festival window."""
    return generate_hourly_timeline(session, start_time, end_time, step_hours)


def run_disruption(
    session: Session,
    disruption_type: str,
    target_entity_id: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Runs a targeted disruption simulation in an isolated scenario sandbox."""
    return run_targeted_disruption(session, disruption_type, target_entity_id, parameters)


def run_multi_disruptions(
    session: Session,
    seed: int = 42,
    disruption_count: int = 3,
    disruption_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Runs seeded multi-disruption Monte Carlo / combinatorial stress test in scenario sandboxes."""
    return run_seeded_multi_disruptions(session, seed, disruption_count, disruption_types)


def get_resilience_analysis(session: Session) -> Dict[str, Any]:
    """Retrieves operational resilience score and component breakdown."""
    return calculate_resilience_score(session)


def get_spofs(session: Session) -> Dict[str, Any]:
    """Identifies and returns all Single Points of Failure."""
    spofs = find_single_points_of_failure(session)
    return {
        "total_spofs": len(spofs),
        "spofs": spofs,
    }


def list_premortem_scenarios(session: Session) -> Dict[str, Any]:
    """Returns history of pre-mortem simulation runs."""
    scenarios = session.exec(select(Scenario).order_by(Scenario.created_at.desc())).all()
    prem_scenarios = [
        {
            "scenario_id": s.id,
            "name": s.name,
            "description": s.description,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "recorded_actions_count": len(s.recorded_actions or []),
        }
        for s in scenarios
        if "premortem" in str(s.name or "").lower() or "disruption" in str(s.description or "").lower()
    ]
    return {
        "total_scenarios": len(prem_scenarios),
        "scenarios": prem_scenarios,
    }
