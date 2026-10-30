# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.events import Event, EventSession
from app.models.participants import Registration
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return events module KPI summary as of `now`."""
    total_events = session.exec(select(func.count(Event.id))).one()
    active_events = session.exec(select(func.count(Event.id)).where(Event.status == "ACTIVE")).one()
    solo_events = session.exec(select(func.count(Event.id)).where(Event.solo_team == "SOLO")).one()
    team_events = session.exec(select(func.count(Event.id)).where(Event.solo_team == "TEAM")).one()
    total_regs = session.exec(select(func.count(Registration.id))).one()

    return {
        "module": "events",
        "total_events": total_events,
        "active_events": active_events,
        "solo_events": solo_events,
        "team_events": team_events,
        "total_registrations": total_regs,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    risk_items = []
    # Check for events with 0 registrations
    active_events = session.exec(select(Event).where(Event.status == "ACTIVE")).all()
    for ev in active_events:
        regs = session.exec(select(func.count(Registration.id)).where(Registration.event_id == ev.id)).one()
        if regs == 0:
            risk_items.append(RiskItem(
                id=f"risk_evt_zero_reg_{ev.id}",
                module="events",
                kind="ZERO_REGISTRATIONS",
                title=f"Zero Registrations for Event {ev.name}",
                severity=2,
                hours_to_impact=24.0,
                people_affected=0,
                uncertainty=0.1,
                resource_criticality=2,
                entity_refs=[EntityRef(type="event", id=ev.id, label=ev.name)],
                explanation=f"Event {ev.name} ({ev.id}) has zero registered participants.",
            ))
    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    deps = []
    if entity_type == "event":
        sessions = session.exec(select(EventSession).where(EventSession.event_id == entity_id)).all()
        for s in sessions:
            deps.append(EntityRef(type="event_session", id=s.id, label=f"{s.event_name} {s.heat}"))
            if s.venue_id:
                deps.append(EntityRef(type="venue", id=s.venue_id, label=s.venue_name or s.venue_id))

        regs = session.exec(select(Registration).where(Registration.event_id == entity_id)).all()
        for r in regs[:20]:  # Cap references to avoid giant graph
            deps.append(EntityRef(type="participant", id=r.participant_id, label=f"Participant {r.participant_id}"))

    return deps
