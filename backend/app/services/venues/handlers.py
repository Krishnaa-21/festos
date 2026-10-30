# OWNER: P1
import logging
from typing import Any, Dict, List

from sqlmodel import Session

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.ops import Venue
from app.schemas.common import Violation

logger = logging.getLogger("festos.venues.handlers")


@register_change_handler("venue.create")
class VenueCreateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        if not p.get("name"):
            return [Violation(code="MISSING_NAME", severity=3, hard=True, message="Venue name is required")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        v = Venue(
            id=req.entity_id,
            name=p["name"],
            code=p.get("code", req.entity_id),
            building=p.get("building", "CAMPUS"),
            capacity=int(p.get("capacity", 100)),
            availability_windows=p.get("availability_windows"),
            indoor_outdoor=p.get("indoor_outdoor", "indoor"),
            accessible=p.get("accessible", True),
            setup_time_min=int(p.get("setup_time_min", 15)),
            teardown_time_min=int(p.get("teardown_time_min", 15)),
            feature_tags=p.get("feature_tags", []),
            status="AVAILABLE",
            created_at=now(),
            updated_at=now(),
        )
        session.add(v)
        session.flush()
        return v.model_dump(mode="json")


@register_change_handler("venue.update")
class VenueUpdateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        v = session.get(Venue, req.entity_id)
        if not v:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Venue {req.entity_id} not found")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        v = session.get(Venue, req.entity_id)
        return v.model_dump(mode="json") if v else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        v = session.get(Venue, req.entity_id)
        p = req.payload
        for k, val in p.items():
            if hasattr(v, k) and k not in ("id", "created_at"):
                setattr(v, k, val)
        v.version += 1
        v.updated_at = now()
        session.add(v)
        session.flush()
        return v.model_dump(mode="json")
