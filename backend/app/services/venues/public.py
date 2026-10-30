# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.events import EventSession
from app.models.ops import Venue
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return venues module KPI summary as of `now`."""
    total_venues = session.exec(select(func.count(Venue.id))).one()
    total_capacity = session.exec(select(func.sum(Venue.capacity))).one() or 0
    indoor_count = session.exec(select(func.count(Venue.id)).where(Venue.indoor_outdoor == "indoor")).one()
    outdoor_count = session.exec(select(func.count(Venue.id)).where(Venue.indoor_outdoor == "outdoor")).one()

    return {
        "module": "venues",
        "total_venues": total_venues,
        "total_capacity": total_capacity,
        "indoor_venues": indoor_count,
        "outdoor_venues": outdoor_count,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active venue risks evaluated as of `now`."""
    return []


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    deps = []
    if entity_type == "venue":
        sessions = session.exec(select(EventSession).where(EventSession.venue_id == entity_id)).all()
        for s in sessions:
            deps.append(EntityRef(type="event_session", id=s.id, label=f"{s.event_name} {s.heat}"))
            deps.append(EntityRef(type="event", id=s.event_id, label=s.event_name))
    return deps
