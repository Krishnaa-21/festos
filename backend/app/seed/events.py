# OWNER: P1
import csv
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_seeder
from app.engines.conflicts import PureConflictDetector
from app.engines.scheduling import PureSchedulingEngine
from app.models.events import (
    Event,
    EventRequirement,
    EventSession,
    ProvisionalTeam,
    ScheduleVersion,
)
from app.models.ops import TravelTime, Venue
from app.models.participants import Participant, Registration

logger = logging.getLogger("festos.seed.events")


def _find_data_file(filename: str) -> Optional[Path]:
    candidates = [
        Path(f"data/raw/{filename}"),
        Path(f"../data/raw/{filename}"),
        Path(f"data/reference/{filename}"),
        Path(f"../data/reference/{filename}"),
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    return None


FEATURE_TAG_MAP = {
    "V01": ["stage", "lights", "audio", "seating"],
    "V02": ["projector", "seating", "audio", "indoor"],
    "V03": ["projector", "seating", "audio", "power", "tables"],
    "V04": ["open ground", "stage", "seating", "outdoor"],
    "V05": ["open ground", "outdoor"],
    "V06": ["open ground", "outdoor"],
    "V07": ["quiet room", "power", "tables", "projector"],
    "V08": ["open ground", "sports", "indoor", "power", "tables"],
    "V09": ["quiet room", "projector", "power", "tables", "indoor"],
}


@register_seeder("events_and_venues", order=20)
def seed_events_and_venues(session: Session) -> None:
    logger.info("Starting venues, travel times, provisional teams, and baseline schedule seed...")

    # 1. Seed Venues
    venues_path = _find_data_file("venues.csv")
    if venues_path:
        with open(venues_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vid = row["venue_id"].strip()
                existing = session.get(Venue, vid)
                tags = FEATURE_TAG_MAP.get(vid, ["standard"])
                cap = int(row.get("capacity", 100))
                win = row.get("availability_windows", "").strip() or None
                in_out = row.get("indoor_outdoor", "indoor").strip()

                if existing:
                    existing.capacity = cap
                    existing.availability_windows = win
                    existing.indoor_outdoor = in_out
                    existing.feature_tags = tags
                    session.add(existing)
                else:
                    v = Venue(
                        id=vid,
                        name=row.get("venue_name", vid).strip(),
                        code=vid,
                        capacity=cap,
                        availability_windows=win,
                        indoor_outdoor=in_out,
                        accessible=True,
                        setup_time_min=15,
                        teardown_time_min=15,
                        feature_tags=tags,
                        status="AVAILABLE",
                        created_at=now(),
                        updated_at=now(),
                    )
                    session.add(v)
        session.flush()

    # 2. Seed Default Travel Times between venues
    all_venues = session.exec(select(Venue)).all()
    for v1 in all_venues:
        for v2 in all_venues:
            if v1.id != v2.id:
                existing_tt = session.exec(
                    select(TravelTime).where(
                        TravelTime.from_venue_id == v1.id,
                        TravelTime.to_venue_id == v2.id,
                    )
                ).first()
                if not existing_tt:
                    # Default 15m; V01 <-> V06 25m override
                    tt_min = 25 if {v1.id, v2.id} == {"V01", "V06"} else 15
                    tt = TravelTime(
                        from_venue_id=v1.id,
                        to_venue_id=v2.id,
                        travel_time_min=tt_min,
                    )
                    session.add(tt)
    session.flush()

    # 3. Ensure Event requirements are populated
    events_path = _find_data_file("events.csv")
    if events_path:
        with open(events_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = row["event_id"].strip()
                existing_ev = session.get(Event, eid)
                eq = row.get("equipment_needs", "").strip()
                if existing_ev:
                    existing_ev.equipment_needs = eq or None
                    session.add(existing_ev)
                if eq and eq.lower() != "no special equipment":
                    for item in eq.split(";"):
                        clean_item = item.strip()
                        if clean_item:
                            existing_req = session.exec(
                                select(EventRequirement).where(
                                    EventRequirement.event_id == eid,
                                    EventRequirement.item_name == clean_item,
                                )
                            ).first()
                            if not existing_req:
                                session.add(EventRequirement(
                                    event_id=eid,
                                    item_name=clean_item,
                                    quantity=1,
                                    is_critical=True,
                                ))
        session.flush()

    # 4. Team Reconciliation: Derive Provisional Teams for 1,810 team registrations lacking team IDs
    team_events = session.exec(select(Event).where(Event.solo_team == "TEAM")).all()
    team_event_ids = {e.id for e in team_events}

    all_regs = session.exec(select(Registration)).all()
    all_participants = {p.id: p for p in session.exec(select(Participant)).all()}

    team_groups: Dict[str, List[Registration]] = defaultdict(list)
    for reg in all_regs:
        if reg.event_id in team_event_ids:
            p = all_participants.get(reg.participant_id)
            cid = p.contingent_id if p and p.contingent_id else "C_UNKNOWN"
            group_key = f"TEAM_{cid}_{reg.event_id}"
            team_groups[group_key].append(reg)

    for prov_id, reg_list in team_groups.items():
        existing_prov = session.get(ProvisionalTeam, prov_id)
        cid = prov_id.split("_")[1]
        eid = prov_id.split("_")[2]
        pids = [r.participant_id for r in reg_list]

        if not existing_prov:
            prov = ProvisionalTeam(
                id=prov_id,
                contingent_id=cid,
                event_id=eid,
                name=f"{cid} Team for {eid}",
                status="ASSUMED",
                participant_ids=pids,
                created_at=now(),
                updated_at=now(),
            )
            session.add(prov)

        for reg in reg_list:
            if not reg.team_id:
                reg.team_id = prov_id
                session.add(reg)

    session.flush()

    # 5. Generate and Seed Baseline Assumed Schedule
    existing_version = session.exec(select(ScheduleVersion)).first()
    if not existing_version:
        events_dicts = [
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
            for e in session.exec(select(Event)).all()
        ]

        venues_dicts = [
            {
                "id": v.id,
                "name": v.name,
                "capacity": v.capacity,
                "availability_windows": v.availability_windows or "",
                "setup_time_min": v.setup_time_min,
                "teardown_time_min": v.teardown_time_min,
            }
            for v in session.exec(select(Venue)).all()
        ]

        regs_dicts = []
        for r in all_regs:
            p = all_participants.get(r.participant_id)
            if p:
                regs_dicts.append({
                    "participant_id": p.id,
                    "event_id": r.event_id,
                    "contingent_id": p.contingent_id or "UNKNOWN",
                    "arrival_dt": p.arrival_at,
                    "departure_dt": p.departure_at,
                })

        engine = PureSchedulingEngine(events_dicts, venues_dicts, regs_dicts)
        sched_result = engine.generate(solver="greedy", include_late_wave=True)

        sessions_data = sched_result["sessions"]
        unsched_data = sched_result["unscheduled_entrants"]
        unplaced_data = sched_result["unplaced_sessions"]

        detector = PureConflictDetector(venues_dicts)
        detected_conflicts = detector.detect_conflicts(sessions_data)

        snapshot_serialized = []
        for s in sessions_data:
            item = dict(s)
            if hasattr(item.get("start_at"), "isoformat"):
                item["start_at"] = item["start_at"].isoformat()
            if hasattr(item.get("end_at"), "isoformat"):
                item["end_at"] = item["end_at"].isoformat()
            snapshot_serialized.append(item)

        sch_ver = ScheduleVersion(
            id="sch_baseline",
            plan_name="Baseline Assumed Schedule (Greedy)",
            status="ASSUMED",
            solver="greedy",
            sessions_count=len(sessions_data),
            unscheduled_count=len(unsched_data),
            unplaced_sessions_count=len(unplaced_data),
            conflicts_count=len(detected_conflicts),
            sessions_snapshot=snapshot_serialized,
            is_active=True,
            created_at=now(),
        )
        session.add(sch_ver)
        session.flush()

        for s in sessions_data:
            sess_obj = EventSession(
                id=s["id"],
                schedule_version_id="sch_baseline",
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

    session.commit()
    logger.info("Events, venues, and baseline schedule successfully seeded.")
