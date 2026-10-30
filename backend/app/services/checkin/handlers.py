# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlmodel import Session, select

from app.core.bus import subscribe
from app.core.clock import now
from app.core.db import get_engine
from app.models.accommodation import BedReallocationSuggestion, Room, StayAssignment
from app.models.participants import Participant

logger = logging.getLogger("festos.services.checkin.handlers")


def _process_cancellation(session: Session, participant_id: str, new_status: str) -> None:
    part = session.get(Participant, participant_id)
    if part:
        part.status = new_status
        session.add(part)

    # 1. Find active stays for this participant
    active_stays = session.exec(
        select(StayAssignment).where(
            StayAssignment.participant_id == participant_id,
            StayAssignment.status == "ACTIVE",
        )
    ).all()

    if not active_stays:
        logger.info(f"No active stays to release for {participant_id}")
        return

    for stay in active_stays:
        stay.status = "CANCELLED"
        stay.updated_at = now()
        session.add(stay)

        freed_room = None
        if stay.room_id:
            freed_room = session.get(Room, stay.room_id)

        # 2. Find eligible unplaced participants to suggest
        active_part_ids_query = select(StayAssignment.participant_id).where(
            StayAssignment.status == "ACTIVE"
        )
        active_part_ids = set(session.exec(active_part_ids_query).all())

        unplaced_candidates = session.exec(
            select(Participant).where(
                Participant.id != participant_id,
                Participant.status.not_in(["CANCELLED", "NO_SHOW", "CHECKED_OUT"]),
                Participant.accommodation_requested == "YES",
                Participant.id.not_in(active_part_ids),
            )
        ).all()

        best_candidate: Participant | None = None
        best_score = 0.0
        cohesion_note = ""

        for cand in unplaced_candidates:
            cand_gender = (cand.gender or "UNKNOWN").lower().strip()
            cand_acc = bool(cand.accessibility_needs and cand.accessibility_needs not in ["none", ""])

            # Check eligibility if on-campus room
            if freed_room:
                if cand_acc and (not freed_room.accessible or freed_room.floor != 0):
                    continue
                if cand_gender in ["male", "boy", "m"] and freed_room.gender_class.lower() not in ["boys", "male", "neutral"]:
                    continue
                if cand_gender in ["female", "girl", "f"] and freed_room.gender_class.lower() not in ["girls", "female", "neutral"]:
                    continue

            # Scoring
            score = 50.0
            if part and cand.contingent_id and cand.contingent_id == part.contingent_id:
                score += 45.0
                cohesion_note = f"Preserves contingent {cand.contingent_id} cohesion with freed peer bed."
            else:
                cohesion_note = "Alternative placement candidate from general unplaced queue."

            if cand.role == "LEADER":
                score += 5.0

            if score > best_score:
                best_score = score
                best_candidate = cand

        # 3. Create reallocation suggestion (ADVISORY ONLY, NEVER AUTO-APPLY)
        suggestion = BedReallocationSuggestion(
            freed_bed_key=stay.bed_key,
            freed_room_id=stay.room_id,
            freed_by_participant_id=participant_id,
            reason=f"PARTICIPANT_{new_status}",
            suggested_participant_id=best_candidate.id if best_candidate else None,
            suggested_participant_name=best_candidate.name if best_candidate else None,
            contingent_id=best_candidate.contingent_id if best_candidate else None,
            priority_score=best_score if best_candidate else 0.0,
            cohesion_benefit=cohesion_note,
            status="PENDING",
            created_at=now(),
        )
        session.add(suggestion)

    session.commit()
    logger.info(f"Released bed(s) for {participant_id} and generated reallocation suggestion.")


@subscribe("participant.status_changed")
def handle_participant_status_changed(payload: Dict[str, Any]) -> None:
    """Subscribe to participant.status_changed domain event.

    On CANCELLATION or NO-SHOW:
    1. Releases active bed allocations (stay.status = CANCELLED).
    2. Suggests (NEVER auto-applies) reallocation for an eligible unplaced participant.
    """
    if not isinstance(payload, dict):
        return

    participant_id = payload.get("participant_id") or payload.get("id")
    new_status = payload.get("new_status") or payload.get("status")

    if not participant_id or new_status not in ["CANCELLED", "NO_SHOW"]:
        return

    logger.info(f"Handling participant status change for {participant_id}: {new_status}")

    session_ctx = payload.get("_session")
    if session_ctx:
        _process_cancellation(session_ctx, participant_id, new_status)
    else:
        with Session(get_engine()) as session:
            _process_cancellation(session, participant_id, new_status)


def register_checkin_handlers() -> None:
    subscribe("participant.status_changed")(handle_participant_status_changed)


register_checkin_handlers()

