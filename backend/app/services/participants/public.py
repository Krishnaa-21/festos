# OWNER: P1
"""Public module contract for Participants.

Used across FestOS for dashboard KPIs, pre-mortem risk evaluation, and impact graph dependency traversal.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.inventory import MerchClaim
from app.models.participants import (
    DuplicateCandidate,
    FieldVerification,
    Participant,
    Registration,
)
from app.schemas.common import EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return participants KPI summary as of `now` for operational dashboards."""
    total_participants = session.exec(
        select(func.count(Participant.id)).where(Participant.status != "MERGED")
    ).one()

    status_counts_raw = session.exec(
        select(Participant.status, func.count(Participant.id))
        .group_by(Participant.status)
    ).all()
    status_map = {st: cnt for st, cnt in status_counts_raw}

    pending_dups = session.exec(
        select(func.count(DuplicateCandidate.id)).where(DuplicateCandidate.status == "PENDING")
    ).one()

    unverified_unknowns = session.exec(
        select(func.count(FieldVerification.id)).where(FieldVerification.status == "UNKNOWN")
    ).one()

    return {
        "module": "participants",
        "total_canonical": total_participants,
        "expected": status_map.get("EXPECTED", 0),
        "arrived": status_map.get("ARRIVED", 0),
        "checked_in": status_map.get("CHECKED_IN", 0),
        "checked_out": status_map.get("CHECKED_OUT", 0),
        "invalid": status_map.get("INVALID", 0),
        "withdrawn": status_map.get("WITHDRAWN", 0) + status_map.get("CANCELLED", 0),
        "pending_duplicates": pending_dups,
        "unverified_unknowns": unverified_unknowns,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now` for pre-mortem simulation and alert banners."""
    items: List[RiskItem] = []

    # 1. Unresolved Duplicates Risk
    likely_dups = session.exec(
        select(DuplicateCandidate).where(
            DuplicateCandidate.classification == "LIKELY",
            DuplicateCandidate.status == "PENDING",
        )
    ).all()

    if likely_dups:
        items.append(RiskItem(
            id="risk_par_unresolved_duplicates",
            module="participants",
            kind="DUPLICATE_CANDIDATES_PENDING",
            title=f"{len(likely_dups)} High-Confidence Duplicate Candidates Unresolved",
            severity=Severity.HIGH,
            hours_to_impact=2,
            people_affected=len(likely_dups) * 2,
            uncertainty=0.1,
            resource_criticality=3,
            entity_refs=[{"type": "duplicate_candidate", "id": d.id, "label": f"{d.participant_a_id} vs {d.participant_b_id}"} for d in likely_dups[:5]],
            action={"label": "Open Reconciliation Workbench", "route": "/reconciliation", "api": "/api/v1/reconciliation/duplicates"},
            explanation="Unmerged duplicate records will cause double-counting of accommodation and duplicate merchandise claims upon arrival check-in.",
        ))

    # 2. Unknown-Heavy Arrivals in Next 4 Hours
    window_end = now + timedelta(hours=4)
    incoming_unknowns = session.exec(
        select(Participant).where(
            Participant.status == "EXPECTED",
            Participant.arrival_at >= now,
            Participant.arrival_at <= window_end,
            (Participant.diet == "UNKNOWN") | (Participant.accommodation_requested == "UNKNOWN"),
        )
    ).all()

    if incoming_unknowns:
        items.append(RiskItem(
            id="risk_par_unknown_heavy_arrivals",
            module="participants",
            kind="UNKNOWN_HEAVY_ARRIVALS",
            title=f"{len(incoming_unknowns)} Participants Arriving Soon With UNKNOWN Requirements",
            severity=Severity.MEDIUM,
            hours_to_impact=4,
            people_affected=len(incoming_unknowns),
            uncertainty=0.4,
            resource_criticality=4,
            entity_refs=[{"type": "participant", "id": p.id, "label": p.name} for p in incoming_unknowns[:5]],
            action={"label": "Open Unknown Verification Queue", "route": "/unknowns", "api": "/api/v1/unknowns/queue"},
            explanation="Participants arriving within 4 hours have unconfirmed housing or dietary needs, creating bottlenecks at the reception and food desks.",
        ))

    # 3. Late/Missing Arrivals
    overdue_arrivals = session.exec(
        select(Participant).where(
            Participant.status == "EXPECTED",
            Participant.arrival_at < now,
        )
    ).all()

    if overdue_arrivals:
        items.append(RiskItem(
            id="risk_par_overdue_arrivals",
            module="participants",
            kind="OVERDUE_ARRIVALS",
            title=f"{len(overdue_arrivals)} Participants Overdue for Arrival",
            severity=Severity.MEDIUM,
            hours_to_impact=1,
            people_affected=len(overdue_arrivals),
            uncertainty=0.2,
            resource_criticality=2,
            entity_refs=[{"type": "participant", "id": p.id, "label": p.name} for p in overdue_arrivals[:5]],
            action={"label": "Review Participant Attendance", "route": "/participants", "api": "/api/v1/participants?status=EXPECTED"},
            explanation="Scheduled arrival time has elapsed but participants are still in EXPECTED status. Contingent leaders should be contacted.",
        ))

    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Traverse downstream entities dependent on participant or contingent."""
    refs: List[EntityRef] = []

    if entity_type == "participant":
        p = session.get(Participant, entity_id)
        if p and p.contingent_id:
            refs.append(EntityRef(type="contingent", id=p.contingent_id, label=f"Contingent {p.contingent_id}"))

        regs = session.exec(select(Registration).where(Registration.participant_id == entity_id)).all()
        for r in regs:
            refs.append(EntityRef(type="registration", id=r.id, label=f"Event {r.event_id}"))

        claims = session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == entity_id)).all()
        for c in claims:
            refs.append(EntityRef(type="merch_claim", id=c.id, label=f"Merch Claim {c.item_id}"))

        # Look for stay assignment if accommodation table exists
        try:
            from app.models.accommodation import StayAssignment
            stays = session.exec(select(StayAssignment).where(StayAssignment.participant_id == entity_id)).all()
            for s in stays:
                refs.append(EntityRef(type="stay_assignment", id=s.id, label=f"Bed {s.bed_key}"))
        except (ImportError, Exception):
            pass

    elif entity_type == "contingent":
        participants = session.exec(
            select(Participant).where(Participant.contingent_id == entity_id)
        ).all()
        for p in participants[:50]:
            refs.append(EntityRef(type="participant", id=p.id, label=p.name))

    return refs
