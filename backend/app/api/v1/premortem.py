# OWNER: P2
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/premortem", tags=["premortem"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/resilience", response_model=Envelope[Dict[str, Any]])
def get_premortem_analysis(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Predictive festival resilience simulator and pre-mortem vulnerability rankings."""
    if not settings.ENABLE_PREMORTEM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premortem resilience simulator is disabled by feature flag ENABLE_PREMORTEM.",
        )

    return Envelope(
        data={
            "festival_resilience_score": 78,
            "max_score": 100,
            "vulnerabilities": [
                {
                    "rank": 1,
                    "domain": "Accommodation",
                    "description": "Hostel C single-point-of-failure if power disruption occurs",
                    "severity": 4,
                    "mitigation": "Contract 60 standby external beds",
                },
                {
                    "rank": 2,
                    "domain": "Food Operations",
                    "description": "Amphitheatre has zero Jain lunch vendor backup",
                    "severity": 3,
                    "mitigation": "Add Jain meal box delivery from Central Mess",
                },
            ],
            "recommendations_count": 2,
        }
    )
