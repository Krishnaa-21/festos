# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session

from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    return {"module": "participants", "status": "OPERATIONAL"}

def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    return []

def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
