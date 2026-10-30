# OWNER: P2
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.registry import register_change_handler
from app.models.accommodation import Room
from app.schemas.common import Violation


@register_change_handler("accommodation.close_hostel")
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
        for r in rooms:
            r.status = "MAINTENANCE"
            session.add(r)
            count += 1
        session.flush()
        return {"closed_block": block, "rooms_affected": count}


@register_change_handler("accommodation.update_room")
class UpdateRoomHandler(ChangeHandler):
    """Updates attributes of a room."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        room = session.get(Room, req.entity_id)
        if room:
            return {"status": room.status, "capacity": room.capacity}
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        room = session.get(Room, req.entity_id)
        if room:
            for k, v in req.payload.items():
                if hasattr(room, k):
                    setattr(room, k, v)
            session.add(room)
            session.flush()
            return {"room_id": room.id, "status": room.status, "capacity": room.capacity}
        return {}
