# OWNER: P1
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import get_actor
from app.core.registry import iter_public_modules
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/impact", tags=["impact"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/blast-radius", response_model=Envelope[Dict[str, Any]])
def get_blast_radius(
    entity_type: str = Query("venue", description="Entity type: venue, hostel, event, participant"),
    entity_id: str = Query("V01", description="Entity ID"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Calculates cross-module downstream blast radius of a change on entity_type:entity_id."""
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
