# OWNER: P1
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.core.clock import now
from app.core.errors import FestOSError
from app.engines.conflicts import PureConflictDetector
from app.engines.resolutions import PureResolutionRecommender
from app.engines.scheduling import PureSchedulingEngine
from app.models.events import Conflict, Event, EventSession, ScheduleVersion
from app.models.ops import TravelTime, Venue
from app.models.participants import Participant, Registration
from app.services.venues.service import _VENUE_COMPATIBILITY_STATE

logger = logging.getLogger("festos.schedule.service")

# Benchmark numbers from the prototype in the spec (Section 4.3 & Feature 4)
PROTOTYPE_BENCHMARK = {
    "prototype_sessions": 172,
    "prototype_unscheduled": 987,
    "prototype_unplaced_sessions": 28,
    "prototype_venue_overlaps": 0,
    "team_events_missing_team_id": 1810,
}


def _prepare_engine_inputs(session: Session) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[Tuple[str, str], int]]:
    events = [
        {
            "id": e.id,
            "name": e.name,
            "duration_min": e.duration_min,
            "rounds_text": e.rounds_text or "prelims|semis|finals",
            "venue_requirements": e.venue_requirements or "",
            "volunteers_needed": e.volunteers_needed or 0,
            "equipment_needs": e.equipment_needs or "",
            "judges_needed": e.judges_needed,
        }
        for e in session.exec(select(Event).where(Event.status != "CANCELLED")).all()
    ]

    venues = [
        {
            "id": v.id,
            "name": v.name,
            "capacity": v.capacity,
            "availability_windows": v.availability_windows or "",
            "setup_time_min": v.setup_time_min,
            "teardown_time_min": v.teardown_time_min,
        }
        for v in session.exec(select(Venue).where(Venue.status != "MAINTENANCE")).all()
    ]

    all_participants = {p.id: p for p in session.exec(select(Participant)).all()}
    all_regs = session.exec(select(Registration)).all()

    regs = []
    for r in all_regs:
        p = all_participants.get(r.participant_id)
        if p:
            regs.append({
                "participant_id": p.id,
                "event_id": r.event_id,
                "contingent_id": p.contingent_id or "UNKNOWN",
                "arrival_dt": p.arrival_at,
                "departure_dt": p.departure_at,
            })

    travel_overrides = {}
    for tt in session.exec(select(TravelTime)).all():
        travel_overrides[(tt.from_venue_id, tt.to_venue_id)] = tt.travel_time_min

    return events, venues, regs, travel_overrides


def generate_schedule(
    session: Session,
    plan_name: str = "Plan Alpha - ASSUMED",
    solver: str = "greedy",
    include_late_wave: bool = True,
    wildcard_finals: bool = False,
    actor_id: str = "SYSTEM",
) -> Dict[str, Any]:
    events, venues, regs, travel_overrides = _prepare_engine_inputs(session)

    engine = PureSchedulingEngine(
        events=events,
        venues=venues,
        registrations=regs,
        venue_compatibility=_VENUE_COMPATIBILITY_STATE,
        travel_overrides=travel_overrides,
    )

    sched_res = engine.generate(
        solver=solver,
        include_late_wave=include_late_wave,
        wildcard_finals=wildcard_finals,
    )

    sessions_data = sched_res["sessions"]
    unsched_data = sched_res["unscheduled_entrants"]
    unplaced_data = sched_res["unplaced_sessions"]

    # Detect conflicts on the generated plan
    detector = PureConflictDetector(venues, travel_overrides=travel_overrides)
    conflicts_data = detector.detect_conflicts(sessions_data)

    # Persist ScheduleVersion
    ver_id = f"sch_{now().strftime('%Y%m%d%H%M%S')}"

    snapshot_serialized = []
    for s in sessions_data:
        item = dict(s)
        if hasattr(item.get("start_at"), "isoformat"):
            item["start_at"] = item["start_at"].isoformat()
        if hasattr(item.get("end_at"), "isoformat"):
            item["end_at"] = item["end_at"].isoformat()
        snapshot_serialized.append(item)

    sch_ver = ScheduleVersion(
        id=ver_id,
        plan_name=plan_name,
        status="ASSUMED",  # Every generated schedule is labelled ASSUMED
        solver=solver,
        sessions_count=len(sessions_data),
        unscheduled_count=len(unsched_data),
        unplaced_sessions_count=len(unplaced_data),
        conflicts_count=len(conflicts_data),
        sessions_snapshot=snapshot_serialized,
        is_active=True,
        created_at=now(),
        created_by=actor_id,
    )

    # Deactivate existing active versions
    for old_v in session.exec(select(ScheduleVersion).where(ScheduleVersion.is_active == True)).all():  # noqa: E712
        old_v.is_active = False
        session.add(old_v)

    session.add(sch_ver)

    # Replace active sessions
    session.exec(select(EventSession)).all()
    for s_old in session.exec(select(EventSession)).all():
        session.delete(s_old)
    session.flush()

    for s in sessions_data:
        sess_obj = EventSession(
            id=s["id"],
            schedule_version_id=ver_id,
            event_id=s["event_id"],
            event_name=s.get("event_name", ""),
            round=s["round"],
            round_number=s.get("round_number", 1),
            heat=s.get("heat", "1"),
            venue_id=s.get("venue_id"),
            venue_name=s.get("venue_name"),
            start_at=s.get("start_at"),
            end_at=s.get("end_at"),
            entrants_count=s.get("entrants_count", 0),
            entrant_basis=s.get("entrant_basis", "registered (assigned)"),
            volunteers_required=s.get("volunteers_required", 0),
            equipment_required=s.get("equipment_required"),
            judge_slots_needed=s.get("judge_slots_needed", 2),
            assigned_judges=s.get("assigned_judges", []),
            assigned_participant_ids=s.get("assigned_participant_ids", []),
            wave=s.get("wave"),
            status="SCHEDULED",
            created_at=now(),
            updated_at=now(),
        )
        session.add(sess_obj)

    # Persist conflicts
    for old_c in session.exec(select(Conflict)).all():
        session.delete(old_c)
    session.flush()

    for c in conflicts_data:
        c_obj = Conflict(
            schedule_version_id=ver_id,
            conflict_type=c["conflict_type"],
            severity=c["severity"],
            status="OPEN",
            description=c["description"],
            entity_refs=c.get("entity_refs", {}),
            created_at=now(),
        )
        session.add(c_obj)

    session.commit()

    return {
        "version_id": ver_id,
        "plan_name": plan_name,
        "status": "ASSUMED",
        "total_sessions": len(sessions_data),
        "scheduled_registrations": len(regs) - len(unsched_data),
        "unscheduled_registrations": len(unsched_data),
        "unplaced_sessions": len(unplaced_data),
        "conflicts_count": len(conflicts_data),
        "fairness_proposals": sched_res["fairness_proposals"],
        "prototype_benchmark": PROTOTYPE_BENCHMARK,
    }


def list_schedule_versions(session: Session) -> Dict[str, Any]:
    versions = session.exec(select(ScheduleVersion).order_by(ScheduleVersion.created_at.desc())).all()
    return {
        "items": [v.model_dump() for v in versions],
        "total": len(versions),
    }


def get_schedule_version(session: Session, version_id: str) -> Dict[str, Any]:
    v = session.get(ScheduleVersion, version_id)
    if not v:
        raise FestOSError(f"Schedule version {version_id} not found", code="NOT_FOUND", status_code=404)
    return v.model_dump()


def list_sessions(
    session: Session,
    event_id: Optional[str] = None,
    venue_id: Optional[str] = None,
    round_name: Optional[str] = None,
    wave: Optional[str] = None,
) -> Dict[str, Any]:
    query = select(EventSession)
    if event_id:
        query = query.where(EventSession.event_id == event_id)
    if venue_id:
        query = query.where(EventSession.venue_id == venue_id)
    if round_name:
        query = query.where(EventSession.round == round_name.lower())
    if wave:
        query = query.where(EventSession.wave == wave)

    sessions = session.exec(query.order_by(EventSession.start_at, EventSession.venue_id)).all()
    items = [s.model_dump() for s in sessions]
    return {
        "items": items,
        "total": len(items),
    }


def list_conflicts(
    session: Session,
    conflict_type: Optional[str] = None,
    severity: Optional[int] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    query = select(Conflict)
    if conflict_type:
        query = query.where(Conflict.conflict_type == conflict_type.upper())
    if severity:
        query = query.where(Conflict.severity == severity)
    if status:
        query = query.where(Conflict.status == status.upper())

    conflicts = session.exec(query.order_by(Conflict.severity.desc(), Conflict.created_at)).all()
    items = [c.model_dump() for c in conflicts]
    return {
        "items": items,
        "total": len(items),
        "warnings": ["Zero venue overlaps does not mean zero conflicts: all 10 types are checked."],
    }


def get_conflict_resolutions(session: Session, conflict_id: str) -> Dict[str, Any]:
    conflict = session.get(Conflict, conflict_id)
    if not conflict:
        raise FestOSError(f"Conflict {conflict_id} not found", code="NOT_FOUND", status_code=404)

    events, venues, regs, travel_overrides = _prepare_engine_inputs(session)
    detector = PureConflictDetector(venues, travel_overrides=travel_overrides)

    active_sessions = [s.model_dump() for s in session.exec(select(EventSession)).all()]

    recommender = PureResolutionRecommender(
        conflict_detector=detector,
        events=events,
        venues=venues,
        venue_compatibility=_VENUE_COMPATIBILITY_STATE,
    )

    candidates = recommender.recommend_for_conflict(
        conflict=conflict.model_dump(),
        sessions=active_sessions,
        max_candidates=5,
    )

    return {
        "conflict_id": conflict_id,
        "conflict_type": conflict.conflict_type,
        "description": conflict.description,
        "recommendations": candidates,
    }


def get_unscheduled_report(session: Session) -> Dict[str, Any]:
    """Honest reporting of unscheduled entrants and later-round sessions."""
    events, venues, regs, travel_overrides = _prepare_engine_inputs(session)
    engine = PureSchedulingEngine(
        events=events,
        venues=venues,
        registrations=regs,
        venue_compatibility=_VENUE_COMPATIBILITY_STATE,
        travel_overrides=travel_overrides,
    )
    sched_res = engine.generate()

    unscheduled = sched_res["unscheduled_entrants"]
    unplaced = sched_res["unplaced_sessions"]

    reasons = defaultdict(int)
    for u in unscheduled:
        reasons[u["reason"]] += 1

    return {
        "total_registrations": len(regs),
        "scheduled_count": len(regs) - len(unscheduled),
        "unscheduled_count": len(unscheduled),
        "unplaced_later_round_sessions": len(unplaced),
        "reasons_breakdown": dict(reasons),
        "comparison_with_prototype": {
            "prototype_unscheduled": PROTOTYPE_BENCHMARK["prototype_unscheduled"],
            "current_unscheduled": len(unscheduled),
            "difference": len(unscheduled) - PROTOTYPE_BENCHMARK["prototype_unscheduled"],
        },
        "items": unscheduled[:100],  # sample preview
        "unplaced_sessions": unplaced,
    }


def get_timeline(
    session: Session,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    venues = session.exec(select(Venue)).all()
    all_sessions = session.exec(select(EventSession).where(EventSession.status != "CANCELLED")).all()

    by_venue = defaultdict(list)
    for s in all_sessions:
        if s.start_at and s.end_at:
            if from_dt and s.end_at < from_dt:
                continue
            if to_dt and s.start_at > to_dt:
                continue

            by_venue[s.venue_id].append({
                "session_id": s.id,
                "event_id": s.event_id,
                "event_name": s.event_name,
                "round": s.round,
                "heat": s.heat,
                "start": s.start_at.isoformat(),
                "end": s.end_at.isoformat(),
                "setup_start": (s.start_at - timedelta(minutes=15)).isoformat(),
                "teardown_end": (s.end_at + timedelta(minutes=15)).isoformat(),
                "entrants_count": s.entrants_count,
            })

    timeline_venues = []
    for v in venues:
        timeline_venues.append({
            "venue_id": v.id,
            "venue_name": v.name,
            "capacity": v.capacity,
            "indoor_outdoor": v.indoor_outdoor,
            "blocks": sorted(by_venue.get(v.id, []), key=lambda x: x["start"]),
        })

    return {
        "venues": timeline_venues,
        "total_venues": len(timeline_venues),
    }
