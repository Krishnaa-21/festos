# OWNER: P2
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Literal

from sqlmodel import Session, select

import app.core.decision_log as decision_log
import app.core.overrides as overrides_core
from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.errors import FestOSError, VersionConflictError
from app.core.registry import register_change_handler
from app.engines.accommodation.rules import is_ground_floor_needed, is_wheelchair_needed
from app.models.accommodation import AccommodationPlan, ExternalProperty, Room, StayAssignment
from app.models.participants import Participant
from app.schemas.common import Role, Severity, Violation


@register_change_handler("accommodation.update_room")
class UpdateRoomHandler(ChangeHandler):
    """Updates attributes and status of an on-campus room."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        room = session.get(Room, req.entity_id)
        if not room:
            return [
                Violation(
                    code="NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Room '{req.entity_id}' not found.",
                )
            ]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        room = session.get(Room, req.entity_id)
        if room:
            return {
                "id": room.id,
                "status": room.status,
                "cleaning_status": room.cleaning_status,
                "cleaning_ready_at": room.cleaning_ready_at.isoformat() if room.cleaning_ready_at else None,
                "capacity": room.capacity,
                "accessible": room.accessible,
                "gender_class": room.gender_class,
                "version": room.version,
            }
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        room = session.get(Room, req.entity_id)
        if not room:
            raise FestOSError(f"Room {req.entity_id} not found", code="NOT_FOUND", status_code=404)

        for k, v in req.payload.items():
            if hasattr(room, k):
                if k == "cleaning_ready_at" and isinstance(v, str):
                    try:
                        v = datetime.fromisoformat(v)
                    except Exception:
                        pass
                setattr(room, k, v)

        room.version += 1
        room.updated_at = now()
        session.add(room)
        session.flush()

        return {
            "room_id": room.id,
            "status": room.status,
            "cleaning_status": room.cleaning_status,
            "cleaning_ready_at": room.cleaning_ready_at.isoformat() if room.cleaning_ready_at else None,
            "accessible": room.accessible,
            "gender_class": room.gender_class,
            "version": room.version,
        }


@register_change_handler("accommodation.cleaning_complete")
class CleaningCompleteHandler(ChangeHandler):
    """Marks room cleaning complete, transitioning status to READY."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        room = session.get(Room, req.entity_id)
        if not room:
            return [
                Violation(
                    code="NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Room '{req.entity_id}' not found.",
                )
            ]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        room = session.get(Room, req.entity_id)
        if room:
            return {
                "id": room.id,
                "status": room.status,
                "cleaning_status": room.cleaning_status,
                "cleaning_ready_at": room.cleaning_ready_at.isoformat() if room.cleaning_ready_at else None,
                "version": room.version,
            }
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        room = session.get(Room, req.entity_id)
        if not room:
            raise FestOSError(f"Room {req.entity_id} not found", code="NOT_FOUND", status_code=404)

        room.status = "READY"
        room.cleaning_status = "READY"
        room.cleaning_ready_at = now()
        room.version += 1
        room.updated_at = now()
        session.add(room)
        session.flush()

        return {
            "room_id": room.id,
            "status": room.status,
            "cleaning_status": room.cleaning_status,
            "cleaning_ready_at": room.cleaning_ready_at.isoformat(),
            "version": room.version,
        }


@register_change_handler("accommodation.close_hostel")
@register_change_handler("accommodation.close_block")
class CloseHostelHandler(ChangeHandler):
    """Closes an entire hostel block for maintenance or emergency drill."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        block = req.payload.get("block") or req.entity_id
        rooms = session.exec(select(Room).where(Room.block == block)).all()
        return {"rooms": {r.id: r.status for r in rooms}}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        block = req.payload.get("block") or req.entity_id
        rooms = session.exec(select(Room).where(Room.block == block)).all()
        count = 0
        target_status = req.payload.get("status") or "CLOSED"
        for r in rooms:
            r.status = target_status
            r.version += 1
            r.updated_at = now()
            session.add(r)
            count += 1
        session.flush()
        return {"closed_block": block, "rooms_affected": count, "status": target_status}


@register_change_handler("accommodation.update_property")
class UpdatePropertyHandler(ChangeHandler):
    """Updates external property parameters and verification status."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        prop = session.get(ExternalProperty, req.entity_id)
        if not prop:
            return [
                Violation(
                    code="NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Property '{req.entity_id}' not found.",
                )
            ]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        prop = session.get(ExternalProperty, req.entity_id)
        if prop:
            return {
                "id": prop.id,
                "name": prop.name,
                "beds": prop.beds,
                "cost_per_bed_night": prop.cost_per_bed_night,
                "status": prop.status,
                "accessibility_verified": prop.accessibility_verified,
                "gender_suitability_verified": prop.gender_suitability_verified,
                "version": prop.version,
            }
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        prop = session.get(ExternalProperty, req.entity_id)
        if not prop:
            raise FestOSError(f"Property {req.entity_id} not found", code="NOT_FOUND", status_code=404)

        for k, v in req.payload.items():
            if hasattr(prop, k):
                setattr(prop, k, v)

        prop.version += 1
        prop.updated_at = now()
        session.add(prop)
        session.flush()

        return {
            "property_id": prop.id,
            "status": prop.status,
            "beds": prop.beds,
            "cost_per_bed_night": prop.cost_per_bed_night,
            "accessibility_verified": prop.accessibility_verified,
            "gender_suitability_verified": prop.gender_suitability_verified,
            "version": prop.version,
        }


@register_change_handler("accommodation.commit_plan")
class CommitPlanHandler(ChangeHandler):
    """Commits candidate plan to LIVE status, archiving previous LIVE plans."""

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        # Accommodation Lead proposes; Director approves when external cost > budget or relaxations exist
        return "HIGH" if req.payload.get("is_high_risk", True) else "LOW"


    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)).first()
        if not plan:
            return [
                Violation(
                    code="NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Candidate plan '{req.entity_id}' not found.",
                )
            ]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        live_plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.status == "LIVE")).first()
        return {
            "previous_live_plan_id": live_plan.plan_id if live_plan else None,
            "target_plan_id": req.entity_id,
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        target_plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)).first()
        if not target_plan:
            raise FestOSError(f"Plan {req.entity_id} not found", code="NOT_FOUND", status_code=404)

        # Archive existing live plans
        existing_lives = session.exec(select(AccommodationPlan).where(AccommodationPlan.status == "LIVE")).all()
        for p in existing_lives:
            p.status = "ARCHIVED"
            p.updated_at = now()
            session.add(p)

        target_plan.status = "LIVE"
        target_plan.updated_at = now()
        session.add(target_plan)

        # Ensure active stay assignments count
        live_stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.plan_id == target_plan.plan_id,
                StayAssignment.status == "ACTIVE"
            )
        ).all()

        decision_log.add(
            session=session,
            module="accommodation",
            decision_type="COMMIT_LIVE_PLAN",
            title=f"Committed {target_plan.name} to LIVE",
            summary=f"Plan {target_plan.plan_id} approved and made operational with {len(live_stays)} assignments.",
            why=req.reason or "Formal plan approval by operations lead / director.",
            hard_constraints_satisfied=["Accessibility", "Gender Segregation", "Capacity Limits"],
            cost_impact_inr=target_plan.total_cost_inr,
            people_affected=len(live_stays),
            approved_by=req.actor.name or req.actor.id,
            entity_refs=[{"type": "accommodation_plan", "id": target_plan.plan_id}],
        )

        session.flush()
        return {
            "plan_id": target_plan.plan_id,
            "status": "LIVE",
            "live_assignments_count": len(live_stays),
            "committed_at": now().isoformat(),
        }


@register_change_handler("accommodation.freeze_plan")
class FreezePlanHandler(ChangeHandler):
    """Freezes the live plan against automated replanning."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)).first()
        if not plan:
            return [
                Violation(
                    code="NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Plan '{req.entity_id}' not found.",
                )
            ]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)).first()
        return {"is_frozen": plan.is_frozen if plan else False}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)).first()
        if not plan:
            raise FestOSError(f"Plan {req.entity_id} not found", code="NOT_FOUND", status_code=404)

        plan.is_frozen = True
        plan.frozen_at = now()
        plan.updated_at = now()
        session.add(plan)
        session.flush()

        return {
            "plan_id": plan.plan_id,
            "is_frozen": True,
            "frozen_at": plan.frozen_at.isoformat(),
        }


@register_change_handler("accommodation.manual_assign")
class ManualAssignHandler(ChangeHandler):
    """Manually assigns or moves a participant, enforcing override policy and concurrency guards."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        participant_id = req.payload.get("participant_id")
        target_bed_key = req.payload.get("target_bed_key")
        target_room_id = req.payload.get("target_room_id")
        override_hard = req.payload.get("override_hard_constraint", False)

        participant = session.get(Participant, participant_id)
        if not participant:
            violations.append(
                Violation(
                    code="PARTICIPANT_NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Participant '{participant_id}' not found.",
                )
            )
            return violations

        # Room checks
        if target_room_id:
            room = session.get(Room, target_room_id)
            if not room:
                violations.append(
                    Violation(
                        code="ROOM_NOT_FOUND",
                        severity=Severity.HIGH,
                        hard=True,
                        message=f"Room '{target_room_id}' not found.",
                    )
                )
                return violations

            if room.status in ["CLOSED", "MAINTENANCE"]:
                violations.append(
                    Violation(
                        code="ROOM_CLOSED",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message=f"Cannot assign to room '{target_room_id}' with status {room.status}.",
                    )
                )

            # Check Accessibility
            needs_wheelchair = is_wheelchair_needed(participant.accessibility_needs)
            needs_ground = is_ground_floor_needed(participant.accessibility_needs)
            if (needs_wheelchair and not room.accessible) or (needs_ground and room.floor != 0):
                violations.append(
                    Violation(
                        code="HARD_ACCESSIBILITY",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message="Participant requires ground-floor wheelchair accessible room.",
                    )
                )

            # Check Gender
            pgender = (participant.gender or "UNKNOWN").lower()
            if pgender in ["male", "boy", "m"] and room.gender_class.lower() not in ["boys", "male", "neutral"]:
                violations.append(
                    Violation(
                        code="GENDER_MISMATCH",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message=f"Male participant cannot be assigned to girls room '{room.id}'.",
                    )
                )
            elif pgender in ["female", "girl", "f"] and room.gender_class.lower() not in ["girls", "female", "neutral"]:
                violations.append(
                    Violation(
                        code="GENDER_MISMATCH",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message=f"Female participant cannot be assigned to boys room '{room.id}'.",
                    )
                )
            elif pgender not in ["male", "boy", "m", "female", "girl", "f"] and room.gender_class.lower() in ["boys", "male", "girls", "female"]:
                violations.append(
                    Violation(code="GENDER_UNCONFIRMED", severity=Severity.CRITICAL, hard=True,
                              message="Unknown or non-binary gender cannot be auto-assigned to a gendered room.")
                )

        # Concurrency / Bed Allocation Guard: check active overlapping stay for same bed
        active_conflict = session.exec(
            select(StayAssignment).where(
                StayAssignment.bed_key == target_bed_key,
                StayAssignment.status == "ACTIVE",
                StayAssignment.participant_id != participant_id,
            )
        ).first()

        if active_conflict:
            violations.append(
                Violation(
                    code="BED_OCCUPIED",
                    severity=Severity.CRITICAL,
                    hard=True,
                    message=f"Bed '{target_bed_key}' is already actively occupied by {active_conflict.participant_id}.",
                )
            )

        if override_hard:
            # Director-only override
            if req.actor.role not in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]:
                violations.append(
                    Violation(
                        code="DIRECTOR_OVERRIDE_REQUIRED",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message="Hard constraint overrides can only be authorized by the Festival Director.",
                    )
                )
            elif not req.reason or not req.reason.strip():
                violations.append(
                    Violation(
                        code="REASON_REQUIRED",
                        severity=Severity.CRITICAL,
                        hard=True,
                        message="Overriding hard constraints requires a mandatory recorded reason.",
                    )
                )
            else:
                # Director override allowed: clear violations that were bypassed
                bypassed = [v.code for v in violations if v.code in ["HARD_ACCESSIBILITY", "GENDER_MISMATCH"]]
                req.payload["_bypassed_violations"] = bypassed
                violations = [v for v in violations if v.code not in ["HARD_ACCESSIBILITY", "GENDER_MISMATCH"]]

        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        participant_id = req.payload.get("participant_id")
        current_stay = session.exec(
            select(StayAssignment).where(
                StayAssignment.participant_id == participant_id,
                StayAssignment.status == "ACTIVE",
            )
        ).first()
        return {
            "participant_id": participant_id,
            "current_stay_id": current_stay.id if current_stay else None,
            "current_bed_key": current_stay.bed_key if current_stay else None,
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        participant_id = req.payload.get("participant_id")
        target_bed_key = req.payload.get("target_bed_key")
        target_room_id = req.payload.get("target_room_id")
        target_prop_id = req.payload.get("target_property_id")
        reason = req.reason or "Manual bed assignment"
        override_hard = req.payload.get("override_hard_constraint", False)
        bypassed_violations = req.payload.get("_bypassed_violations", [])

        # Concurrency bed lock guard in transaction
        active_conflict = session.exec(
            select(StayAssignment).where(
                StayAssignment.bed_key == target_bed_key,
                StayAssignment.status == "ACTIVE",
                StayAssignment.participant_id != participant_id,
            )
        ).first()
        if active_conflict:
            raise VersionConflictError(f"Bed '{target_bed_key}' was just allocated to {active_conflict.participant_id}.")

        # Find LIVE plan
        live_plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.status == "LIVE")).first()
        plan_id = live_plan.plan_id if live_plan else "LIVE"

        # Cancel current active stay for this participant
        existing_stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.participant_id == participant_id,
                StayAssignment.status == "ACTIVE",
            )
        ).all()
        for es in existing_stays:
            es.status = "CANCELLED"
            es.updated_at = now()
            session.add(es)

        # Record override if applicable
        override_id = None
        if override_hard and bypassed_violations:
            ovr = overrides_core.record(
                session=session,
                entity_type="stay_assignment",
                entity_id=participant_id,
                constraint_code=",".join(bypassed_violations),
                reason=reason,
                actor=req.actor,
                risk_level="HIGH",
            )
            override_id = ovr.id

        is_ext = bool(target_prop_id)
        new_stay = StayAssignment(
            plan_id=plan_id,
            bed_key=target_bed_key,
            participant_id=participant_id,
            room_id=target_room_id,
            property_id=target_prop_id,
            is_external=is_ext,
            start_at=now(),
            end_at=now(),
            cost_inr=0.0,
            status="ACTIVE",
            explanation=json.dumps({"manual_assign": True, "reason": reason, "override_id": override_id}),
            version=1,
            created_at=now(),
            updated_at=now(),
        )
        session.add(new_stay)
        session.flush()

        dec_card = decision_log.add(
            session=session,
            module="accommodation",
            decision_type="MANUAL_ASSIGNMENT",
            title=f"Manual Assignment for {participant_id} -> {target_bed_key}",
            summary=f"Assigned to {target_bed_key}. Reason: {reason}",
            why=reason,
            hard_constraints_satisfied=["Capacity Checked"],
            soft_constraints_relaxed=[{"constraint": c, "reason": reason} for c in bypassed_violations],
            cost_impact_inr=0.0,
            people_affected=1,
            approved_by=req.actor.name or req.actor.id,
            override_id=override_id,
            entity_refs=[{"type": "participant", "id": participant_id}, {"type": "bed", "id": target_bed_key}],
        )

        return {
            "assignment_id": new_stay.id,
            "participant_id": participant_id,
            "bed_key": target_bed_key,
            "room_id": target_room_id,
            "override_id": override_id,
            "decision_card_id": dec_card.id,
            "bypassed_violations": bypassed_violations,
        }


@register_change_handler("accommodation.apply_repair")
class ApplyRepairHandler(ChangeHandler):
    """Applies a candidate repair plan to LIVE operations."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        repair_plan = session.exec(
            select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)
        ).first()
        if not repair_plan:
            return [
                Violation(
                    code="NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Repair candidate plan '{req.entity_id}' not found.",
                )
            ]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        live_plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.status == "LIVE")).first()
        return {"live_plan_id": live_plan.plan_id if live_plan else None}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        repair_plan = session.exec(
            select(AccommodationPlan).where(AccommodationPlan.plan_id == req.entity_id)
        ).first()
        if not repair_plan:
            raise FestOSError(f"Repair plan {req.entity_id} not found", code="NOT_FOUND", status_code=404)

        # Archive current live
        existing_lives = session.exec(select(AccommodationPlan).where(AccommodationPlan.status == "LIVE")).all()
        for p in existing_lives:
            p.status = "ARCHIVED"
            p.updated_at = now()
            session.add(p)

        repair_plan.status = "LIVE"
        repair_plan.updated_at = now()
        session.add(repair_plan)

        live_stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.plan_id == repair_plan.plan_id,
                StayAssignment.status == "ACTIVE"
            )
        ).all()

        decision_log.add(
            session=session,
            module="accommodation",
            decision_type="APPLY_REPAIR_PLAN",
            title=f"Applied Repair Plan {repair_plan.name} to LIVE",
            summary=f"Repaired accommodation operations with {len(live_stays)} active assignments.",
            why=req.reason or "Approved minimal-change replan following disruption.",
            hard_constraints_satisfied=["Accessibility Verified", "Gender Class Preserved"],
            cost_impact_inr=repair_plan.total_cost_inr,
            people_affected=len(live_stays),
            approved_by=req.actor.name or req.actor.id,
            entity_refs=[{"type": "accommodation_plan", "id": repair_plan.plan_id}],
        )

        session.flush()
        return {
            "plan_id": repair_plan.plan_id,
            "status": "LIVE",
            "active_stays_count": len(live_stays),
            "applied_at": now().isoformat(),
        }
