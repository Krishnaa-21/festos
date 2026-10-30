# OWNER: P1
import uuid
from datetime import datetime, timezone

import app.services.events.handlers  # noqa: F401
import app.services.schedule.handlers  # noqa: F401
import app.services.venues.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_engine, init_db
from app.models.events import Event, EventSession
from app.models.ops import Venue
from app.schemas.common import Actor
from sqlmodel import Session

engine = get_engine()


def _setup_test_db():
    init_db(engine)


def test_delayed_round_results_cascade():
    _setup_test_db()
    uid = uuid.uuid4().hex[:6]
    ev_id = f"E_TC_{uid}"
    v_id = f"V_TC_{uid}"
    s1_id = f"ses_prelim_{uid}"
    s2_id = f"ses_final_{uid}"

    with Session(engine) as session:
        ev = Event(
            id=ev_id,
            name="Cascade Test Event",
            code=f"TC_{uid}",
            solo_team="SOLO",
            rounds=2,
            rounds_text="prelims|finals",
            duration_min=60,
        )
        session.add(ev)

        v = Venue(
            id=v_id,
            name="Venue TC",
            capacity=100,
            availability_windows="2026-10-31 08:00-22:00",
        )
        session.add(v)
        session.flush()

        # Prelim session: 08:00 to 09:00
        s_prelim = EventSession(
            id=s1_id,
            event_id=ev_id,
            event_name="Cascade Test Event",
            round="prelims",
            round_number=1,
            heat="M1",
            venue_id=v_id,
            start_at=datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 10, 31, 9, 0, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        # Final session: originally scheduled at 10:00 to 11:00 (exactly 60m after prelim end)
        s_final = EventSession(
            id=s2_id,
            event_id=ev_id,
            event_name="Cascade Test Event",
            round="finals",
            round_number=2,
            heat="F1",
            venue_id=v_id,
            start_at=datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        session.add(s_prelim)
        session.add(s_final)
        session.commit()

        # Move prelim session from 08:00 to 09:30 (new end_at: 10:30)
        # The 60m result buffer requires finals to start at >= 11:30
        actor = Actor(id="usr_lead", role="EVENT_LEAD", name="Event Lead")
        req = ChangeRequest(
            action="schedule.move_session",
            entity_type="event_session",
            entity_id=s1_id,
            payload={"new_start_at": "2026-10-31T09:30:00+00:00"},
            actor=actor,
        )
        res = execute_change(req, session)
        assert res.status == "APPLIED"
        assert s2_id in res.data["cascaded_sessions"]

        # Verify finals session was cascaded to 11:30
        final_reloaded = session.get(EventSession, s2_id)
        assert final_reloaded.start_at == datetime(2026, 10, 31, 11, 30, tzinfo=timezone.utc)
        assert final_reloaded.end_at == datetime(2026, 10, 31, 12, 30, tzinfo=timezone.utc)


def test_duration_increased_cascades_session_end():
    _setup_test_db()
    uid = uuid.uuid4().hex[:6]
    ev_id = f"E_DUR_{uid}"
    s_id = f"ses_dur_{uid}"

    with Session(engine) as session:
        ev = Event(
            id=ev_id,
            name="Duration Event",
            code=f"DUR_{uid}",
            solo_team="SOLO",
            duration_min=45,
        )
        session.add(ev)
        session.flush()

        s = EventSession(
            id=s_id,
            event_id=ev_id,
            start_at=datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 10, 31, 10, 45, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        session.add(s)
        session.commit()

        actor = Actor(id="usr_lead", role="EVENT_LEAD", name="Event Lead")
        req = ChangeRequest(
            action="event.extend_duration",
            entity_type="event",
            entity_id=ev_id,
            payload={"new_duration_min": 75},
            actor=actor,
        )
        res = execute_change(req, session)
        assert res.status == "APPLIED"

        s_reloaded = session.get(EventSession, s_id)
        assert s_reloaded.end_at == datetime(2026, 10, 31, 11, 15, tzinfo=timezone.utc)


def test_venue_capacity_reduced_rejection():
    _setup_test_db()
    uid = uuid.uuid4().hex[:6]
    ev_id = f"E_CAP_{uid}"
    v_orig_id = f"V_ORIG_{uid}"
    v_small_id = f"V_SMALL_{uid}"
    s_id = f"ses_cap_{uid}"

    with Session(engine) as session:
        ev = Event(
            id=ev_id,
            name="Cap Test Event",
            code=f"CAP_{uid}",
            solo_team="SOLO",
        )
        v_orig = Venue(
            id=v_orig_id,
            name="Orig Big Venue",
            capacity=100,
            availability_windows="2026-10-31 08:00-22:00",
        )
        v_small = Venue(
            id=v_small_id,
            name="Small Room",
            capacity=20,
            availability_windows="2026-10-31 08:00-22:00",
        )
        session.add(ev)
        session.add(v_orig)
        session.add(v_small)
        session.flush()

        s = EventSession(
            id=s_id,
            event_id=ev_id,
            venue_id=v_orig_id,
            entrants_count=50,
            start_at=datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        session.add(s)
        session.commit()

        # Attempt to change venue to v_small with 50 entrants > 20 capacity -> Rejection
        actor = Actor(id="usr_lead", role="EVENT_LEAD", name="Event Lead")
        req = ChangeRequest(
            action="schedule.change_venue",
            entity_type="event_session",
            entity_id=s_id,
            payload={"new_venue_id": v_small_id},
            actor=actor,
        )
        res = execute_change(req, session)
        assert res.status == "REJECTED"
        assert any(v.code == "CAPACITY_VIOLATION" for v in res.violations)
