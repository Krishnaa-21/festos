# OWNER: P1
from typing import Any, Dict, Optional

from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.scenarios import service as scenarios_service
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class CreateScenarioBody(BaseModel):
    name: str
    description: Optional[str] = None


class ScenarioActionBody(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    payload: Dict[str, Any]
    reason: Optional[str] = None


class CommitScenarioBody(BaseModel):
    reason: Optional[str] = None


class SimulateIncidentBody(BaseModel):
    incident_type: str
    target_id: str
    severity: int = 4
    details: Optional[str] = None


@router.post("", response_model=Envelope[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
def create_scenario(
    body: CreateScenarioBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Forks the live production database into an isolated sandbox environment."""
    data = scenarios_service.create_scenario(
        session=session,
        name=body.name,
        description=body.description,
        actor_id=actor.id,
    )
    return Envelope(data=data)


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_scenarios(
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Lists active, committed, and discarded simulation scenarios."""
    data = scenarios_service.list_scenarios(
        session=session,
        status_filter=status,
    )
    return Envelope(data=data)


@router.get("/{id}", response_model=Envelope[Dict[str, Any]])
def get_scenario(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns scenario details, metadata, and recorded actions."""
    data = scenarios_service.get_scenario(session, id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Scenario '{id}' not found")
    return Envelope(data=data)


@router.post("/{id}/actions", response_model=Envelope[Dict[str, Any]])
def execute_scenario_action(
    id: str,
    body: ScenarioActionBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Executes a ChangeService mutation inside the isolated scenario sandbox."""
    try:
        data = scenarios_service.execute_action_in_scenario(
            session=session,
            scenario_id=id,
            action=body.action,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            payload=body.payload,
            reason=body.reason,
            actor=actor,
        )
        return Envelope(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}/compare", response_model=Envelope[Dict[str, Any]])
def compare_scenario(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Computes metrics diff comparing live production state versus the simulated sandbox state."""
    try:
        data = scenarios_service.compare_scenario(session, id)
        return Envelope(data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{id}/commit", response_model=Envelope[Dict[str, Any]])
def commit_scenario(
    id: str,
    body: CommitScenarioBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Replays all recorded sandbox changes onto the live production database."""
    try:
        data = scenarios_service.commit_scenario(
            session=session,
            scenario_id=id,
            actor=actor,
            reason=body.reason,
        )
        warnings = data.pop("warnings", [])
        return Envelope(data=data, warnings=warnings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/discard", response_model=Envelope[Dict[str, Any]])
def discard_scenario(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Discards a scenario and deletes its sandbox storage."""
    data = scenarios_service.discard_scenario(session, id)
    return Envelope(data=data)


@router.post("/{id}/simulate-incident", response_model=Envelope[Dict[str, Any]])
def simulate_incident(
    id: str,
    body: SimulateIncidentBody,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Incident simulation adapter allowing Prompt 14 drills to test crises in a sandbox."""
    try:
        data = scenarios_service.simulate_incident_in_scenario(
            session=session,
            scenario_id=id,
            incident_type=body.incident_type,
            target_id=body.target_id,
            severity=body.severity,
            details=body.details,
            actor=actor,
        )
        return Envelope(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
