# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.core.change_service import ChangeRequest
from app.core.registry import register_impact_hook
from app.engines.impact.graph import _normalize_type, build_impact_graph, get_entity_subgraph
from app.schemas.common import Actor
from app.schemas.impact import ImpactAnalyzeRequest, ImpactGraphResponse, ImpactReport

logger = logging.getLogger("festos.services.impact")


def analyze_change(session: Session, req: ImpactAnalyzeRequest, actor: Optional[Actor] = None) -> ImpactReport:
    """Preview downstream blast radius and consequences of any proposed change without applying it (Task 1)."""
    norm_type = _normalize_type(req.entity_type)
    change_req = ChangeRequest(
        action=req.action,
        entity_type=norm_type,
        entity_id=req.entity_id,
        payload=req.effective_payload,
        actor=actor or Actor(id="system_impact_analyzer", name="Impact Engine", role="FESTIVAL_DIRECTOR"),
    )
    return build_impact_graph(session, change_req)


def get_entity_graph(session: Session, entity_str: str, max_depth: int = 3) -> ImpactGraphResponse:
    """Build directed graph node-and-edge response for GET /impact/graph?entity=."""
    if ":" in entity_str:
        entity_type, entity_id = entity_str.split(":", 1)
    else:
        entity_type, entity_id = "resource", entity_str

    return get_entity_subgraph(session, entity_type=entity_type, entity_id=entity_id, max_depth=max_depth)


def incident_impact_hook(req: ChangeRequest, apply_result: Dict[str, Any], session: Session) -> Dict[str, Any]:
    """Hook registered with core.change_service to attach downstream blast radius to any applied change."""
    try:
        report = build_impact_graph(session, req)
        return {
            "blast_radius": {
                "nodes_count": len(report.nodes_flat),
                "people_affected": report.total_people_affected,
                "counts_by_type": report.counts_by_type,
                "severities": report.severities,
            }
        }
    except Exception as e:
        logger.debug(f"Impact hook non-fatal error: {e}")
        return {"blast_radius": {"nodes_count": 0, "people_affected": 0}}


# Register the impact hook automatically
register_impact_hook(incident_impact_hook)
