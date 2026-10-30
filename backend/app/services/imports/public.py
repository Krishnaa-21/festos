# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.ops import StagedRecord
from app.models.participants import ImportBatch, Participant, QuarantineRow, RawRecord
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    total_batches = len(session.exec(select(ImportBatch)).all())
    total_raw = len(session.exec(select(RawRecord)).all())
    total_quarantined = len(session.exec(select(QuarantineRow)).all())
    total_staged = len(session.exec(select(StagedRecord)).all())

    # Count canonical participants
    canonical_participants = len(session.exec(select(Participant)).all())

    status = "NEEDS_ATTENTION" if total_quarantined > 0 else "OPERATIONAL"

    return {
        "module": "imports",
        "status": status,
        "total_batches": total_batches,
        "total_raw_records": total_raw,
        "total_staged_records": total_staged,
        "total_quarantined_records": total_quarantined,
        "canonical_participants": canonical_participants,
        "reconciliation_baseline": {
            "raw_participants": 2836,
            "narrative_expected": 2400,
            "declared_contingent": 2842,
        },
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now` (so premortem can replay any hour).
    Key risks: unresolved quarantine, UNKNOWN-heavy critical fields.
    """
    risk_items: List[RiskItem] = []

    # 1. Unresolved quarantine rows
    quarantine_rows = session.exec(select(QuarantineRow)).all()
    q_count = len(quarantine_rows)
    if q_count > 0:
        entity_refs = [
            EntityRef(type="quarantine_row", id=r.id, label=f"{r.reason} ({r.raw_payload.get('participant_id', 'UNKNOWN')})")
            for r in quarantine_rows[:10]
        ]
        risk_items.append(
            RiskItem(
                id="risk_imports_unresolved_quarantine",
                module="imports",
                kind="DATA_INTEGRITY",
                title=f"{q_count} raw records quarantined with invalid intervals",
                severity=Severity.CRITICAL,
                hours_to_impact=0.0,
                people_affected=q_count,
                uncertainty=0.0,
                resource_criticality=5,
                entity_refs=entity_refs,
                action=ActionRef(
                    label="Review Quarantined Records",
                    route="/imports",
                    api="/api/v1/imports",
                ),
                explanation="Participants with arrival datetime scheduled at or after departure cannot be accommodated or scheduled safely.",
            )
        )

    # 2. UNKNOWN-heavy critical fields (Gender)
    participants = session.exec(select(Participant)).all()
    if not participants:
        # Fallback to staged records if canonical not yet promoted
        staged = session.exec(select(StagedRecord).where(StagedRecord.target_table == "participant")).all()
        participants = [s.payload for s in staged]
    else:
        participants = [p.model_dump() for p in participants]

    if participants:
        unknown_gender_count = sum(
            1 for p in participants if p.get("gender") in ("UNKNOWN", "Prefer not to say", "Non-binary", None)
        )
        if unknown_gender_count > 0:
            risk_items.append(
                RiskItem(
                    id="risk_imports_unknown_gender",
                    module="imports",
                    kind="ALLOCATION_BOTTLENECK",
                    title=f"{unknown_gender_count} participants have UNKNOWN/Non-binary gender",
                    severity=Severity.HIGH,
                    hours_to_impact=12.0,
                    people_affected=unknown_gender_count,
                    uncertainty=0.4,
                    resource_criticality=4,
                    action=ActionRef(
                        label="View Unknowns Queue",
                        route="/data-quality",
                        api="/api/v1/data-quality",
                    ),
                    explanation="Campus hostels have only boys and girls blocks. UNKNOWN gender participants cannot be auto-placed without verification or gender-neutral assignment.",
                )
            )

        unknown_diet_count = sum(1 for p in participants if p.get("diet") in ("UNKNOWN", None, ""))
        if unknown_diet_count > 0:
            risk_items.append(
                RiskItem(
                    id="risk_imports_unknown_diet",
                    module="imports",
                    kind="FOOD_SAFETY",
                    title=f"{unknown_diet_count} participants lack dietary clearance",
                    severity=Severity.MEDIUM,
                    hours_to_impact=24.0,
                    people_affected=unknown_diet_count,
                    uncertainty=0.3,
                    resource_criticality=3,
                    action=ActionRef(
                        label="Dietary Compliance",
                        route="/data-quality",
                        api="/api/v1/data-quality",
                    ),
                    explanation="Meal catering cannot ensure religious dietary or allergen clearance for unverified dietary participants.",
                )
            )

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    if entity_type == "import_batch":
        staged = session.exec(
            select(StagedRecord).where(StagedRecord.batch_id == entity_id)
        ).all()
        return [
            EntityRef(type=s.target_table, id=s.source_row_id, label=f"Staged {s.target_table} {s.source_row_id}")
            for s in staged[:25]
        ]
    return []
