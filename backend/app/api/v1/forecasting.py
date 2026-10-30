# OWNER: P2
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/crowd", response_model=Envelope[Dict[str, Any]])
def get_crowd_forecasting(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Predictive analytics and crowd flow forecasting across festival venues."""
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    return Envelope(
        data={
            "peak_crowd_hour": "2026-10-31T17:00:00Z",
            "forecasts": [
                {
                    "venue_id": "V01",
                    "venue_name": "Main Auditorium",
                    "projected_occupancy_pct": 92.5,
                    "risk": "HIGH_CONGESTION",
                },
                {
                    "venue_id": "V02",
                    "venue_name": "Management Block Courtyard",
                    "projected_occupancy_pct": 64.0,
                    "risk": "NORMAL",
                },
            ],
            "total_projected_simultaneous_attendees": 1850,
        }
    )
