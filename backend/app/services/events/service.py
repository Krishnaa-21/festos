# OWNER: P1
import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session, col, func, select

from app.core.clock import now
from app.core.errors import FestOSError
from app.models.events import Event, EventRequirement, EventSession, Judge, ProvisionalTeam
from app.models.participants import Participant, Registration

logger = logging.getLogger("festos.events.service")


def list_events(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    solo_team: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    query = select(Event)

    if solo_team:
        query = query.where(func.lower(Event.solo_team) == solo_team.lower())

    if q:
        search = f"%{q.lower()}%"
        query = query.where(
            func.lower(Event.name).like(search) | func.lower(Event.id).like(search)
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    events = session.exec(query).all()

    items = []
    for ev in events:
        reg_count = session.exec(
            select(func.count(Registration.id)).where(Registration.event_id == ev.id)
        ).one()
        ev_dict = ev.model_dump()
        ev_dict["registrations_count"] = reg_count
        items.append(ev_dict)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


def get_event_profile(session: Session, event_id: str) -> Dict[str, Any]:
    ev = session.get(Event, event_id)
    if not ev:
        raise FestOSError(f"Event {event_id} not found", code="NOT_FOUND", status_code=404)

    reqs = session.exec(select(EventRequirement).where(EventRequirement.event_id == event_id)).all()
    sessions = session.exec(select(EventSession).where(EventSession.event_id == event_id)).all()
    reg_count = session.exec(select(func.count(Registration.id)).where(Registration.event_id == event_id)).one()

    prov_teams_count = 0
    if ev.solo_team == "TEAM":
        prov_teams_count = session.exec(
            select(func.count(ProvisionalTeam.id)).where(ProvisionalTeam.event_id == event_id)
        ).one()

    data = ev.model_dump()
    data["requirements_items"] = [r.model_dump() for r in reqs]
    data["sessions_count"] = len(sessions)
    data["registrations_count"] = reg_count
    data["provisional_teams_count"] = prov_teams_count
    return data


def get_event_registrations(session: Session, event_id: str) -> Dict[str, Any]:
    ev = session.get(Event, event_id)
    if not ev:
        raise FestOSError(f"Event {event_id} not found", code="NOT_FOUND", status_code=404)

    regs = session.exec(select(Registration).where(Registration.event_id == event_id)).all()
    p_ids = [r.participant_id for r in regs]
    participants = {p.id: p for p in session.exec(select(Participant).where(col(Participant.id).in_(p_ids))).all()} if p_ids else {}

    items = []
    for r in regs:
        p = participants.get(r.participant_id)
        cid = p.contingent_id if p else "UNKNOWN"
        items.append({
            "registration_id": r.id,
            "participant_id": r.participant_id,
            "participant_name": p.name if p else "UNKNOWN",
            "contingent_id": cid,
            "team_id": r.team_id,
            "provisional_team_id": f"TEAM_{cid}_{event_id}" if ev.solo_team == "TEAM" else None,
            "team_label": "ASSUMED" if ev.solo_team == "TEAM" else None,
            "status": r.status,
        })

    return {
        "event_id": event_id,
        "registrations": items,
        "total": len(items),
    }


def get_provisional_teams(session: Session) -> Dict[str, Any]:
    """Team reconciliation: where team events lack team IDs (1,810 registrations),

    returns derived provisional teams (contingent + event) labelled ASSUMED.
    """
    prov_teams = session.exec(select(ProvisionalTeam)).all()
    team_events = session.exec(select(Event).where(Event.solo_team == "TEAM")).all()
    team_event_ids = {e.id for e in team_events}

    team_regs_count = session.exec(
        select(func.count(Registration.id)).where(col(Registration.event_id).in_(team_event_ids))
    ).one() if team_event_ids else 0

    return {
        "total_team_registrations": team_regs_count,
        "missing_team_id_count": team_regs_count,
        "provisional_teams_count": len(prov_teams),
        "label": "ASSUMED",
        "provisional_teams": [t.model_dump() for t in prov_teams],
    }


def list_judges_and_slots(session: Session) -> Dict[str, Any]:
    """Judge registry: lists registered judges, flags conflicts, and shows explicit UNASSIGNED slots."""
    judges = session.exec(select(Judge)).all()
    sessions = session.exec(select(EventSession).where(EventSession.status != "CANCELLED")).all()

    # Pre-fetch participants to detect if any judge is a competitor or from participating college
    participants = session.exec(select(Participant)).all()
    participant_emails = {p.email.lower(): p for p in participants if p.email and p.email != "UNKNOWN"}
    participant_names = {p.name.lower(): p for p in participants if p.name and p.name != "UNKNOWN"}

    judge_items = []
    for j in judges:
        is_competitor = False
        competitor_p = None
        if j.email and j.email.lower() in participant_emails:
            is_competitor = True
            competitor_p = participant_emails[j.email.lower()]
        elif j.name.lower() in participant_names:
            is_competitor = True
            competitor_p = participant_names[j.name.lower()]

        j_dict = j.model_dump()
        j_dict["is_participant"] = is_competitor
        j_dict["participant_id"] = competitor_p.id if competitor_p else None
        j_dict["college_affiliation"] = j.college_affiliation
        judge_items.append(j_dict)

    unassigned_slots = []
    for s in sessions:
        needed = s.judge_slots_needed
        assigned = len(s.assigned_judges or [])
        gap = max(0, needed - assigned)
        for i in range(gap):
            unassigned_slots.append({
                "session_id": s.id,
                "event_id": s.event_id,
                "event_name": s.event_name,
                "round": s.round,
                "heat": s.heat,
                "slot_number": assigned + i + 1,
                "status": "UNASSIGNED",
            })

    return {
        "judges": judge_items,
        "total_judges": len(judge_items),
        "unassigned_slots_count": len(unassigned_slots),
        "unassigned_slots": unassigned_slots,
    }


def register_judge(
    session: Session,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    college_affiliation: Optional[str] = None,
    expert_events: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    judge = Judge(
        name=name,
        email=email,
        phone=phone,
        college_affiliation=college_affiliation,
        expert_events=expert_events or [],
        notes=notes,
        created_at=now(),
    )
    session.add(judge)
    session.commit()
    session.refresh(judge)
    return judge.model_dump()
