# OWNER: P1
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.bus import publish
from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.staff import Shift, Staff
from app.schemas.common import Violation

logger = logging.getLogger("festos.staff.handlers")


@register_change_handler("staff.assign")
class StaffAssignHandler(ChangeHandler):
    """Assigns a staff member to a shift or event session."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        staff_id = p.get("staff_id")
        if not staff_id:
            return [Violation(code="MISSING_STAFF", severity=4, hard=True, message="staff_id is required")]

        staff = session.get(Staff, staff_id)
        if not staff:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Staff {staff_id} not found")]

        if staff.status != "ACTIVE":
            return [Violation(code="INACTIVE_STAFF", severity=4, hard=True, message=f"Staff {staff_id} is {staff.status}")]

        start_at = p.get("start_at")
        end_at = p.get("end_at")
        if not start_at or not end_at:
            return [Violation(code="INVALID_WINDOW", severity=4, hard=True, message="start_at and end_at are required")]

        # Check overload & overlap
        all_shifts = [s.model_dump() for s in session.exec(select(Shift).where(Shift.staff_id == staff_id)).all()]
        st = datetime.fromisoformat(start_at.replace("Z", "+00:00")) if isinstance(start_at, str) else start_at
        et = datetime.fromisoformat(end_at.replace("Z", "+00:00")) if isinstance(end_at, str) else end_at

        # Overlap check
        for sh in all_shifts:
            if sh.get("status") in ("CANCELLED", "MISSED"):
                continue
            e_st = sh.get("start_at")
            e_et = sh.get("end_at")
            if e_st and e_et:
                if isinstance(e_st, str):
                    e_st = datetime.fromisoformat(e_st.replace("Z", "+00:00"))
                if isinstance(e_et, str):
                    e_et = datetime.fromisoformat(e_et.replace("Z", "+00:00"))
                if st < e_et and et > e_st:
                    return [Violation(
                        code="SHIFT_OVERLAP",
                        severity=4,
                        hard=True,
                        message=f"Staff member is already assigned to overlapping shift {sh.get('id')}",
                    )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        staff_id = req.payload.get("staff_id")
        staff = session.get(Staff, staff_id) if staff_id else None
        return staff.model_dump(mode="json") if staff else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        st = datetime.fromisoformat(p["start_at"].replace("Z", "+00:00")) if isinstance(p["start_at"], str) else p["start_at"]
        et = datetime.fromisoformat(p["end_at"].replace("Z", "+00:00")) if isinstance(p["end_at"], str) else p["end_at"]

        shift = Shift(
            staff_id=p["staff_id"],
            role_required=p.get("role_required", "VOLUNTEER"),
            location=p.get("location", "CAMPUS"),
            venue_id=p.get("venue_id"),
            session_id=p.get("session_id"),
            start_at=st,
            end_at=et,
            handover_notes=p.get("handover_notes"),
            status="SCHEDULED",
        )
        session.add(shift)
        session.flush()

        publish("staff.shift_assigned", {
            "shift_id": shift.id,
            "staff_id": shift.staff_id,
            "session_id": shift.session_id,
        })

        return {
            "shift_id": shift.id,
            "staff_id": shift.staff_id,
            "session_id": shift.session_id,
        }


@register_change_handler("staff.replace")
class StaffReplaceHandler(ChangeHandler):
    """Replaces a staff member on a scheduled shift. Mandatory handover note required."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        shift_id = p.get("shift_id")
        replacement_id = p.get("replacement_staff_id")
        handover_notes = p.get("handover_notes")

        if not shift_id:
            return [Violation(code="MISSING_SHIFT", severity=4, hard=True, message="shift_id is required")]
        if not replacement_id:
            return [Violation(code="MISSING_REPLACEMENT", severity=4, hard=True, message="replacement_staff_id is required")]

        # Critical requirement: shift replacement without a handover note is flagged
        if not handover_notes or not handover_notes.strip():
            return [Violation(
                code="HANDOVER_NOTE_MISSING",
                severity=4,
                hard=True,
                message="A shift replacement requires a mandatory handover note detailing responsibilities and state.",
            )]

        shift = session.get(Shift, shift_id)
        if not shift:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Shift {shift_id} not found")]

        repl_staff = session.get(Staff, replacement_id)
        if not repl_staff:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Replacement staff {replacement_id} not found")]
        if repl_staff.status != "ACTIVE":
            return [Violation(code="INACTIVE_STAFF", severity=4, hard=True, message=f"Replacement staff {replacement_id} is {repl_staff.status}")]

        # Check that replacement staff is not double-booked for this window
        all_repl_shifts = [s.model_dump() for s in session.exec(select(Shift).where(Shift.staff_id == replacement_id)).all()]
        st = shift.start_at
        et = shift.end_at
        if st and et:
            for sh in all_repl_shifts:
                if sh.get("id") == shift.id or sh.get("status") in ("CANCELLED", "MISSED"):
                    continue
                e_st = sh.get("start_at")
                e_et = sh.get("end_at")
                if e_st and e_et:
                    if isinstance(e_st, str):
                        e_st = datetime.fromisoformat(e_st.replace("Z", "+00:00"))
                    if isinstance(e_et, str):
                        e_et = datetime.fromisoformat(e_et.replace("Z", "+00:00"))
                    if st < e_et and et > e_st:
                        return [Violation(
                            code="SHIFT_OVERLAP",
                            severity=4,
                            hard=True,
                            message=f"Replacement staff member {replacement_id} is already assigned to overlapping shift {sh.get('id')}",
                        )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        shift_id = req.payload.get("shift_id")
        shift = session.get(Shift, shift_id) if shift_id else None
        return shift.model_dump(mode="json") if shift else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        shift = session.get(Shift, p["shift_id"])
        prev_staff_id = shift.staff_id
        shift.staff_id = p["replacement_staff_id"]
        shift.handover_notes = p["handover_notes"]
        shift.updated_at = now()
        shift.version += 1

        session.add(shift)
        session.flush()

        publish("staff.shift_replaced", {
            "shift_id": shift.id,
            "previous_staff_id": prev_staff_id,
            "replacement_staff_id": shift.staff_id,
            "handover_notes": shift.handover_notes,
        })

        return {
            "shift_id": shift.id,
            "previous_staff_id": prev_staff_id,
            "replacement_staff_id": shift.staff_id,
            "handover_notes": shift.handover_notes,
        }
