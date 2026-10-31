# OWNER: P2
import uuid
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


_PREVENTIVE_ACTIONS: List[Dict[str, Any]] = [
    {
        "id": "act_prev_01",
        "title": "Contract Lakeview Inn 40-Bed Contingency Overflow Block",
        "category": "Accommodation",
        "urgency": "IMMEDIATE",
        "projectedRiskReductionPct": 35,
        "status": "PENDING",
        "actionLabel": "Contract Hotel Block",
        "actionRoute": "/accommodation",
    },
    {
        "id": "act_prev_02",
        "title": "Standby Certified Jain Caterer (Green Gourmet Express)",
        "category": "Food",
        "urgency": "IMMEDIATE",
        "projectedRiskReductionPct": 25,
        "status": "PENDING",
        "actionLabel": "Engage Standby Caterer",
        "actionRoute": "/food",
    },
    {
        "id": "act_prev_03",
        "title": "Reserve Secondary Diesel Genset for Main Auditorium Stage",
        "category": "Power",
        "urgency": "BEFORE_DAY_2",
        "projectedRiskReductionPct": 20,
        "status": "PENDING",
        "actionLabel": "Assign Secondary Genset",
        "actionRoute": "/events",
    },
    {
        "id": "act_prev_04",
        "title": "Pre-Authorize Midnight Shuttle Loop for Delayed Trains",
        "category": "Transport",
        "urgency": "BEFORE_DAY_2",
        "projectedRiskReductionPct": 15,
        "status": "PENDING",
        "actionLabel": "Roster Night Drivers",
        "actionRoute": "/transport",
    },
    {
        "id": "act_prev_05",
        "title": "Roster Floating Security Lead for North Gate Peak Egress",
        "category": "Staff",
        "urgency": "OPTIONAL",
        "projectedRiskReductionPct": 10,
        "status": "PENDING",
        "actionLabel": "Assign Floating Lead",
        "actionRoute": "/staff",
    },
]


@router.get("/spofs", response_model=Envelope[Dict[str, Any]])
@router.get("/spof", response_model=Envelope[Dict[str, Any]])
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
    raw_spofs = res.get("spofs", [])
    formatted_items = []
    for s in raw_spofs:
        par = s.get("people_at_risk", 50)
        formatted_items.append({
            "id": s.get("entity_id", str(uuid.uuid4())[:8]),
            "name": s.get("name", "Critical Resource"),
            "component": s.get("entity_type", "INFRASTRUCTURE"),
            "vulnerability": s.get("impact_summary", "Failure cascade risk"),
            "failureImpact": s.get("impact_summary", "Downstream disruption"),
            "peopleAtRisk": par,
            "resilienceTier": "CRITICAL" if par > 100 else "HIGH" if par > 50 else "MODERATE",
            "recommendedMitigation": s.get("preventive_recommendation", "Establish operational standby redundancy"),
            "mitigationRoute": "/accommodation" if "HOSTEL" in str(s.get("entity_type", "")) else "/food",
        })
    return Envelope(data={"items": formatted_items, "total": len(formatted_items), "spofs": raw_spofs})


@router.get("/preventive", response_model=Envelope[Dict[str, Any]])
def get_preventive_actions(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns catalog of preemptive mitigation actions for high-risk single points of failure."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )
    return Envelope(data={"items": _PREVENTIVE_ACTIONS, "total": len(_PREVENTIVE_ACTIONS)})


@router.post("/preventive/{id}/execute", response_model=Envelope[Dict[str, Any]])
def execute_preventive_action(
    id: str,
    body: Optional[Dict[str, Any]] = None,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Execute a preventive risk mitigation action before festival kickoff."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )
    for act in _PREVENTIVE_ACTIONS:
        if act["id"] == id:
            act["status"] = "EXECUTED"
            return Envelope(data={"action": act, "status": "EXECUTED", "executed_by": actor.name})
    return Envelope(data={"id": id, "status": "EXECUTED", "executed_by": actor.name})


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
