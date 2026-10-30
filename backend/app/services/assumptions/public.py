# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.ops import Assumption
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity
from app.services.assumptions.service import ASSUMPTION_CATALOG, get_assumption


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    assumptions = session.exec(select(Assumption)).all()
    owners = set(a.owner for a in assumptions if a.owner)
    
    last_updated = None
    if assumptions:
        dates = [a.updated_at for a in assumptions if a.updated_at]
        if dates:
            last_updated = max(dates).isoformat()

    return {
        "module": "assumptions",
        "status": "OPERATIONAL" if assumptions else "NOT_SEEDED",
        "total_assumptions": len(assumptions),
        "owners": sorted(list(owners)),
        "last_updated": last_updated,
        "catalog_keys_count": len(ASSUMPTION_CATALOG),
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now` (so premortem can replay any hour)."""
    risk_items: List[RiskItem] = []

    # 1. Check if cleaning buffer is dangerously low (< 15 mins)
    cleaning_buf = get_assumption("cleaning_buffer_minutes", session=session)
    if cleaning_buf is not None and isinstance(cleaning_buf, (int, float)) and cleaning_buf < 15:
        risk_items.append(
            RiskItem(
                id="risk_assumptions_cleaning_buffer_tight",
                module="assumptions",
                kind="OPERATIONAL_BOTTLENECK",
                title=f"Hostel cleaning buffer is only {cleaning_buf} mins (minimum recommended: 15 mins)",
                severity=Severity.HIGH,
                hours_to_impact=2.0,
                people_affected=1450,
                uncertainty=0.2,
                resource_criticality=4,
                action=ActionRef(
                    label="Adjust Cleaning Buffer",
                    route="/assumptions",
                    api="/api/v1/assumptions",
                ),
                explanation="Room turnover between contingent departures and arrivals requires at least 15-30 minutes for inspection and sanitation.",
            )
        )

    # 2. Check if minor threshold is set appropriately
    minor_thresh = get_assumption("minor_age_threshold", session=session)
    if minor_thresh is not None and isinstance(minor_thresh, (int, float)) and minor_thresh < 18:
        risk_items.append(
            RiskItem(
                id="risk_assumptions_minor_threshold_lax",
                module="assumptions",
                kind="LEGAL_COMPLIANCE",
                title=f"Minor age threshold is set to {minor_thresh} instead of legal age 18",
                severity=Severity.CRITICAL,
                hours_to_impact=0.0,
                people_affected=279,
                uncertainty=0.0,
                resource_criticality=5,
                action=ActionRef(
                    label="Correct Minor Threshold",
                    route="/assumptions",
                    api="/api/v1/assumptions",
                ),
                explanation="Statutory campus safety rules mandate special escort requirements for anyone under age 18.",
            )
        )

    # 3. Check for any assumption marked as placeholder or unverified
    unverified = session.exec(select(Assumption).where(Assumption.reason.like("%placeholder%"))).all()
    if unverified:
        risk_items.append(
            RiskItem(
                id="risk_assumptions_unverified_placeholders",
                module="assumptions",
                kind="POLICY_UNCERTAINTY",
                title=f"{len(unverified)} assumptions are using placeholder estimates",
                severity=Severity.MEDIUM,
                hours_to_impact=48.0,
                people_affected=500,
                uncertainty=0.5,
                resource_criticality=3,
                entity_refs=[
                    EntityRef(type="assumption", id=a.key, label=f"{a.key}: {a.value}")
                    for a in unverified[:5]
                ],
                action=ActionRef(
                    label="Review Assumptions Register",
                    route="/assumptions",
                    api="/api/v1/assumptions",
                ),
                explanation="Operating parameters marked as placeholders need sign-off by festival coordinators before launch.",
            )
        )

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    if entity_type == "assumption":
        # Check catalog dependents for this assumption key
        cat = ASSUMPTION_CATALOG.get(entity_id)
        if cat and cat.get("dependent_modules"):
            return [
                EntityRef(type="module", id=m, label=f"Module {m}")
                for m in cat["dependent_modules"]
            ]
    return []

