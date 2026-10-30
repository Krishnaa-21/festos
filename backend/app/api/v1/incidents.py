# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest, execute_change
from app.core.clock import now
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.registry import register_change_handler
from app.models.ops import Incident
from app.schemas.common import Actor, Envelope, Violation

router = APIRouter(prefix="/incidents", tags=["incidents"])


class CreateIncidentBody(BaseModel):
    title: str
    severity: int = 2
    category: str = "GENERAL"
    description: str
    reason: Optional[str] = None


@register_change_handler("incident.create")
class IncidentCreateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        payload = req.payload
        inc = Incident(
            title=payload.get("title", "Operational Incident"),
            severity=int(payload.get("severity", 2)),
            category=payload.get("category", "GENERAL"),
            description=payload.get("description", ""),
            status="OPEN",
            reported_by=req.actor.name,
            reported_at=now(),
        )
        session.add(inc)
        session.flush()
        return {"incident_id": inc.id, "title": inc.title, "status": inc.status}


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List operational incidents."""
    query = select(Incident).order_by(Incident.reported_at.desc())
    if status_filter:
        query = query.where(Incident.status == status_filter.upper())
    if severity:
        query = query.where(Incident.severity == severity)

    all_items = session.exec(query).all()
    total = len(all_items)
    start = (page - 1) * page_size
    items = all_items[start : start + page_size]

    return Envelope(
        data={
            "items": [
                {
                    "id": inc.id,
                    "title": inc.title,
                    "severity": inc.severity,
                    "category": inc.category,
                    "description": inc.description,
                    "status": inc.status,
                    "reported_by": inc.reported_by,
                    "reported_at": inc.reported_at.isoformat() if inc.reported_at else None,
                }
                for inc in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("", response_model=Envelope[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
def create_incident(
    body: CreateIncidentBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Log an incident via ChangeService."""
    req = ChangeRequest(
        action="incident.create",
        entity_type="incident",
        entity_id=f"inc_{now().strftime('%Y%m%d%H%M%S')}",
        payload=body.model_dump(),
        reason=body.reason or f"Declared incident: {body.title}",
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())
