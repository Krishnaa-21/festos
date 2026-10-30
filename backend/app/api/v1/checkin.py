# OWNER: P2
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_actor
from app.models.participants import Participant
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/board", response_model=Envelope[Dict[str, Any]])
def get_checkin_board(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Arrival desk board summarizing arrivals, checkin statuses, and pending counts."""
    participants = session.exec(select(Participant)).all()

    expected = sum(1 for p in participants if p.status == "EXPECTED")
    arrived = sum(1 for p in participants if p.status == "ARRIVED")
    checked_in = sum(1 for p in participants if p.status == "CHECKED_IN")

    return Envelope(
        data={
            "counts": {
                "total_participants": len(participants),
                "expected": expected,
                "arrived": arrived,
                "checked_in": checked_in,
            },
            "recent_checkins": [
                {
                    "participant_id": p.id,
                    "name": p.name,
                    "contingent_id": p.contingent_id,
                    "status": p.status,
                }
                for p in participants
                if p.status == "CHECKED_IN"
            ][:10],
        }
    )
