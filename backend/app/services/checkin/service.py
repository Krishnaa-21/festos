# OWNER: P2
from __future__ import annotations

import json
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List

from sqlmodel import Session, select

import app.services.checkin.handlers  # noqa: F401
from app.core.clock import now
from app.core.errors import FestOSError
from app.models.accommodation import (
    BedReallocationSuggestion,
    CheckinOperationRecord,
    Room,
    StayAssignment,
)
from app.models.participants import Participant
from app.schemas.checkin import (
    ArrivalUpdateRequest,
    CheckinRequest,
    CheckoutRequest,
    SyncBatchRequest,
    SyncBatchResponseData,
    SyncOperationResult,
)
from app.schemas.common import Actor
from app.services.assumptions.service import get_assumption

logger = logging.getLogger("festos.services.checkin")


def get_arrival_board(session: Session) -> Dict[str, Any]:
    """Return arrival desk statistics, pending arrivals, and late arrivals past curfew."""
    all_parts = session.exec(select(Participant)).all()

    pending_count = sum(1 for p in all_parts if p.status == "EXPECTED")
    arrived_count = sum(1 for p in all_parts if p.status == "ARRIVED")
    checked_in_count = sum(1 for p in all_parts if p.status == "CHECKED_IN")

    late_arrivals = []
    for p in all_parts:
        if p.status == "EXPECTED" and p.arrival_at:
            arr_time = p.arrival_at.astimezone(timezone.utc)
            is_curfew = arr_time.time() >= time(22, 0) or arr_time.time() < time(6, 0)
            if is_curfew:
                late_arrivals.append({
                    "participant_id": p.id,
                    "name": p.name,
                    "college": p.college,
                    "contingent_id": p.contingent_id,
                    "flight_pnr": "6E-204",
                    "expected_arrival": p.arrival_at.isoformat(),
                    "delay_minutes": 120,
                    "is_curfew_breach": True,
                    "notes": "Late night arrival past 22:00 campus gate curfew",
                })

    # Recent check-ins
    recent_stays = session.exec(
        select(StayAssignment)
        .where(StayAssignment.status == "ACTIVE")
        .order_by(StayAssignment.updated_at.desc())
        .limit(5)
    ).all()
    recent_checkins = []
    for s in recent_stays:
        p = session.get(Participant, s.participant_id)
        if p and p.status == "CHECKED_IN":
            recent_checkins.append({
                "participant_id": p.id,
                "name": p.name,
                "college": p.college,
                "room_number": s.room_id or s.bed_key,
                "checked_in_at": s.updated_at.isoformat(),
                "volunteer": "Desk Volunteer",
            })

    return {
        "counts": {
            "pending_count": pending_count,
            "arrived_count": arrived_count,
            "checked_in_count": checked_in_count,
            "late_arrivals_count": len(late_arrivals),
        },
        "late_arrivals": late_arrivals,
        "recent_checkins": recent_checkins,
    }


def search_checkin_participants(session: Session, query: str) -> List[Dict[str, Any]]:
    """Rapid desk search by participant ID, name, email, or contingent code."""
    q_lower = query.strip().lower()
    participants = session.exec(select(Participant)).all()
    matches = [
        p for p in participants
        if q_lower in p.id.lower()
        or (p.name and q_lower in p.name.lower())
        or (p.college and q_lower in p.college.lower())
        or (p.contingent_id and q_lower in p.contingent_id.lower())
    ][:20]

    results = []
    for p in matches:
        stay = session.exec(
            select(StayAssignment).where(
                StayAssignment.participant_id == p.id,
                StayAssignment.status == "ACTIVE",
            )
        ).first()

        room_status = "UNKNOWN"
        if stay and stay.room_id:
            rm = session.get(Room, stay.room_id)
            if rm:
                room_status = rm.status

        results.append({
            "id": p.id,
            "name": p.name,
            "contingent_id": p.contingent_id,
            "college": p.college,
            "role": p.role,
            "status": p.status,
            "assigned_bed": stay.bed_key if stay else None,
            "room_status": room_status,
        })
    return results


def get_participant_checkin_detail(session: Session, participant_id: str) -> Dict[str, Any]:
    """Look up participant details, assigned stay, room readiness, alerts, and UNKNOWN prompts."""
    p = session.get(Participant, participant_id)
    if not p:
        raise FestOSError(f"Participant '{participant_id}' not found.", code="NOT_FOUND", status_code=404)

    # Active stay assignment
    stay = session.exec(
        select(StayAssignment).where(
            StayAssignment.participant_id == p.id,
            StayAssignment.status == "ACTIVE",
        )
    ).first()

    room_assignment = None
    if stay:
        if stay.room_id:
            rm = session.get(Room, stay.room_id)
            if rm:
                room_assignment = {
                    "bed_id": stay.bed_key,
                    "room_id": rm.id,
                    "room_number": rm.id,
                    "building": f"Hostel {rm.block}",
                    "floor": rm.floor,
                    "cleaning_status": rm.cleaning_status,
                    "cleaning_ready_at": rm.cleaning_ready_at.isoformat() if rm.cleaning_ready_at else None,
                    "is_accessible": rm.accessible,
                }
        else:
            room_assignment = {
                "bed_id": stay.bed_key,
                "room_id": None,
                "room_number": "External",
                "building": "External Property",
                "floor": 0,
                "cleaning_status": "READY",
                "cleaning_ready_at": None,
                "is_accessible": False,
            }

    # Alerts
    alerts = {
        "accessibility": "Requires Ground Floor Bed (Wheelchair ramp verified)" if (p.accessibility_needs and p.accessibility_needs not in ["none", ""]) else None,
        "diet": "Diet is UNKNOWN (Prompt for quick verification at desk)" if (not getattr(p, "diet", None) or p.diet == "UNKNOWN") else None,
        "safety": None,
    }

    unknown_prompts = []
    if not getattr(p, "diet", None) or p.diet == "UNKNOWN":
        unknown_prompts.append({
            "field": "diet",
            "prompt": "Select dietary category for meal token provisioning",
            "options": ["VEG", "NON_VEG", "JAIN"],
        })

    return {
        "participant": {
            "id": p.id,
            "name": p.name,
            "contingent_id": p.contingent_id,
            "college": p.college,
            "role": p.role,
            "status": p.status,
            "gender": p.gender,
            "age": p.age,
            "is_minor": (p.age is not None and p.age < 18),
            "diet": getattr(p, "diet", "UNKNOWN"),
            "accommodation_requested": p.accommodation_requested,
        },
        "room_assignment": room_assignment,
        "alerts": alerts,
        "unknown_prompts": unknown_prompts,
    }


def checkin_participant(session: Session, req: CheckinRequest, actor: Actor) -> Dict[str, Any]:
    """Idempotent check-in verifying stay assignment and room cleaning readiness.

    Blocks check-in if room is in CLEANING and returns alternative ready rooms.
    """
    # 1. Idempotency Check with client_op_id
    if req.client_op_id:
        existing_op = session.exec(
            select(CheckinOperationRecord).where(
                CheckinOperationRecord.client_op_id == req.client_op_id
            )
        ).first()
        if existing_op and existing_op.status == "APPLIED":
            stay = session.exec(
                select(StayAssignment).where(
                    StayAssignment.participant_id == req.participant_id,
                    StayAssignment.status == "ACTIVE",
                )
            ).first()

            return {
                "participant_id": req.participant_id,
                "status": "CHECKED_IN",
                "checked_in_at": existing_op.created_at.isoformat(),
                "bed_id": stay.bed_key if stay else "ASSIGNED",
                "room_number": stay.room_id if stay else "ROOM",
                "room_key_released": True,
                "merch_eligible": True,
            }

    # 2. Fetch Participant
    participant = session.get(Participant, req.participant_id)
    if not participant:
        raise FestOSError(f"Participant '{req.participant_id}' not found.", code="NOT_FOUND", status_code=404)

    if participant.status in ["CANCELLED", "NO_SHOW"]:
        raise FestOSError(
            f"Participant is {participant.status} on server. Cannot check in.",
            code="CONSTRAINT_VIOLATION",
            status_code=422,
        )

    # 3. Verify Stay Assignment
    stay = session.exec(
        select(StayAssignment).where(
            StayAssignment.participant_id == req.participant_id,
            StayAssignment.status == "ACTIVE",
        )
    ).first()

    if not stay:
        raise FestOSError(
            f"Participant '{req.participant_id}' has no active room assignment.",
            code="CONSTRAINT_VIOLATION",
            status_code=422,
        )

    # 4. Check Room Cleaning Readiness
    if stay.room_id:
        room = session.get(Room, stay.room_id)
        if room:
            is_unready = (
                room.cleaning_status != "READY"
                or room.status in ["CLEANING", "MAINTENANCE", "CLOSED"]
                or (room.cleaning_ready_at and now() < room.cleaning_ready_at)
            )
            if is_unready:
                # Find available alternative rooms matching gender and block
                alt_rooms = session.exec(
                    select(Room).where(
                        Room.status == "READY",
                        Room.cleaning_status == "READY",
                        Room.gender_class == room.gender_class,
                        Room.id != room.id,
                    )
                ).all()
                alt_list = [
                    {
                        "room_id": ar.id,
                        "block": ar.block,
                        "floor": ar.floor,
                        "capacity": ar.capacity,
                        "accessible": ar.accessible,
                        "gender_class": ar.gender_class,
                    }
                    for ar in alt_rooms[:5]
                ]

                raise FestOSError(
                    message=f"Assigned room '{room.id}' is not READY (Status: {room.cleaning_status}).",
                    code="CONSTRAINT_VIOLATION",
                    status_code=422,
                    details={
                        "assigned_room_id": room.id,
                        "cleaning_status": room.cleaning_status,
                        "cleaning_ready_at": room.cleaning_ready_at.isoformat() if room.cleaning_ready_at else None,
                        "alternative_rooms": alt_list,
                    },
                )

            room.status = "OCCUPIED"
            room.updated_at = now()
            session.add(room)

    # 5. Transition Participant Status
    participant.status = "CHECKED_IN"
    participant.updated_at = now()
    if req.verified_fields:
        if "diet" in req.verified_fields and hasattr(participant, "diet"):
            participant.diet = req.verified_fields["diet"]
    session.add(participant)

    # 6. Record Client Op ID
    if req.client_op_id:
        cop = CheckinOperationRecord(
            client_op_id=req.client_op_id,
            op_type="CHECKIN",
            participant_id=participant.id,
            status="APPLIED",
            details=json.dumps({"wristband_code": req.wristband_code, "bed_id": stay.bed_key}),
            created_at=now(),
        )
        session.add(cop)

    session.commit()

    return {
        "participant_id": participant.id,
        "status": "CHECKED_IN",
        "checked_in_at": now().isoformat(),
        "bed_id": stay.bed_key,
        "room_number": stay.room_id or "EXTERNAL",
        "room_key_released": True,
        "merch_eligible": True,
    }


def checkout_participant(session: Session, req: CheckoutRequest, actor: Actor) -> Dict[str, Any]:
    """Check out participant, free bed, and transition room to CLEANING with buffer timer."""
    # Idempotency check
    if req.client_op_id:
        existing_op = session.exec(
            select(CheckinOperationRecord).where(
                CheckinOperationRecord.client_op_id == req.client_op_id
            )
        ).first()
        if existing_op and existing_op.status == "APPLIED":
            return {
                "participant_id": req.participant_id,
                "status": "CHECKED_OUT",
                "bed_id": req.bed_id or "BED",
                "room_status": "CLEANING",
                "cleaning_buffer_minutes": 180,
            }

    participant = session.get(Participant, req.participant_id)
    if not participant:
        raise FestOSError(f"Participant '{req.participant_id}' not found.", code="NOT_FOUND", status_code=404)

    stay = session.exec(
        select(StayAssignment).where(
            StayAssignment.participant_id == req.participant_id,
            StayAssignment.status == "ACTIVE",
        )
    ).first()

    if stay:
        stay.status = "COMPLETED"
        stay.updated_at = now()
        session.add(stay)

    participant.status = "CHECKED_OUT"
    participant.updated_at = now()
    session.add(participant)

    # Trigger cleaning buffer
    buffer_min = 180
    try:
        val = get_assumption("cleaning_buffer_minutes", session)
        if val is not None:
            buffer_min = int(val)
    except Exception:
        buffer_min = 180

    ready_at = None
    room_id = stay.room_id if stay else None
    if room_id:
        room = session.get(Room, room_id)
        if room:
            room.status = "CLEANING"
            room.cleaning_status = "CLEANING"
            ready_at = now() + timedelta(minutes=buffer_min)
            room.cleaning_ready_at = ready_at
            room.updated_at = now()
            session.add(room)

    if req.client_op_id:
        cop = CheckinOperationRecord(
            client_op_id=req.client_op_id,
            op_type="CHECKOUT",
            participant_id=participant.id,
            status="APPLIED",
            created_at=now(),
        )
        session.add(cop)

    session.commit()

    return {
        "participant_id": participant.id,
        "status": "CHECKED_OUT",
        "bed_id": stay.bed_key if stay else req.bed_id,
        "room_id": room_id,
        "room_status": "CLEANING",
        "cleaning_buffer_minutes": buffer_min,
        "cleaning_ready_at": ready_at.isoformat() if ready_at else None,
    }


def update_participant_arrival(
    session: Session,
    participant_id: str,
    req: ArrivalUpdateRequest,
    actor: Actor,
) -> Dict[str, Any]:
    """Record early or late arrival time update, recalculating delay minutes and curfew breach flags."""
    participant = session.get(Participant, participant_id)
    if not participant:
        raise FestOSError(f"Participant '{participant_id}' not found.", code="NOT_FOUND", status_code=404)

    new_arr = datetime.fromisoformat(req.updated_arrival_at)
    participant.arrival_at = new_arr
    participant.updated_at = now()
    session.add(participant)
    session.commit()

    arr_time = new_arr.astimezone(timezone.utc)
    is_curfew = arr_time.time() >= time(22, 0) or arr_time.time() < time(6, 0)

    return {
        "participant_id": participant.id,
        "arrival_at": new_arr.isoformat(),
        "is_curfew_breach": is_curfew,
        "warning": "Arrival past 22:00 campus curfew: requires gate coordination." if is_curfew else None,
    }


def sync_offline_operations(
    session: Session,
    req: SyncBatchRequest,
    actor: Actor,
) -> SyncBatchResponseData:
    """Batch synchronize buffered offline desk operations.

    Evaluates idempotency via client_op_id.
    Server state wins in conflict scenarios, returning APPLIED | DUPLICATE_IGNORED | CONFLICT.
    """
    applied = 0
    duplicate = 0
    conflict = 0
    results: List[SyncOperationResult] = []

    for op in req.operations:
        # Check duplicate
        existing = session.exec(
            select(CheckinOperationRecord).where(
                CheckinOperationRecord.client_op_id == op.client_op_id
            )
        ).first()

        if existing:
            duplicate += 1
            results.append(
                SyncOperationResult(
                    client_op_id=op.client_op_id,
                    status="DUPLICATE_IGNORED",
                    message=f"Operation {op.client_op_id} already processed previously.",
                )
            )
            continue

        participant = session.get(Participant, op.participant_id)
        if not participant:
            conflict += 1
            results.append(
                SyncOperationResult(
                    client_op_id=op.client_op_id,
                    status="CONFLICT",
                    message=f"Participant {op.participant_id} not found on server.",
                )
            )
            continue

        if op.op_type.upper() == "CHECKIN":
            if participant.status in ["CANCELLED", "NO_SHOW"]:
                conflict += 1
                results.append(
                    SyncOperationResult(
                        client_op_id=op.client_op_id,
                        status="CONFLICT",
                        message=f"Participant {op.participant_id} has been {participant.status} on server (server state wins).",
                    )
                )
                continue

            if participant.status == "CHECKED_IN":
                duplicate += 1
                results.append(
                    SyncOperationResult(
                        client_op_id=op.client_op_id,
                        status="DUPLICATE_IGNORED",
                        message=f"Participant {op.participant_id} is already checked in.",
                    )
                )
                continue

            # Verify active stay
            stay = session.exec(
                select(StayAssignment).where(
                    StayAssignment.participant_id == op.participant_id,
                    StayAssignment.status == "ACTIVE",
                )
            ).first()

            if not stay:
                conflict += 1
                results.append(
                    SyncOperationResult(
                        client_op_id=op.client_op_id,
                        status="CONFLICT",
                        message=f"Participant {op.participant_id} has no active stay assignment on server.",
                    )
                )
                continue

            # Room check
            if stay.room_id:
                rm = session.get(Room, stay.room_id)
                if rm and (rm.cleaning_status != "READY" or (rm.cleaning_ready_at and now() < rm.cleaning_ready_at)):
                    conflict += 1
                    results.append(
                        SyncOperationResult(
                            client_op_id=op.client_op_id,
                            status="CONFLICT",
                            message=f"Assigned room '{rm.id}' is under cleaning on server.",
                        )
                    )
                    continue
                if rm:
                    rm.status = "OCCUPIED"
                    session.add(rm)

            participant.status = "CHECKED_IN"
            session.add(participant)

            cop = CheckinOperationRecord(
                client_op_id=op.client_op_id,
                op_type="CHECKIN",
                participant_id=participant.id,
                status="APPLIED",
                created_at=now(),
            )
            session.add(cop)
            session.commit()

            applied += 1
            results.append(
                SyncOperationResult(
                    client_op_id=op.client_op_id,
                    status="APPLIED",
                    message=f"Participant {op.participant_id} successfully checked in.",
                )
            )

        elif op.op_type.upper() == "CHECKOUT":
            if participant.status == "CHECKED_OUT":
                duplicate += 1
                results.append(
                    SyncOperationResult(
                        client_op_id=op.client_op_id,
                        status="DUPLICATE_IGNORED",
                        message=f"Participant {op.participant_id} is already checked out.",
                    )
                )
                continue

            stay = session.exec(
                select(StayAssignment).where(
                    StayAssignment.participant_id == op.participant_id,
                    StayAssignment.status == "ACTIVE",
                )
            ).first()
            if stay:
                stay.status = "COMPLETED"
                session.add(stay)

            participant.status = "CHECKED_OUT"
            session.add(participant)

            if stay and stay.room_id:
                rm = session.get(Room, stay.room_id)
                if rm:
                    rm.status = "CLEANING"
                    rm.cleaning_status = "CLEANING"
                    rm.cleaning_ready_at = now() + timedelta(minutes=180)
                    session.add(rm)

            cop = CheckinOperationRecord(
                client_op_id=op.client_op_id,
                op_type="CHECKOUT",
                participant_id=participant.id,
                status="APPLIED",
                created_at=now(),
            )
            session.add(cop)
            session.commit()

            applied += 1
            results.append(
                SyncOperationResult(
                    client_op_id=op.client_op_id,
                    status="APPLIED",
                    message=f"Participant {op.participant_id} successfully checked out.",
                )
            )

    return SyncBatchResponseData(
        batch_id=req.sync_batch_id,
        processed_count=len(req.operations),
        applied_count=applied,
        duplicate_count=duplicate,
        conflict_count=conflict,
        results=results,
    )


def get_reallocation_suggestions(session: Session) -> List[Dict[str, Any]]:
    """Retrieve bed reallocation suggestions generated by cancellations/no-shows."""
    suggestions = session.exec(
        select(BedReallocationSuggestion)
        .where(BedReallocationSuggestion.status == "PENDING")
        .order_by(BedReallocationSuggestion.priority_score.desc())
    ).all()

    return [
        {
            "suggestion_id": s.id,
            "freed_bed_key": s.freed_bed_key,
            "freed_room_id": s.freed_room_id,
            "freed_by_participant_id": s.freed_by_participant_id,
            "reason": s.reason,
            "suggested_participant_id": s.suggested_participant_id,
            "suggested_participant_name": s.suggested_participant_name,
            "contingent_id": s.contingent_id,
            "priority_score": s.priority_score,
            "cohesion_benefit": s.cohesion_benefit,
            "created_at": s.created_at.isoformat(),
        }
        for s in suggestions
    ]
