# OWNER: P2
"""Public module contract for Unknowns."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.participants import FieldVerification
from app.schemas.common import EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return unknowns module KPI summary as of `now`."""
    total_unverified = session.exec(
        select(func.count(FieldVerification.id)).where(FieldVerification.status == "UNKNOWN")
    ).one()
    total_verified = session.exec(
        select(func.count(FieldVerification.id)).where(FieldVerification.status == "VERIFIED")
    ).one()

    return {
        "module": "unknowns",
        "unverified_fields": total_unverified,
        "verified_fields": total_verified,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks from unverified fields."""
    risks_list: List[RiskItem] = []
    unverified_housing = session.exec(
        select(func.count(FieldVerification.id)).where(
            FieldVerification.field == "accommodation_requested",
            FieldVerification.status == "UNKNOWN",
        )
    ).one()

    if unverified_housing > 0:
        risks_list.append(RiskItem(
            id="risk_unk_housing_unconfirmed",
            module="unknowns",
            kind="HOUSING_UNVERIFIED",
            title=f"{unverified_housing} Participants Have Unconfirmed Housing Requests",
            severity=Severity.HIGH,
            hours_to_impact=4,
            people_affected=unverified_housing,
            uncertainty=0.4,
            resource_criticality=4,
            entity_refs=[],
            action={"label": "Review Unknown Queue", "route": "/unknowns", "api": "/api/v1/unknowns/queue"},
            explanation="Unconfirmed accommodation requests prevent definitive bed blocks in Plan A and Plan B.",
        ))

    return risks_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entity for a verification record."""
    if entity_type == "field_verification":
        v = session.get(FieldVerification, entity_id)
        if v:
            return [EntityRef(type=v.entity_type, id=v.entity_id, label=f"{v.entity_type}:{v.entity_id}")]
    return []
