# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.participants import Participant
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    unspecified_arrivals = session.exec(
        select(func.count(Participant.id)).where(Participant.arrival_at == None)
    ).one()
    unspecified_diet = session.exec(
        select(func.count(Participant.id)).where(Participant.diet == "UNKNOWN")
    ).one()

    return {
        "module": "forecasting",
        "data_gaps": {
            "unspecified_arrivals": unspecified_arrivals,
            "unspecified_diet": unspecified_diet,
        },
        "status": "OPERATIONAL",
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now` identifying data gaps that block or distort forecasts."""
    items: List[RiskItem] = []

    unspecified_arrivals = session.exec(
        select(func.count(Participant.id)).where(Participant.arrival_at == None)
    ).one()
    if unspecified_arrivals > 0:
        items.append(
            RiskItem(
                id="risk_fc_arr_gap",
                module="forecasting",
                kind="DATA_GAP",
                severity=Severity.HIGH,
                people_affected=unspecified_arrivals,
                title="Unknown Arrival Times Blocking Queue Forecasting",
                explanation=f"{unspecified_arrivals} participants have missing arrival timestamps, forcing check-in queue and shuttle forecasts to rely on assumption buffers.",
                hours_to_impact=6.0,
                action=ActionRef(
                    label="Verify Arrival Times",
                    route="/unknowns",
                    api="/api/v1/unknowns/ranking",
                ),
            )
        )

    unspecified_diet = session.exec(
        select(func.count(Participant.id)).where(Participant.diet == "UNKNOWN")
    ).one()
    if unspecified_diet > 50:
        items.append(
            RiskItem(
                id="risk_fc_diet_gap",
                module="forecasting",
                kind="DATA_GAP",
                severity=Severity.HIGH,
                people_affected=unspecified_diet,
                title="Unknown Dietary Choices Distorting Catering Forecasts",
                explanation=f"{unspecified_diet} attendees have UNKNOWN dietary preferences, introducing high variance into vendor meal procurement allocations.",
                hours_to_impact=12.0,
                action=ActionRef(
                    label="Verify Diets",
                    route="/unknowns",
                    api="/api/v1/unknowns/ranking",
                ),
            )
        )

    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
