# OWNER: P1
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.bus import publish
from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.change import Assumption
from app.models.transport import GuardianApproval, ShuttleAssignment, ShuttleRun
from app.schemas.common import Violation

logger = logging.getLogger("festos.transport.handlers")


@register_change_handler("transport.update_assumptions")
class TransportUpdateAssumptionsHandler(ChangeHandler):
    """Updates transport planning operational assumptions and recalculates dependent schedules."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        if not p:
            return [Violation(code="EMPTY_PAYLOAD", severity=4, hard=True, message="Payload is empty")]
        if "shuttle_capacity_seats" in p and int(p["shuttle_capacity_seats"]) <= 0:
            return [Violation(code="INVALID_CAPACITY", severity=4, hard=True, message="shuttle_capacity_seats must be positive")]
        if "shuttle_vehicle_count" in p and int(p["shuttle_vehicle_count"]) <= 0:
            return [Violation(code="INVALID_VEHICLES", severity=4, hard=True, message="shuttle_vehicle_count must be positive")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        assumptions = session.exec(select(Assumption).where(Assumption.key.like("shuttle_%"))).all()
        return {a.key: a.value for a in assumptions}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        updated_keys = []
        for k, v in p.items():
            asm = session.exec(select(Assumption).where(Assumption.key == k)).first()
            if not asm:
                asm = Assumption(
                    key=k,
                    value=str(v),
                    owner="P1",
                    source="OPERATOR_OVERRIDE",
                    reason="Updated via ChangeService transport.update_assumptions",
                    impact_if_changed="Recalculates shuttle requirements and duty of care capacity",
                )
                session.add(asm)
            else:
                asm.value = str(v)
                asm.source = "OPERATOR_OVERRIDE"
                asm.updated_at = now()
                session.add(asm)
            updated_keys.append(k)

        session.flush()
        publish("transport.assumptions_updated", {"updated_keys": updated_keys})
        return {"updated_keys": updated_keys}


@register_change_handler("transport.create_run")
class TransportCreateRunHandler(ChangeHandler):
    """Schedules a new shuttle run for external accommodation or night transfer."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        if not p.get("route_name"):
            return [Violation(code="MISSING_ROUTE", severity=4, hard=True, message="route_name is required")]
        if not p.get("departure_at"):
            return [Violation(code="MISSING_DEPARTURE", severity=4, hard=True, message="departure_at is required")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        dep = p["departure_at"]
        arr = p.get("arrival_at")
        dep_dt = datetime.fromisoformat(dep.replace("Z", "+00:00")) if isinstance(dep, str) else dep
        arr_dt = datetime.fromisoformat(arr.replace("Z", "+00:00")) if (arr and isinstance(arr, str)) else arr

        run = ShuttleRun(
            route_id=p.get("route_id"),
            route_name=p["route_name"],
            vehicle_id=p.get("vehicle_id"),
            property_id=p.get("property_id"),
            departure_at=dep_dt,
            arrival_at=arr_dt,
            capacity=int(p.get("capacity", 15)),
            escort_staff_id=p.get("escort_staff_id"),
            status="SCHEDULED",
        )
        session.add(run)
        session.flush()

        publish("transport.run_created", {"run_id": run.id, "route_name": run.route_name})
        return {"run_id": run.id, "status": run.status}


@register_change_handler("transport.verify_safety")
class TransportVerifySafetyHandler(ChangeHandler):
    """Verifies duty-of-care and escort arrangement for late-night movement."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        if not p.get("participant_id"):
            return [Violation(code="MISSING_PARTICIPANT", severity=4, hard=True, message="participant_id is required")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        pid = req.payload.get("participant_id")
        existing = session.exec(select(ShuttleAssignment).where(ShuttleAssignment.participant_id == pid)).first()
        return existing.model_dump(mode="json") if existing else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        pid = p["participant_id"]
        assignment = session.exec(select(ShuttleAssignment).where(ShuttleAssignment.participant_id == pid)).first()
        if not assignment:
            assignment = ShuttleAssignment(
                participant_id=pid,
                shuttle_run_id=p.get("shuttle_run_id"),
                property_id=p.get("property_id"),
                safety_verified=bool(p.get("verified", True)),
                verified_by_staff_id=p.get("escort_staff_id"),
                notes=p.get("notes"),
                status="CONFIRMED",
            )
            session.add(assignment)
        else:
            assignment.safety_verified = bool(p.get("verified", True))
            if p.get("shuttle_run_id"):
                assignment.shuttle_run_id = p["shuttle_run_id"]
            if p.get("escort_staff_id"):
                assignment.verified_by_staff_id = p["escort_staff_id"]
            if p.get("notes"):
                assignment.notes = p["notes"]
            assignment.updated_at = now()
            assignment.version += 1
            session.add(assignment)

        session.flush()
        publish("transport.safety_verified", {"participant_id": pid, "verified": assignment.safety_verified})
        return {"participant_id": pid, "verified": assignment.safety_verified}


@register_change_handler("transport.approve_guardian")
class TransportApproveGuardianHandler(ChangeHandler):
    """Approves or rejects guardian authorization for minors staying in external accommodation."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        approval_id = p.get("approval_id")
        if not approval_id:
            return [Violation(code="MISSING_APPROVAL_ID", severity=4, hard=True, message="approval_id is required")]
        appr = session.get(GuardianApproval, approval_id)
        if not appr:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"GuardianApproval {approval_id} not found")]
        status = p.get("approval_status", "").upper()
        if status not in ("APPROVED", "REJECTED", "PENDING"):
            return [Violation(code="INVALID_STATUS", severity=4, hard=True, message="approval_status must be APPROVED, REJECTED, or PENDING")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        appr_id = req.payload.get("approval_id")
        appr = session.get(GuardianApproval, appr_id) if appr_id else None
        return appr.model_dump(mode="json") if appr else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        appr = session.get(GuardianApproval, p["approval_id"])
        appr.approval_status = p["approval_status"].upper()
        appr.notes = p.get("notes") or appr.notes
        if appr.approval_status == "APPROVED":
            appr.approved_at = now()
        appr.updated_at = now()
        appr.version += 1

        session.add(appr)
        session.flush()

        publish("transport.guardian_approved", {
            "approval_id": appr.id,
            "participant_id": appr.participant_id,
            "status": appr.approval_status,
        })
        return {"approval_id": appr.id, "status": appr.approval_status}
