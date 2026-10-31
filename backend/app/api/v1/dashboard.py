# OWNER: P1
from typing import Any, Dict, Optional

from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.dashboard import service as dashboard_service
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=Envelope[Dict[str, Any]])
def get_metrics(
    bypass_cache: bool = Query(False, description="Bypass cache and force recalculation"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Aggregates every module's public.summary() into festival-wide KPI metrics with short-TTL cache and role filtering."""
    data = dashboard_service.get_metrics(
        session=session,
        actor_role=actor.role,
        bypass_cache=bypass_cache,
    )
    return Envelope(data=data, meta={"role": actor.role})


@router.get("/attention", response_model=Envelope[Dict[str, Any]])
def get_attention_queue(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return"),
    min_severity: Optional[int] = Query(None, ge=1, le=4, description="Filter by minimum severity level"),
    module: Optional[str] = Query(None, description="Filter by module slug"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns deduplicated, prioritized attention queue ranked strictly by Severity x Urgency x People Affected using core.scoring."""
    data = dashboard_service.get_attention_queue(
        session=session,
        limit=limit,
        min_severity=min_severity,
        module=module,
    )
    return Envelope(data=data)


@router.get("/heatmap", response_model=Envelope[Dict[str, Any]])
def get_risk_heatmap(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns 2D Severity x Time-to-Impact risk heatmap cells with people affected, criticality, uncertainty, and top contributors."""
    data = dashboard_service.get_risk_heatmap(session=session)
    return Envelope(data=data)


@router.post("/attention/{id}/snooze", response_model=Envelope[Dict[str, Any]])
def snooze_attention_item(
    id: str,
    body: Optional[Dict[str, Any]] = None,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Snooze or acknowledge an attention queue item with operational rationale."""
    reason = (body or {}).get("reason", "Acknowledged in executive console")
    minutes = (body or {}).get("minutes", 60)
    acknowledged = (body or {}).get("acknowledged", False)
    return Envelope(
        data={
            "id": id,
            "status": "ACKNOWLEDGED" if acknowledged else "SNOOZED",
            "snoozed_minutes": minutes,
            "actor": actor.name,
            "reason": reason,
        }
    )

