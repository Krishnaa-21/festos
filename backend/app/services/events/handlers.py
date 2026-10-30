# OWNER: P1
import logging
from typing import Any, Dict, List, Literal

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.events import Event, EventSession
from app.models.participants import Registration
from app.schemas.common import Violation

logger = logging.getLogger("festos.events.handlers")


@register_change_handler("event.create")
class EventCreateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = req.payload
        if not p.get("name"):
            return [Violation(code="MISSING_NAME", severity=3, hard=True, message="Event name is required")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = req.payload
        evt = Event(
            id=req.entity_id,
            name=p["name"],
            code=p.get("code", req.entity_id),
            solo_team=p.get("solo_team", "SOLO").upper(),
            event_type=p.get("event_type", "solo").lower(),
            rounds=int(p.get("rounds", 1)),
            rounds_text=p.get("rounds_text"),
            duration_min=int(p.get("duration_min", 60)),
            venue_requirements=p.get("venue_requirements"),
            equipment_needs=p.get("equipment_needs"),
            volunteers_needed=int(p.get("volunteers_needed", 0)),
            judges_needed=int(p.get("judges_needed", 2)),
            requirements=p.get("requirements", {}),
            status="ACTIVE",
            created_at=now(),
            updated_at=now(),
        )
        session.add(evt)
        session.flush()
        return evt.model_dump(mode="json")


@register_change_handler("event.update")
class EventUpdateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        evt = session.get(Event, req.entity_id)
        if not evt:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Event {req.entity_id} not found")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        evt = session.get(Event, req.entity_id)
        return evt.model_dump(mode="json") if evt else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        evt = session.get(Event, req.entity_id)
        p = req.payload
        for k, v in p.items():
            if hasattr(evt, k) and k not in ("id", "created_at"):
                setattr(evt, k, v)
        evt.version += 1
        evt.updated_at = now()
        session.add(evt)
        session.flush()
        return evt.model_dump(mode="json")


@register_change_handler("event.cancel")
class EventCancelHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        evt = session.get(Event, req.entity_id)
        if not evt:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Event {req.entity_id} not found")]
        if evt.status == "CANCELLED":
            return [Violation(code="ALREADY_CANCELLED", severity=2, hard=True, message=f"Event {req.entity_id} is already cancelled")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        evt = session.get(Event, req.entity_id)
        sessions = session.exec(select(EventSession).where(EventSession.event_id == req.entity_id)).all()
        return {
            "event": evt.model_dump(mode="json") if evt else {},
            "sessions": [s.model_dump(mode="json") for s in sessions],
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        evt = session.get(Event, req.entity_id)
        evt.status = "CANCELLED"
        evt.version += 1
        evt.updated_at = now()
        session.add(evt)

        # Cancel associated sessions
        sessions = session.exec(select(EventSession).where(EventSession.event_id == req.entity_id)).all()
        for s in sessions:
            s.status = "CANCELLED"
            s.updated_at = now()
            session.add(s)

        session.flush()
        return {"event_id": req.entity_id, "status": "CANCELLED", "cancelled_sessions_count": len(sessions)}

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        return "HIGH"


@register_change_handler("event.merge")
class EventMergeHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        source = session.get(Event, req.entity_id)
        target_id = req.payload.get("target_event_id")
        target = session.get(Event, target_id) if target_id else None

        if not source:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Source event {req.entity_id} not found")]
        if not target:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Target event {target_id} not found")]
        if source.id == target.id:
            return [Violation(code="INVALID_MERGE", severity=3, hard=True, message="Cannot merge an event into itself")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        source = session.get(Event, req.entity_id)
        target = session.get(Event, req.payload.get("target_event_id"))
        return {
            "source": source.model_dump(mode="json") if source else {},
            "target": target.model_dump(mode="json") if target else {},
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        source = session.get(Event, req.entity_id)
        target_id = req.payload.get("target_event_id")
        target = session.get(Event, target_id)

        source.status = "MERGED"
        source.version += 1
        source.updated_at = now()
        session.add(source)

        # Repoint registrations
        regs = session.exec(select(Registration).where(Registration.event_id == source.id)).all()
        for r in regs:
            r.event_id = target.id
            r.updated_at = now()
            session.add(r)

        session.flush()
        return {
            "source_id": source.id,
            "target_id": target.id,
            "repointed_registrations_count": len(regs),
        }

    def risk(self, req: ChangeRequest) -> Literal["LOW", "HIGH"]:
        return "HIGH"


@register_change_handler("event.extend_duration")
class EventExtendDurationHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        evt = session.get(Event, req.entity_id)
        if not evt:
            return [Violation(code="NOT_FOUND", severity=4, hard=True, message=f"Event {req.entity_id} not found")]
        new_dur = req.payload.get("new_duration_min")
        if not new_dur or int(new_dur) <= 0:
            return [Violation(code="INVALID_DURATION", severity=3, hard=True, message="Valid duration in minutes required")]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        evt = session.get(Event, req.entity_id)
        sessions = session.exec(select(EventSession).where(EventSession.event_id == req.entity_id)).all()
        return {
            "event": evt.model_dump(mode="json") if evt else {},
            "sessions": [s.model_dump(mode="json") for s in sessions],
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        from datetime import timedelta
        evt = session.get(Event, req.entity_id)
        new_dur = int(req.payload["new_duration_min"])
        old_dur = evt.duration_min
        evt.duration_min = new_dur
        evt.version += 1
        evt.updated_at = now()
        session.add(evt)

        # Update end times of all existing sessions
        sessions = session.exec(select(EventSession).where(EventSession.event_id == req.entity_id)).all()
        for s in sessions:
            if s.start_at:
                s.end_at = s.start_at + timedelta(minutes=new_dur)
                s.updated_at = now()
                session.add(s)

        session.flush()
        return {
            "event_id": req.entity_id,
            "old_duration_min": old_dur,
            "new_duration_min": new_dur,
            "updated_sessions_count": len(sessions),
        }
