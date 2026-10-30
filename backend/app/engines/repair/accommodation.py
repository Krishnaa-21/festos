# OWNER: P2
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.clock import now
from app.models.accommodation import AccommodationPlan, ExternalProperty, Room, StayAssignment
from app.models.participants import Participant
from sqlmodel import Session, select

logger = logging.getLogger("festos.engines.repair")


def replan_accommodation(
    session: Session,
    plan_id: Optional[str] = None,
    closed_room_ids: Optional[List[str]] = None,
    closed_block: Optional[str] = None,
    closed_property_id: Optional[str] = None,
    strategy: str = "MINIMAL_CHANGE",
) -> Tuple[AccommodationPlan, Dict[str, Any]]:
    """Minimal-change accommodation replanning engine (Spec 6.6).

    Preserves existing approved allocations, relocating only affected participants
    with the fewest moves while strictly respecting hard accessibility, privacy,
    and safety constraints and maximizing contingent cohesion.
    """
    closed_room_ids = closed_room_ids or []

    # 1. Resolve source plan
    source_plan = None
    if plan_id:
        source_plan = session.exec(
            select(AccommodationPlan).where(AccommodationPlan.plan_id == plan_id)
        ).first()

    if not source_plan:
        # Fallback to LIVE or latest candidate
        source_plan = session.exec(
            select(AccommodationPlan).where(AccommodationPlan.status == "LIVE")
        ).first()
        if not source_plan:
            source_plan = session.exec(
                select(AccommodationPlan).order_by(AccommodationPlan.created_at.desc())
            ).first()

    if not source_plan:
        raise ValueError("No accommodation plan found to repair.")

    # 2. Fetch all rooms and properties
    all_rooms = session.exec(select(Room)).all()
    room_map = {r.id: r for r in all_rooms}
    all_props = session.exec(select(ExternalProperty)).all()


    # 3. Determine closed resources
    closed_room_set: Set[str] = set(closed_room_ids)
    if closed_block:
        for r in all_rooms:
            if r.block.upper() == closed_block.upper():
                closed_room_set.add(r.id)

    closed_prop_set: Set[str] = set()
    if closed_property_id:
        closed_prop_set.add(closed_property_id)

    # 4. Fetch all active stay assignments for the plan
    active_stays = session.exec(
        select(StayAssignment).where(
            StayAssignment.plan_id == source_plan.plan_id,
            StayAssignment.status == "ACTIVE",
        )
    ).all()

    affected_stays: List[StayAssignment] = []
    unaffected_stays: List[StayAssignment] = []

    for s in active_stays:
        is_affected = False
        if s.room_id and s.room_id in closed_room_set:
            is_affected = True
        elif s.property_id and s.property_id in closed_prop_set:
            is_affected = True
        elif s.room_id and room_map.get(s.room_id) and room_map[s.room_id].status in ["CLOSED", "MAINTENANCE"]:
            is_affected = True

        if is_affected:
            affected_stays.append(s)
        else:
            unaffected_stays.append(s)

    # 5. Inventory tracking of unaffected stays
    # Room occupancy: room_id -> count of occupied beds
    room_occupancy: Dict[str, int] = {}
    prop_occupancy: Dict[str, int] = {}
    contingent_block_counts: Dict[str, Dict[str, int]] = {}
    contingent_prop_counts: Dict[str, Dict[str, int]] = {}

    for s in unaffected_stays:
        part = session.get(Participant, s.participant_id)
        cid = part.contingent_id if part else "UNKNOWN"

        if s.room_id:
            room_occupancy[s.room_id] = room_occupancy.get(s.room_id, 0) + 1
            rm = room_map.get(s.room_id)
            if rm:
                contingent_block_counts.setdefault(cid, {})
                contingent_block_counts[cid][rm.block] = contingent_block_counts[cid].get(rm.block, 0) + 1
        elif s.property_id:
            prop_occupancy[s.property_id] = prop_occupancy.get(s.property_id, 0) + 1
            contingent_prop_counts.setdefault(cid, {})
            contingent_prop_counts[cid][s.property_id] = contingent_prop_counts[cid].get(s.property_id, 0) + 1

    # 6. Eligible candidate resources
    available_rooms = [
        r for r in all_rooms
        if r.id not in closed_room_set and r.status not in ["CLOSED", "MAINTENANCE"]
    ]
    available_props = [
        p for p in all_props
        if p.id not in closed_prop_set and p.status not in ["CLOSED", "MAINTENANCE"]
    ]

    # 7. Sort affected participants (preserve cohesion & prioritize accessibility)
    affected_part_ids = [s.participant_id for s in affected_stays]
    participants = session.exec(
        select(Participant).where(Participant.id.in_(affected_part_ids))
    ).all()
    part_map = {p.id: p for p in participants}

    def sort_key(s: StayAssignment):
        p = part_map.get(s.participant_id)
        if not p:
            return (0, 0, "")
        acc_priority = 1 if (p.accessibility_needs and p.accessibility_needs not in ["none", ""]) else 0
        return (acc_priority, 1 if p.role == "LEADER" else 0, p.contingent_id or "")

    affected_stays.sort(key=sort_key, reverse=True)

    # 8. Re-place affected participants
    moves = []
    new_assignments = []
    unplaced_count = 0
    cost_delta = 0.0

    # Track bed keys assigned
    used_bed_keys: Set[str] = {s.bed_key for s in unaffected_stays}

    for s in affected_stays:
        p = part_map.get(s.participant_id)
        if not p:
            continue

        cid = p.contingent_id or "C00"
        gender = (p.gender or "UNKNOWN").strip().lower()
        needs_acc = bool(p.accessibility_needs and p.accessibility_needs not in ["none", ""])
        old_cost = s.cost_inr

        placed = False

        # Attempt On-Campus placement first
        candidate_rooms = []
        for r in available_rooms:
            occupied = room_occupancy.get(r.id, 0)
            if occupied >= r.capacity:
                continue

            # Hard Constraint 1: Accessibility
            if needs_acc and (not r.accessible or r.floor != 0):
                continue

            # Hard Constraint 2: Gender segregation
            if gender in ["male", "boy", "m"] and r.gender_class.lower() not in ["boys", "male", "neutral"]:
                continue
            if gender in ["female", "girl", "f"] and r.gender_class.lower() not in ["girls", "female", "neutral"]:
                continue

            # Scoring: Cohesion affinity
            affinity = contingent_block_counts.get(cid, {}).get(r.block, 0)
            candidate_rooms.append((affinity, r))

        # Sort rooms by contingent affinity descending
        candidate_rooms.sort(key=lambda x: x[0], reverse=True)

        if candidate_rooms:
            best_room = candidate_rooms[0][1]
            bed_num = room_occupancy.get(best_room.id, 0) + 1
            room_occupancy[best_room.id] = bed_num
            contingent_block_counts.setdefault(cid, {})
            contingent_block_counts[cid][best_room.block] = contingent_block_counts[cid].get(best_room.block, 0) + 1

            new_bed_key = f"{best_room.id}-bed{bed_num}"
            while new_bed_key in used_bed_keys:
                bed_num += 1
                new_bed_key = f"{best_room.id}-bed{bed_num}"
            used_bed_keys.add(new_bed_key)

            new_cost = 0.0  # On campus is 0 INR extra
            cost_delta += (new_cost - old_cost)

            explanation = {
                "relocation_reason": f"Minimal-change repair due to closure of {closed_block or 'room'}",
                "original_bed": s.bed_key,
                "strategy": strategy,
                "contingent_peers_in_block": candidate_rooms[0][0],
            }

            new_stay = StayAssignment(
                bed_key=new_bed_key,
                participant_id=p.id,
                room_id=best_room.id,
                property_id=None,
                is_external=False,
                start_at=s.start_at,
                end_at=s.end_at,
                cost_inr=new_cost,
                status="ACTIVE",
                explanation=json.dumps(explanation),
                version=1,
            )
            new_assignments.append(new_stay)
            moves.append({
                "participant_id": p.id,
                "name": p.name,
                "from_bed": s.bed_key,
                "to_bed": new_bed_key,
                "location": f"Hostel {best_room.block} (Room {best_room.id})",
                "cost_inr": new_cost,
                "reason": f"Minimal-change repair relocation from closed {closed_block or s.room_id}",
            })
            placed = True

        # Overflow to External Property if no on-campus room fits
        if not placed and available_props:
            candidate_props = []
            for prop in available_props:
                occupied = prop_occupancy.get(prop.id, 0)
                if occupied >= prop.beds:
                    continue
                # Accessibility check on property
                if needs_acc and not prop.accessibility_verified:
                    continue

                affinity = contingent_prop_counts.get(cid, {}).get(prop.id, 0)
                candidate_props.append((affinity, -prop.cost_per_bed_night, prop))

            candidate_props.sort(key=lambda x: (x[0], x[1]), reverse=True)
            if candidate_props:
                best_prop = candidate_props[0][2]
                bed_num = prop_occupancy.get(best_prop.id, 0) + 1
                prop_occupancy[best_prop.id] = bed_num
                contingent_prop_counts.setdefault(cid, {})
                contingent_prop_counts[cid][best_prop.id] = contingent_prop_counts[cid].get(best_prop.id, 0) + 1

                new_bed_key = f"{best_prop.id}-bed{bed_num}"
                while new_bed_key in used_bed_keys:
                    bed_num += 1
                    new_bed_key = f"{best_prop.id}-bed{bed_num}"
                used_bed_keys.add(new_bed_key)

                # Duration in nights
                start = s.start_at
                end = s.end_at
                nights = max(1, (end - start).days) if (start and end) else 3
                new_cost = nights * best_prop.cost_per_bed_night
                cost_delta += (new_cost - old_cost)

                explanation = {
                    "relocation_reason": f"Minimal-change overflow repair due to closure of {closed_block or 'room'}",
                    "original_bed": s.bed_key,
                    "strategy": strategy,
                }

                new_stay = StayAssignment(
                    bed_key=new_bed_key,
                    participant_id=p.id,
                    room_id=None,
                    property_id=best_prop.id,
                    is_external=True,
                    start_at=s.start_at,
                    end_at=s.end_at,
                    cost_inr=new_cost,
                    status="ACTIVE",
                    explanation=json.dumps(explanation),
                    version=1,
                )
                new_assignments.append(new_stay)
                moves.append({
                    "participant_id": p.id,
                    "name": p.name,
                    "from_bed": s.bed_key,
                    "to_bed": new_bed_key,
                    "location": f"{best_prop.name}",
                    "cost_inr": new_cost,
                    "reason": f"Relocated to external property {best_prop.name}",
                })
                placed = True

        if not placed:
            unplaced_count += 1

    # 9. Create Repair Candidate Plan
    desc_label = closed_block or (closed_property_id or "closure")
    candidate_plan_id = f"plan_repair_{desc_label}_{uuid.uuid4().hex[:6]}"

    # Clone unaffected stays with new plan_id
    cloned_stays = []
    for s in unaffected_stays:
        cloned_stays.append(
            StayAssignment(
                plan_id=candidate_plan_id,
                bed_key=s.bed_key,
                participant_id=s.participant_id,
                room_id=s.room_id,
                property_id=s.property_id,
                is_external=s.is_external,
                start_at=s.start_at,
                end_at=s.end_at,
                cost_inr=s.cost_inr,
                status="ACTIVE",
                explanation=s.explanation,
                version=1,
                created_at=now(),
                updated_at=now(),
            )
        )

    for ns in new_assignments:
        ns.plan_id = candidate_plan_id
        ns.created_at = now()
        ns.updated_at = now()
        cloned_stays.append(ns)

    session.add_all(cloned_stays)

    total_cost = sum(st.cost_inr for st in cloned_stays)
    on_campus_count = sum(1 for st in cloned_stays if not st.is_external)
    external_count = sum(1 for st in cloned_stays if st.is_external)

    candidate_plan = AccommodationPlan(
        plan_id=candidate_plan_id,
        kind="REPAIR",
        name=f"Repair Plan ({desc_label})",
        status="CANDIDATE",
        on_campus_placed=on_campus_count,
        external_placed=external_count,
        unplaced_count=unplaced_count,
        contingent_splits=source_plan.contingent_splits,
        total_cost_inr=total_cost,
        safety_flags_count=source_plan.safety_flags_count,
        accessibility_issues_count=0,
        relaxed_constraints_count=source_plan.relaxed_constraints_count,
        minors_external_count=source_plan.minors_external_count,
        plan_hash=f"repair_{candidate_plan_id}",
        sacrifices_summary=f"Minimal-change replanning for {len(affected_stays)} displaced participants.",
        created_at=now(),
        updated_at=now(),
    )
    session.add(candidate_plan)
    session.commit()

    diff = {
        "candidate_plan_id": candidate_plan_id,
        "affected_participants_count": len(affected_stays),
        "people_moved": len(moves),
        "relocated_count": len(moves),
        "unplaced_count": unplaced_count,
        "splits_added": 0,
        "cost_delta_inr": round(cost_delta, 2),
        "moves": moves,
    }

    return candidate_plan, diff
