# OWNER: P1
"""Service layer for Reconciliation, Waterfall, and Duplicate Resolution."""

from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional

from sqlmodel import Session, func, select

from app.core.clock import now
from app.models.change import Assumption
from app.models.events import Event
from app.models.inventory import MerchClaim
from app.models.participants import (
    Contingent,
    DuplicateCandidate,
    MergeRecord,
    Participant,
    QuarantineRow,
    Registration,
)


def get_waterfall(session: Session) -> Dict[str, Any]:
    """Generates the counts panel and honest reconciliation waterfall explaining the 2,836 vs 2,842 vs 2,400 gap."""
    # 1. Total Raw Rosters
    raw_count = session.exec(select(func.count(Participant.id))).one()

    # 2. Total Declared
    declared_sum = session.exec(select(func.sum(Contingent.strength_declared))).one() or 0

    # 3. Narrative Expected (from assumption or default 2400)
    narrative_asm = session.exec(
        select(Assumption).where(Assumption.key == "expected_participants_narrative")
    ).first()
    narrative_expected = int(narrative_asm.value) if narrative_asm else 2400

    # 4. Invalids and Withdrawn
    invalid_count = session.exec(select(func.count(Participant.id)).where(Participant.status == "INVALID")).one()
    withdrawn_count = session.exec(
        select(func.count(Participant.id)).where(Participant.status.in_(["WITHDRAWN", "CANCELLED"]))
    ).one()

    # 5. Duplicates
    exact_dup = session.exec(
        select(func.count(DuplicateCandidate.id)).where(
            DuplicateCandidate.classification == "EXACT",
            DuplicateCandidate.status == "PENDING",
        )
    ).one()
    likely_dup = session.exec(
        select(func.count(DuplicateCandidate.id)).where(
            DuplicateCandidate.classification == "LIKELY",
            DuplicateCandidate.status == "PENDING",
        )
    ).one()
    possible_dup = session.exec(
        select(func.count(DuplicateCandidate.id)).where(
            DuplicateCandidate.classification == "POSSIBLE",
            DuplicateCandidate.status == "PENDING",
        )
    ).one()
    total_unresolved = exact_dup + likely_dup + possible_dup

    # 6. Quarantined
    quarantined_count = session.exec(select(func.count(QuarantineRow.id))).one()

    # Calculate deficit and surplus across contingents
    contingents = session.exec(select(Contingent)).all()
    actual_counts = session.exec(
        select(Participant.contingent_id, func.count(Participant.id))
        .where(Participant.status != "MERGED")
        .group_by(Participant.contingent_id)
    ).all()
    act_map = {cid: cnt for cid, cnt in actual_counts if cid}

    deficit_sum = 0
    surplus_sum = 0
    deficit_contingents: List[str] = []
    surplus_contingents: List[str] = []

    for c in contingents:
        dec = c.strength_declared or 0
        act = act_map.get(c.id, 0)
        diff = act - dec
        if diff < 0:
            deficit_sum += diff
            deficit_contingents.append(f"{c.code} ({diff:+d})")
        elif diff > 0:
            surplus_sum += diff
            surplus_contingents.append(f"{c.code} ({diff:+d})")

    # Waterfall Steps
    running = declared_sum
    waterfall = [
        {
            "step": "DECLARED_TOTAL",
            "label": "Total Declared Across 38 Contingents",
            "count": running,
            "delta": running,
            "note": "Sum of strength_declared in contingents.csv",
        },
        {
            "step": "CONTINGENT_DEFICIT",
            "label": f"Under-declared Contingent Gaps ({', '.join(deficit_contingents)})",
            "count": running + deficit_sum,
            "delta": deficit_sum,
            "note": f"Institutions that submitted fewer participant names than declared (net {deficit_sum})",
        },
    ]
    running += deficit_sum

    waterfall.append({
        "step": "CONTINGENT_SURPLUS",
        "label": f"Over-declared Contingent Gaps ({', '.join(surplus_contingents)})",
        "count": running + surplus_sum,
        "delta": surplus_sum,
        "note": f"Institutions that submitted surplus participant names over declared (net +{surplus_sum})",
    })
    running += surplus_sum

    waterfall.append({
        "step": "RAW_ROSTER_TOTAL",
        "label": "Raw Imported Participant Rosters",
        "count": raw_count,
        "delta": 0,
        "note": "Exact count of imported participant rows in participants.csv",
    })

    waterfall.append({
        "step": "INVALID_DATES",
        "label": "Invalid Departure Prior to Arrival",
        "count": raw_count - invalid_count,
        "delta": -invalid_count,
        "note": f"{invalid_count} records have departure_datetime < arrival_datetime and are held out",
    })

    waterfall.append({
        "step": "LIKELY_DUPLICATES",
        "label": "High-Confidence Duplicates Requiring Review",
        "count": raw_count - invalid_count - likely_dup,
        "delta": -likely_dup,
        "note": f"{likely_dup} multi-signal duplicate pairs pending desk review",
    })

    surplus_over_narrative = raw_count - narrative_expected
    waterfall.append({
        "step": "NARRATIVE_SURPLUS",
        "label": "Surplus Roster Volume Over Planning Narrative",
        "count": narrative_expected,
        "delta": -surplus_over_narrative,
        "note": f"Planning narrative estimated {narrative_expected}; actual rosters contain {raw_count} (surplus +{surplus_over_narrative})",
    })

    counts = {
        "raw": raw_count,
        "narrative_expected": narrative_expected,
        "declared": declared_sum,
        "declared_vs_raw_gap": raw_count - declared_sum,
        "exact_duplicates": exact_dup,
        "likely_duplicates": likely_dup,
        "possible_duplicates": possible_dup,
        "withdrawn": withdrawn_count,
        "invalid": invalid_count,
        "unresolved": total_unresolved,
        "quarantined": quarantined_count,
    }

    warnings = []
    if len(deficit_contingents) > 0 or len(surplus_contingents) > 0:
        warnings.append(f"{len(deficit_contingents) + len(surplus_contingents)} contingents have declared vs actual roster discrepancies.")
    if invalid_count > 0:
        warnings.append(f"{invalid_count} participant records have impossible arrival/departure datetimes.")

    return {
        "counts": counts,
        "waterfall": waterfall,
        "warnings": warnings,
    }


def list_duplicates(
    session: Session,
    classification: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Lists duplicate candidate pairs with pagination and filtering."""
    query = select(DuplicateCandidate)

    if classification:
        query = query.where(DuplicateCandidate.classification == classification)
    if status:
        query = query.where(DuplicateCandidate.status == status)
    subq = query.subquery()
    total = session.exec(select(func.count()).select_from(subq)).one()

    offset = (page - 1) * page_size
    candidates = session.exec(
        query.order_by(DuplicateCandidate.score.desc()).offset(offset).limit(page_size)
    ).all()

    items = []
    for c in candidates:
        pa = session.get(Participant, c.participant_a_id)
        pb = session.get(Participant, c.participant_b_id)
        items.append({
            "id": c.id,
            "participant_a_id": c.participant_a_id,
            "participant_b_id": c.participant_b_id,
            "participant_a_name": pa.name if pa else "UNKNOWN",
            "participant_b_name": pb.name if pb else "UNKNOWN",
            "college_a": pa.college if pa else None,
            "college_b": pb.college if pb else None,
            "score": c.score,
            "classification": c.classification,
            "reasons": c.reasons,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def compare_participants(session: Session, id1: str, id2: str) -> Optional[Dict[str, Any]]:
    """Generates a side-by-side comparison of two participant records including registrations and claims."""
    pa = session.get(Participant, id1)
    pb = session.get(Participant, id2)
    if not pa or not pb:
        return None

    # Registrations
    regs_a = session.exec(select(Registration).where(Registration.participant_id == id1)).all()
    regs_b = session.exec(select(Registration).where(Registration.participant_id == id2)).all()

    def _reg_to_dict(r: Registration) -> Dict[str, Any]:
        ev = session.get(Event, r.event_id)
        return {
            "registration_id": r.id,
            "event_id": r.event_id,
            "event_name": ev.name if ev else r.event_id,
            "team_id": r.team_id,
        }

    # Merch Claims
    claims_a = session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == id1)).all()
    claims_b = session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == id2)).all()

    items_a = {c.item_id for c in claims_a}
    items_b = {c.item_id for c in claims_b}
    merch_conflict = bool(items_a.intersection(items_b))

    from rapidfuzz import fuzz
    name_sim = fuzz.token_sort_ratio(pa.name.lower(), pb.name.lower()) / 100.0

    return {
        "participant_a": {
            "id": pa.id,
            "name": pa.name,
            "college": pa.college,
            "contingent_id": pa.contingent_id,
            "phone": pa.phone,
            "email": pa.email,
            "gender": pa.gender,
            "diet": pa.diet,
            "tshirt_size": pa.tshirt_size,
            "age": pa.age,
            "status": pa.status,
            "arrival_at": pa.arrival_at.isoformat() if pa.arrival_at else None,
            "departure_at": pa.departure_at.isoformat() if pa.departure_at else None,
            "registrations": [_reg_to_dict(r) for r in regs_a],
            "claims": [{"id": c.id, "item_id": c.item_id} for c in claims_a],
        },
        "participant_b": {
            "id": pb.id,
            "name": pb.name,
            "college": pb.college,
            "contingent_id": pb.contingent_id,
            "phone": pb.phone,
            "email": pb.email,
            "gender": pb.gender,
            "diet": pb.diet,
            "tshirt_size": pb.tshirt_size,
            "age": pb.age,
            "status": pb.status,
            "arrival_at": pb.arrival_at.isoformat() if pb.arrival_at else None,
            "departure_at": pb.departure_at.isoformat() if pb.departure_at else None,
            "registrations": [_reg_to_dict(r) for r in regs_b],
            "claims": [{"id": c.id, "item_id": c.item_id} for c in claims_b],
        },
        "comparison": {
            "name_similarity": name_sim,
            "contingent_match": pa.contingent_id == pb.contingent_id,
            "age_match": pa.age == pb.age,
            "phone_match": pa.phone == pb.phone if pa.phone and pb.phone else False,
            "merch_conflict": merch_conflict,
            "can_merge": not merch_conflict and pa.status != "MERGED" and pb.status != "MERGED",
        },
    }


def keep_separate(session: Session, candidate_id: str, reason: str, actor_id: str) -> Dict[str, Any]:
    """Marks a duplicate candidate pair as IGNORED with recorded rationale."""
    cand = session.get(DuplicateCandidate, candidate_id)
    if not cand:
        raise ValueError(f"DuplicateCandidate {candidate_id} not found.")

    cand.status = "IGNORED"
    cand.reasons = {**(cand.reasons or {}), "ignored_reason": reason, "ignored_by": actor_id, "ignored_at": now().isoformat()}
    session.add(cand)
    session.flush()

    return {"candidate_id": cand.id, "status": "IGNORED"}


def get_merge_history(session: Session) -> List[Dict[str, Any]]:
    """Returns chronological merge operations with reversibility status."""
    records = session.exec(select(MergeRecord).order_by(MergeRecord.merged_at.desc())).all()
    history = []
    for m in records:
        pa = session.get(Participant, m.canonical_participant_id)
        pb = session.get(Participant, m.merged_participant_id)
        history.append({
            "id": m.id,
            "canonical_participant_id": m.canonical_participant_id,
            "canonical_name": pa.name if pa else "UNKNOWN",
            "merged_participant_id": m.merged_participant_id,
            "merged_name": pb.name if pb else "UNKNOWN",
            "reason": m.reason,
            "merged_by": m.merged_by,
            "merged_at": m.merged_at.isoformat() if m.merged_at else None,
            "is_reverted": m.is_reverted,
            "reverted_at": m.reverted_at.isoformat() if m.reverted_at else None,
            "reverted_by": m.reverted_by,
        })
    return history


def get_flags(session: Session) -> Dict[str, Any]:
    """Identifies operational edge cases across participants, leadership, and staff."""
    # 1. Same name different people across institutions
    name_groups = session.exec(
        select(Participant.name, func.count(Participant.id), func.count(func.distinct(Participant.contingent_id)))
        .where(Participant.status != "MERGED")
        .group_by(Participant.name)
        .having(func.count(func.distinct(Participant.contingent_id)) > 1)
    ).all()

    same_name_diff: List[Dict[str, Any]] = []
    for name, cnt, cont_cnt in name_groups[:20]:
        conts = session.exec(
            select(func.distinct(Participant.contingent_id))
            .where(Participant.name == name, Participant.status != "MERGED")
        ).all()
        same_name_diff.append({
            "name": name,
            "count": cnt,
            "contingents": [c for c in conts if c],
            "note": "Distinct individuals with identical names across institutions",
        })

    # 2. Leaders who are also competitors
    contingents = session.exec(select(Contingent)).all()
    leaders_competing = []
    for c in contingents:
        if not c.leader:
            continue
        p = session.exec(
            select(Participant).where(Participant.contingent_id == c.id, Participant.name == c.leader)
        ).first()
        if p:
            regs = session.exec(select(Registration).where(Registration.participant_id == p.id)).all()
            if regs:
                leaders_competing.append({
                    "participant_id": p.id,
                    "name": p.name,
                    "contingent_id": c.id,
                    "college": c.college,
                    "registered_events_count": len(regs),
                    "registered_events": [r.event_id for r in regs],
                })

    # 3. Staff as participants (cross-referenced with core_team.csv if present)
    staff_as_participants = []
    from app.seed.participants import _find_data_file
    core_team_path = _find_data_file("core_team.csv")
    if core_team_path and core_team_path.exists():
        with open(core_team_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            staff_rows = list(reader)
            staff_names = {r["name"].strip().lower(): r for r in staff_rows if "name" in r}

            matched_participants = session.exec(
                select(Participant).where(Participant.status != "MERGED")
            ).all()

            for p in matched_participants:
                p_name_lower = p.name.strip().lower()
                if p_name_lower in staff_names:
                    s_info = staff_names[p_name_lower]
                    staff_as_participants.append({
                        "participant_id": p.id,
                        "name": p.name,
                        "staff_id": s_info.get("member_id"),
                        "staff_role": s_info.get("role"),
                        "college": p.college,
                        "note": "Same name as core team member (check if distinct individual)",
                    })

    return {
        "same_name_different_people": same_name_diff,
        "leaders_competing": leaders_competing,
        "escorts_judging": [],  # Escort judging checks (no judge data in pack)
        "staff_as_participants": staff_as_participants[:25],
    }
