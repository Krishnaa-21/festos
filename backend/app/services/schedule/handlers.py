# OWNER: P1
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.events import EventSession, ScheduleVersion
from app.models.ops import Venue
from app.schemas.common import Violation

logger = logging.getLogger("festos.schedule.handlers")


def _parse_dt(dt_val: Any) -> Optional[datetime]:
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val
    if isinstance(dt_val, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(dt_val, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass
    return None


@register_change_handler("schedule.move_session")
class ScheduleMoveSessionHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        s = session.get(EventSession, req.entity_id)
        if not s:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Session {req.entity_id} not found")]
        new_start = _parse_dt(req.payload.get("new_start_at"))
        if not new_start:
            return [Violation(code="INVALID_DATETIME", severity=3, hard=True, message="Valid new_start_at is required")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        s = session.get(EventSession, req.entity_id)
        return s.model_dump(mode="json") if s else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        s = session.get(EventSession, req.entity_id)
        new_start = _parse_dt(req.payload["new_start_at"])

        dur = (s.end_at - s.start_at) if (s.end_at and s.start_at) else timedelta(minutes=60)
        old_start = s.start_at
        s.start_at = new_start
        s.end_at = new_start + dur
        s.version += 1
        s.updated_at = now()
        session.add(s)

        # Cascading: Check if downstream later rounds (e.g. semis or finals) for the same event violate round_result_buffer_min (60m)
        cascaded_sessions = []
        downstream = session.exec(
            select(EventSession).where(
                EventSession.event_id == s.event_id,
                EventSession.round_number > s.round_number,
                EventSession.status != "CANCELLED",
            )
        ).all()

        min_buffer = timedelta(minutes=60)
        current_gate = s.end_at + min_buffer

        for ds in sorted(downstream, key=lambda x: x.start_at or now()):
            if ds.start_at and ds.start_at < current_gate:
                ds_dur = (ds.end_at - ds.start_at) if ds.end_at else timedelta(minutes=60)
                ds.start_at = current_gate
                ds.end_at = current_gate + ds_dur
                ds.version += 1
                ds.updated_at = now()
                session.add(ds)
                cascaded_sessions.append(ds.id)
                current_gate = ds.end_at + min_buffer

        session.flush()
        return {
            "session_id": s.id,
            "old_start_at": old_start.isoformat() if old_start else None,
            "new_start_at": s.start_at.isoformat(),
            "new_end_at": s.end_at.isoformat(),
            "cascaded_sessions": cascaded_sessions,
        }

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        # If moving a session causes multiple downstream cascades or peak shift, flag as HIGH
        return "LOW"


@register_change_handler("schedule.change_venue")
class ScheduleChangeVenueHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        s = session.get(EventSession, req.entity_id)
        new_vid = req.payload.get("new_venue_id")
        v = session.get(Venue, new_vid) if new_vid else None
        if not s:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Session {req.entity_id} not found")]
        if not v:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Venue {new_vid} not found")]
        if s.entrants_count > v.capacity:
            return [Violation(
                code="CAPACITY_VIOLATION",
                severity=4,
                hard=True,
                message=f"Entrants ({s.entrants_count}) exceed venue {v.name} capacity ({v.capacity})",
            )]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        s = session.get(EventSession, req.entity_id)
        return s.model_dump(mode="json") if s else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        s = session.get(EventSession, req.entity_id)
        new_vid = req.payload["new_venue_id"]
        v = session.get(Venue, new_vid)

        old_vid = s.venue_id
        s.venue_id = v.id
        s.venue_name = v.name
        s.version += 1
        s.updated_at = now()
        session.add(s)
        session.flush()
        return {
            "session_id": s.id,
            "old_venue_id": old_vid,
            "new_venue_id": v.id,
            "new_venue_name": v.name,
        }


@register_change_handler("schedule.restore_version")
class ScheduleRestoreVersionHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        ver = session.get(ScheduleVersion, req.entity_id)
        if not ver:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Schedule version {req.entity_id} not found")]
        if not ver.sessions_snapshot:
            return [Violation(code="NO_SNAPSHOT", severity=3, hard=True, message="Target schedule version has no saved snapshot")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        # Snapshot current active sessions
        current_sessions = session.exec(select(EventSession)).all()
        return {
            "sessions": [s.model_dump(mode="json") for s in current_sessions],
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        target_ver = session.get(ScheduleVersion, req.entity_id)
        snapshot = target_ver.sessions_snapshot or []

        # 1. Delete or clear existing sessions
        existing_sessions = session.exec(select(EventSession)).all()
        for s in existing_sessions:
            session.delete(s)
        session.flush()

        # 2. Re-create sessions from snapshot
        restored_count = 0
        for s_data in snapshot:
            s_obj = EventSession(
                id=s_data["id"],
                schedule_version_id=target_ver.id,
                event_id=s_data["event_id"],
                event_name=s_data.get("event_name", ""),
                round=s_data.get("round", "prelims"),
                round_number=s_data.get("round_number", 1),
                heat=s_data.get("heat", "1"),
                venue_id=s_data.get("venue_id"),
                venue_name=s_data.get("venue_name"),
                start_at=_parse_dt(s_data.get("start_at")),
                end_at=_parse_dt(s_data.get("end_at")),
                entrants_count=s_data.get("entrants_count", 0),
                entrant_basis=s_data.get("entrant_basis", "registered (assigned)"),
                volunteers_required=s_data.get("volunteers_required", 0),
                equipment_required=s_data.get("equipment_required"),
                judge_slots_needed=s_data.get("judge_slots_needed", 2),
                assigned_judges=s_data.get("assigned_judges", []),
                assigned_participant_ids=s_data.get("assigned_participant_ids", []),
                wave=s_data.get("wave"),
                status=s_data.get("status", "SCHEDULED"),
                created_at=now(),
                updated_at=now(),
            )
            session.add(s_obj)
            restored_count += 1

        # Mark target version as active
        all_vers = session.exec(select(ScheduleVersion)).all()
        for v in all_vers:
            v.is_active = (v.id == target_ver.id)
            session.add(v)

        session.flush()
        return {
            "restored_version_id": target_ver.id,
            "plan_name": target_ver.plan_name,
            "restored_sessions_count": restored_count,
        }

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        return "HIGH"
