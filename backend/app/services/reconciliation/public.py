# OWNER: P1
"""Public module contract for Reconciliation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.participants import DuplicateCandidate, MergeRecord, Participant
from app.schemas.common import EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return reconciliation KPI summary as of `now`."""
    raw_count = session.exec(select(func.count(Participant.id))).one()
    merged_count = session.exec(select(func.count(Participant.id)).where(Participant.status == "MERGED")).one()
    active_merges = session.exec(select(func.count(MergeRecord.id)).where(MergeRecord.is_reverted.is_(False))).one()
    pending_cands = session.exec(select(func.count(DuplicateCandidate.id)).where(DuplicateCandidate.status == "PENDING")).one()

    return {
        "module": "reconciliation",
        "raw_participants": raw_count,
        "canonical_active": raw_count - merged_count,
        "merged_records": merged_count,
        "active_merges": active_merges,
        "pending_duplicate_candidates": pending_cands,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active reconciliation risks."""
    risks_list: List[RiskItem] = []

    pending_likely = session.exec(
        select(func.count(DuplicateCandidate.id)).where(
            DuplicateCandidate.classification == "LIKELY",
            DuplicateCandidate.status == "PENDING",
        )
    ).one()

    if pending_likely > 0:
        risks_list.append(RiskItem(
            id="risk_rec_pending_likely",
            module="reconciliation",
            kind="UNRESOLVED_LIKELY_DUPLICATES",
            title=f"{pending_likely} High-Confidence Duplicates Unresolved",
            severity=Severity.HIGH,
            hours_to_impact=2,
            people_affected=pending_likely * 2,
            uncertainty=0.1,
            resource_criticality=3,
            entity_refs=[],
            action={"label": "Review Duplicates", "route": "/reconciliation", "api": "/api/v1/reconciliation/duplicates"},
            explanation="Likely duplicates should be merged or marked keep-separate prior to check-in to avoid badge and kit duplication.",
        ))

    return risks_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream merged entities."""
    refs: List[EntityRef] = []
    if entity_type == "merge_record":
        m = session.get(MergeRecord, entity_id)
        if m:
            refs.append(EntityRef(type="participant", id=m.canonical_participant_id, label="Canonical Participant"))
            refs.append(EntityRef(type="participant", id=m.merged_participant_id, label="Merged Participant"))
    return refs
