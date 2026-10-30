# OWNER: P1
"""Public module contract for Contingents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.participants import Contingent, Participant
from app.schemas.common import EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return contingents module KPI summary as of `now`."""
    total_contingents = session.exec(select(func.count(Contingent.id))).one()
    total_declared = session.exec(select(func.sum(Contingent.strength_declared))).one() or 0

    # Actual count
    total_actual = session.exec(
        select(func.count(Participant.id)).where(Participant.status != "MERGED")
    ).one()

    return {
        "module": "contingents",
        "total_contingents": total_contingents,
        "total_declared": total_declared,
        "total_actual": total_actual,
        "strength_gap": total_actual - total_declared,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active contingent operational risks."""
    risks_list: List[RiskItem] = []

    # Flag contingents with size mismatches
    contingents = session.exec(select(Contingent)).all()
    actuals = session.exec(
        select(Participant.contingent_id, func.count(Participant.id))
        .where(Participant.status != "MERGED")
        .group_by(Participant.contingent_id)
    ).all()
    act_map = {cid: cnt for cid, cnt in actuals if cid}

    mismatch_ids = []
    for c in contingents:
        if act_map.get(c.id, 0) != (c.strength_declared or 0):
            mismatch_ids.append(c.id)

    if mismatch_ids:
        risks_list.append(RiskItem(
            id="risk_ctg_roster_mismatch",
            module="contingents",
            kind="DECLARED_ACTUAL_STRENGTH_MISMATCH",
            title=f"{len(mismatch_ids)} Contingents Have Declared vs Roster Discrepancies",
            severity=Severity.MEDIUM,
            hours_to_impact=12,
            people_affected=sum(abs(act_map.get(cid, 0) - (session.get(Contingent, cid).strength_declared or 0)) for cid in mismatch_ids),
            uncertainty=0.1,
            resource_criticality=3,
            entity_refs=[{"type": "contingent", "id": cid, "label": f"Contingent {cid}"} for cid in mismatch_ids],
            action={"label": "View Contingents", "route": "/contingents", "api": "/api/v1/contingents?has_mismatch=true"},
            explanation="Declared institution strengths do not match submitted student rosters. Logistics and meal counts require reconciliation.",
        ))

    return risks_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream participants of a contingent."""
    if entity_type == "contingent":
        participants = session.exec(
            select(Participant.id, Participant.name).where(Participant.contingent_id == entity_id)
        ).all()
        return [EntityRef(type="participant", id=pid, label=name) for pid, name in participants[:100]]
    return []
