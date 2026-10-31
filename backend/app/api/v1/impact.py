# OWNER: P1
from typing import Any, Dict, List

from app.core.db import get_session
from app.core.deps import get_actor
from app.core.rbac import check_permission
from app.core.registry import iter_public_modules
from app.schemas.common import Actor, Envelope
from app.schemas.impact import ImpactAnalyzeRequest, ImpactGraphResponse, ImpactReport
from app.services.impact.service import analyze_change, get_entity_graph
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

router = APIRouter(prefix="/impact", tags=["impact"])


@router.post("/analyze", response_model=Envelope[ImpactReport])
def analyze_proposed_change(
    req: ImpactAnalyzeRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Preview downstream blast radius and consequences without applying change (Task 1)."""
    check_permission(actor, "impact:read")
    report = analyze_change(session=session, req=req, actor=actor)
    return Envelope(data=report)


@router.get("/graph", response_model=Envelope[ImpactGraphResponse])
def get_graph(
    entity: str = Query("hostel:A", description="Entity in format type:id (e.g. hostel:A, venue:VEN-001)"),
    depth: int = Query(3, ge=1, le=5, description="Depth cap (1-5)"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Return directed graph nodes and edges for visualization and traversal (Task 1 & 7)."""
    check_permission(actor, "impact:read")
    graph_resp = get_entity_graph(session, entity_str=entity, max_depth=depth)
    return Envelope(data=graph_resp)


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/blast-radius", response_model=Envelope[Dict[str, Any]])
def get_blast_radius(
    entity_type: str = Query("venue", description="Entity type: venue, hostel, event, participant"),
    entity_id: str = Query("V01", description="Entity ID"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Calculates cross-module downstream blast radius of a change on entity_type:entity_id."""
    check_permission(actor, "impact:read")
    dependents: List[Dict[str, Any]] = []

    for mod_info in iter_public_modules():
        mod = mod_info["module"]
        slug = mod_info["slug"]
        if hasattr(mod, "dependents"):
            try:
                deps = mod.dependents(session, entity_type, entity_id)
                for d in deps:
                    dependents.append({
                        "module": slug,
                        "entity_type": getattr(d, "type", str(d)),
                        "entity_id": getattr(d, "id", str(d)),
                        "label": getattr(d, "label", str(d)),
                    })
            except Exception:
                pass

    return Envelope(
        data={
            "source_entity": {
                "type": entity_type,
                "id": entity_id,
            },
            "downstream_dependents_count": len(dependents),
            "dependents": dependents,
        }
    )
