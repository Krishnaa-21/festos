# OWNER: P1
import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.errors import FestOSError
from app.engines.scheduling import DEFAULT_VENUE_COMPATIBILITY
from app.models.ops import TravelTime, Venue

logger = logging.getLogger("festos.venues.service")

# Dynamic in-memory or persisted compatibility mapping
_VENUE_COMPATIBILITY_STATE = dict(DEFAULT_VENUE_COMPATIBILITY)


def list_venues(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    indoor_outdoor: Optional[str] = None,
) -> Dict[str, Any]:
    query = select(Venue)
    if indoor_outdoor:
        query = query.where(Venue.indoor_outdoor == indoor_outdoor.lower())

    venues = session.exec(query).all()
    items = [v.model_dump() for v in venues]

    return {
        "items": items,
        "total": len(items),
        "page": page,
        "page_size": page_size,
    }


def get_venue_profile(session: Session, venue_id: str) -> Dict[str, Any]:
    v = session.get(Venue, venue_id)
    if not v:
        raise FestOSError(f"Venue {venue_id} not found", code="NOT_FOUND", status_code=404)
    return v.model_dump()


def get_travel_times(session: Session) -> Dict[str, Any]:
    overrides = session.exec(select(TravelTime)).all()
    return {
        "default_travel_min": 15,
        "overrides": [
            {
                "from_venue_id": o.from_venue_id,
                "to_venue_id": o.to_venue_id,
                "travel_time_min": o.travel_time_min,
            }
            for o in overrides
        ],
    }


def set_travel_time(
    session: Session,
    from_venue_id: str,
    to_venue_id: str,
    travel_time_min: int,
) -> Dict[str, Any]:
    existing = session.exec(
        select(TravelTime).where(
            TravelTime.from_venue_id == from_venue_id,
            TravelTime.to_venue_id == to_venue_id,
        )
    ).first()

    if existing:
        existing.travel_time_min = travel_time_min
        session.add(existing)
    else:
        new_tt = TravelTime(
            from_venue_id=from_venue_id,
            to_venue_id=to_venue_id,
            travel_time_min=travel_time_min,
        )
        session.add(new_tt)

    session.commit()
    return {
        "from_venue_id": from_venue_id,
        "to_venue_id": to_venue_id,
        "travel_time_min": travel_time_min,
    }


def get_compatibility_mapping() -> Dict[str, Any]:
    return {
        "mapping": _VENUE_COMPATIBILITY_STATE,
        "status": "ASSUMED",
        "notes": "Derived from prototype requirements mapping; editable ASSUMED mapping.",
    }


def update_compatibility_mapping(
    requirement_key: str,
    venue_ids: List[str],
) -> Dict[str, Any]:
    _VENUE_COMPATIBILITY_STATE[requirement_key] = venue_ids
    return {
        "requirement_key": requirement_key,
        "venue_ids": venue_ids,
        "status": "ASSUMED",
    }
