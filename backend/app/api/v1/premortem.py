# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.premortem.service import (
    get_resilience_analysis,
    get_spofs,
    get_timeline,
    list_premortem_scenarios,
    run_disruption,
    run_multi_disruptions,
)

router = APIRouter(prefix="/premortem", tags=["premortem"])


class RunDisruptionBody(BaseModel):
    disruption_type: str
    target_entity_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class RunMultiDisruptionsBody(BaseModel):
    seed: int = 42
    disruption_count: int = 3
    intensity: str = "HIGH"
    disruption_types: Optional[List[str]] = None


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/resilience", response_model=Envelope[Dict[str, Any]])
def get_premortem_resilience(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Predictive festival resilience simulator and pre-mortem vulnerability rankings."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    res = get_resilience_analysis(session)
    return Envelope(data=res)


@router.get("/timeline", response_model=Envelope[Dict[str, Any]])
def get_hourly_timeline(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    step_hours: int = Query(1, ge=1, le=24),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Hourly scrubber across festival window computing bed occupancy, food demand,
    venue utilization, equipment, volunteers, transport and module risks.
    """
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    timeline_data = get_timeline(session, start_time, end_time, step_hours)
    return Envelope(data=timeline_data)


@router.post("/disruptions/run", response_model=Envelope[Dict[str, Any]])
def run_targeted_disruption_endpoint(
    body: RunDisruptionBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Run a single targeted disruption in an isolated scenario sandbox using the impact engine."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    try:
        res = run_disruption(session, body.disruption_type, body.target_entity_id, body.parameters)
        return Envelope(data=res)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/disruptions/multi-run", response_model=Envelope[Dict[str, Any]])
def run_multi_disruptions_endpoint(
    body: RunMultiDisruptionsBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Run seeded multi-disruption Monte Carlo / combinatorial stress test in scenario sandboxes."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    res = run_multi_disruptions(session, body.seed, body.disruption_count, body.disruption_types)
    return Envelope(data=res)


@router.get("/spofs", response_model=Envelope[Dict[str, Any]])
def get_single_points_of_failure(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns detected Single Points of Failure across all festival resources."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    res = get_spofs(session)
    return Envelope(data=res)


@router.get("/scenarios", response_model=Envelope[Dict[str, Any]])
def get_premortem_scenarios_history(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns history of simulated pre-mortem scenarios."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    res = list_premortem_scenarios(session)
    return Envelope(data=res)
