# OWNER: P2
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.engines.impact.graph import _normalize_type
from app.models.accommodation import Room, StayAssignment
from app.models.events import EventSession
from app.models.inventory import InventoryItem
from app.models.participants import Participant
from app.models.vendors import Vendor
from app.schemas.impact import ImpactReport
from app.schemas.incidents import RecoveryPlanSchema
from sqlmodel import Session, select

logger = logging.getLogger("festos.engines.replan")


def generate_recovery_plans(
    session: Session,
    scenario_type: str,
    entity_type: Optional[str],
    entity_id: Optional[str],
    parameters: Dict[str, Any],
    impact_report: ImpactReport,
    notification_draft_ids: Optional[List[str]] = None,
) -> List[RecoveryPlanSchema]:
    """Minimal-change replanner (Spec 6.6, Task 4).

    Objective order:
    1. Fewest people relocated (people_moved)
    2. Least schedule disruption (schedule_changes)
    3. Least resource movement (resource_moves)
    4. Preserve cohesion (cohesion_score, higher is better)
    5. Least cost increase (cost_increase_inr)
    6. Preserve approved allocations (changes_count)
    """
    sc_type = scenario_type.upper().strip()
    norm_entity = _normalize_type(entity_type or "")
    total_people = impact_report.total_people_affected
    draft_ids = notification_draft_ids or []

    candidate_plans: List[RecoveryPlanSchema] = []

    if sc_type == "HOSTEL_CLOSURE":
        block = parameters.get("block") or (entity_id if norm_entity == "hostel" else "A")
        # Find active stays in this block
        rooms_in_block = session.exec(select(Room).where(Room.block == block)).all()
        room_ids = [r.id for r in rooms_in_block]
        affected_stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.room_id.in_(room_ids),
                StayAssignment.status == "ACTIVE",
            )
        ).all()
        people_count = len(affected_stays) if affected_stays else (total_people or 24)

        # Plan A: Minimal Campus Reassignment (Preserve cohesion, fill campus vacancies)
        # Cost delta is 0 INR since on-campus hostels are already funded.
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Minimal On-Campus Reallocation",
            summary=f"Reallocate {people_count} participants into vacant beds across adjacent on-campus hostel blocks.",
            people_moved=people_count,
            schedule_changes=0,
            resource_moves=len(rooms_in_block),
            cost_increase_inr=0.0,
            cohesion_score=0.92,
            changes_count=people_count + len(rooms_in_block),
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "accommodation.close_block",
                "strategy": "MINIMAL_ON_CAMPUS",
                "block": block,
                "closed_room_ids": room_ids,
                "people_count": people_count,
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: External Hotel Overflow (Guaranteed 100% cohesion, higher cost)
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        ext_cost = float(people_count * 2200)
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: External Hotel Contingent Block",
            summary=f"Transfer all {people_count} participants to external hotel partner to preserve 100% contingent cohesion together.",
            people_moved=people_count,
            schedule_changes=0,
            resource_moves=len(rooms_in_block) + 1,
            cost_increase_inr=ext_cost,
            cohesion_score=1.0,
            changes_count=people_count + len(rooms_in_block) + 1,
            notifications_drafted=len(draft_ids),
            requires_director_approval=True,
            change_set_payload={
                "action": "accommodation.close_block",
                "strategy": "EXTERNAL_HOTEL_OVERFLOW",
                "block": block,
                "closed_room_ids": room_ids,
                "people_count": people_count,
                "estimated_cost_inr": ext_cost,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    elif sc_type == "LATE_CONTINGENT":
        contingent_id = parameters.get("contingent_id") or entity_id or "CONT-001"
        delay_hours = int(parameters.get("delay_hours", 3))
        contingent_members = session.exec(select(Participant).where(Participant.contingent_id == contingent_id)).all()
        people_count = len(contingent_members) if contingent_members else (total_people or 15)

        # Plan A: Window Shift & Allocation Retention (Fewest changes)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Schedule Window Shift & Retain Beds",
            summary=f"Postpone check-in and dining windows for contingent {contingent_id} by {delay_hours}h; retain all approved hostel beds and notify teams.",
            people_moved=0,
            schedule_changes=1,
            resource_moves=0,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=1,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "contingent.delay_arrival",
                "strategy": "SHIFT_WINDOW",
                "contingent_id": contingent_id,
                "delay_hours": delay_hours,
                "people_count": people_count,
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: Emergency Reception Holding & Staggered Induction
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: Emergency Reception Holding Lounge",
            summary="Route late arrivals to 24/7 student center lounge; stagger check-in without modifying competition slot times.",
            people_moved=people_count,
            schedule_changes=2,
            resource_moves=1,
            cost_increase_inr=3500.0,
            cohesion_score=0.85,
            changes_count=people_count + 3,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "contingent.delay_arrival",
                "strategy": "RECEPTION_HOLDING",
                "contingent_id": contingent_id,
                "delay_hours": delay_hours,
                "people_count": people_count,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    elif sc_type == "DUPLICATE_PARTICIPANT":
        p_primary = parameters.get("primary_participant_id") or entity_id or "P-001"
        p_duplicate = parameters.get("duplicate_participant_id") or parameters.get("duplicate_id") or "P-002"

        # Plan A: Merge Duplicate into Primary (Repoint Stays, Regs, Claims)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Merge Duplicate Profile into Primary",
            summary=f"Execute deterministic reconciliation merge: repoint registrations, stay assignments, and merchandise claims from {p_duplicate} to {p_primary}.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=0,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=1,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "participant.merge",
                "primary_id": p_primary,
                "duplicate_id": p_duplicate,
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: Disambiguate with Unique Identifier Suffix
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: Disambiguate Profiles with Unique Suffix",
            summary=f"Maintain both {p_primary} and {p_duplicate} as distinct entities by appending college identity disambiguation suffixes.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=0,
            cost_increase_inr=0.0,
            cohesion_score=0.9,
            changes_count=2,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "participant.disambiguate",
                "primary_id": p_primary,
                "duplicate_id": p_duplicate,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    elif sc_type == "EQUIPMENT_FAILURE":
        item_id = parameters.get("item_id") or entity_id or "EQ-001"
        item = session.get(InventoryItem, item_id)
        item_name = item.name if item else item_id

        # Plan A: Hot-Swap Backup Unit from Inventory (Zero schedule disruption)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Hot-Swap Backup Unit from Central Inventory",
            summary=f"Dispatch idle backup {item_name} from Central Store to venue; preserve all event session schedules.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=1,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=2,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "logistics.equipment_swap",
                "strategy": "HOT_SWAP",
                "item_id": item_id,
                "reason": parameters.get("issue", "Equipment technical malfunction"),
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: Time-Shift Session & Expedited Off-Site Rental
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: Time-Shift Event Session & Expedited Rental",
            summary=f"Delay affected session by 2 hours; procure high-output replacement {item_name} via expedited courier.",
            people_moved=0,
            schedule_changes=1,
            resource_moves=1,
            cost_increase_inr=12000.0,
            cohesion_score=1.0,
            changes_count=3,
            notifications_drafted=len(draft_ids),
            requires_director_approval=True,
            change_set_payload={
                "action": "logistics.equipment_swap",
                "strategy": "EXPEDITED_RENTAL",
                "item_id": item_id,
                "cost_inr": 12000.0,
                "delay_hours": 2,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    elif sc_type == "VENUE_CHANGE":
        venue_id = parameters.get("venue_id") or entity_id or "VEN-001"
        sessions_in_venue = session.exec(select(EventSession).where(EventSession.venue_id == venue_id)).all()
        session_count = len(sessions_in_venue) if sessions_in_venue else 1

        # Plan A: Reassign to Adjacent Matching Venue (Minimal travel)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Reassign Sessions to Adjacent Venue",
            summary=f"Transfer {session_count} scheduled sessions from {venue_id} to closest compatible venue with identical AV equipment.",
            people_moved=total_people or 50,
            schedule_changes=0,
            resource_moves=session_count,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=session_count,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "schedule.change_venue",
                "strategy": "NEAREST_VENUE",
                "old_venue_id": venue_id,
                "new_venue_id": parameters.get("new_venue_id") or parameters.get("replacement_venue_id") or "VEN-002",
                "session_count": session_count,
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: Stagger Sessions into Multi-Purpose Hall
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: Stagger Sessions in Multi-Purpose Hall",
            summary=f"Split and stagger {session_count} sessions into Morning/Evening blocks in Multi-Purpose Hall.",
            people_moved=total_people or 50,
            schedule_changes=session_count,
            resource_moves=session_count * 2,
            cost_increase_inr=2500.0,
            cohesion_score=0.85,
            changes_count=session_count * 2 + 1,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "schedule.change_venue",
                "strategy": "STAGGERED_HALL",
                "old_venue_id": venue_id,
                "new_venue_id": "VEN-MPH-01",
                "session_count": session_count,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    elif sc_type == "VENDOR_SHUTDOWN":
        vendor_id = parameters.get("vendor_id") or entity_id or "VND-001"
        vendor = session.get(Vendor, vendor_id)
        vendor_name = vendor.name if vendor else vendor_id

        # Plan A: Transfer to Primary Backup Vendor (Pre-contracted rates)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Transfer Meal Slots to Approved Backup Vendor",
            summary=f"Reassign affected meal slots from {vendor_name} to qualified secondary backup vendor at negotiated rate.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=1,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=2,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "vendors.shutdown",
                "strategy": "BACKUP_VENDOR",
                "vendor_id": vendor_id,
                "replacement_vendor_id": parameters.get("replacement_vendor_id", "VND-BACKUP-01"),
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: Emergency Outside Catering Contract (Full capacity coverage, higher surge rate)
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: Emergency External Catering Mobilization",
            summary="Mobilize outside industrial caterer to deploy 2 food trucks on campus green.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=2,
            cost_increase_inr=30000.0,
            cohesion_score=1.0,
            changes_count=3,
            notifications_drafted=len(draft_ids),
            requires_director_approval=True,
            change_set_payload={
                "action": "vendors.shutdown",
                "strategy": "EMERGENCY_CATERER",
                "vendor_id": vendor_id,
                "cost_inr": 30000.0,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    elif sc_type == "DUPLICATE_MERCHANDISE_CLAIM":
        claim_id = parameters.get("claim_id") or entity_id or "CLM-001"
        part_id = parameters.get("participant_id") or "P-001"

        # Plan A: Reject Duplicate & Flag Identity (Zero cost, enforce policy)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name="Plan A: Reject Second Claim & Flag Suspected Duplicate",
            summary=f"Reject duplicate merchandise claim {claim_id} for participant {part_id}, log security audit flag, and lock collection.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=0,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=1,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "merchandise.flag_duplicate",
                "strategy": "REJECT_DUPLICATE",
                "claim_id": claim_id,
                "participant_id": part_id,
                "decision": "REJECT",
            },
            notification_draft_ids=draft_ids,
        )

        # Plan B: Authorized Exceptional Replacement (Size exchange / damaged item)
        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name="Plan B: Authorize Exceptional Merchandise Override",
            summary=f"Authorize exceptional second merchandise kit for participant {part_id} under damaged item replacement protocol.",
            people_moved=0,
            schedule_changes=0,
            resource_moves=1,
            cost_increase_inr=650.0,
            cohesion_score=1.0,
            changes_count=2,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "merchandise.flag_duplicate",
                "strategy": "AUTHORIZE_OVERRIDE",
                "claim_id": claim_id,
                "participant_id": part_id,
                "decision": "OVERRIDE_APPROVE",
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    else:
        # Generic / Extra disruption scenarios (BUS_DELAY, STAFF_SHORTAGE, etc.)
        plan_a_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_a = RecoveryPlanSchema(
            plan_id=plan_a_id,
            rank=1,
            name=f"Plan A: Minimal Disruption Mitigation for {sc_type}",
            summary=f"Internal rescheduling and resource absorption for {entity_type or 'resource'} {entity_id or ''}.",
            people_moved=0,
            schedule_changes=1,
            resource_moves=1,
            cost_increase_inr=0.0,
            cohesion_score=1.0,
            changes_count=2,
            notifications_drafted=len(draft_ids),
            requires_director_approval=False,
            change_set_payload={
                "action": "incident.generic_mitigation",
                "strategy": "MINIMAL_INTERNAL",
                "scenario_type": sc_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            notification_draft_ids=draft_ids,
        )

        plan_b_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_b = RecoveryPlanSchema(
            plan_id=plan_b_id,
            rank=2,
            name=f"Plan B: Emergency Buffer Dispatch for {sc_type}",
            summary=f"Dispatch on-call contingency personnel and external reserve units for {sc_type}.",
            people_moved=total_people or 10,
            schedule_changes=1,
            resource_moves=2,
            cost_increase_inr=5000.0,
            cohesion_score=0.9,
            changes_count=4,
            notifications_drafted=len(draft_ids),
            requires_director_approval=True,
            change_set_payload={
                "action": "incident.generic_mitigation",
                "strategy": "EXTERNAL_BUFFER",
                "scenario_type": sc_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            notification_draft_ids=draft_ids,
        )
        candidate_plans = [plan_a, plan_b]

    # Deterministic ranking according to strict objective order
    candidate_plans.sort(
        key=lambda p: (
            p.people_moved,
            p.schedule_changes,
            p.resource_moves,
            -p.cohesion_score,
            p.cost_increase_inr,
            p.changes_count,
        )
    )

    for idx, plan in enumerate(candidate_plans, start=1):
        plan.rank = idx

    return candidate_plans
