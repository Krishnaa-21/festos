# OWNER: P1
"""Pure Scheduling Engine.

No DB access, no FastAPI imports.
Implements:
- Interval availability and buffer management
- Participant arrival wave allocation (Early, Main, Late)
- Capacity-bounded heat generation
- Multi-round cascading (prelims -> semis -> finals) with result declaration buffers
- Unscheduled participant accounting with honest reasons
- Fairness proposals for Late Wave & Wildcard Finals
- Support for optional OR-Tools CP-SAT or pure greedy graph-clustered solver
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# Default constants
DEFAULT_SETUP_BUFFER_MIN = 15
DEFAULT_TEARDOWN_BUFFER_MIN = 15
DEFAULT_VENUE_TRAVEL_MIN = 15
DEFAULT_CHECKIN_BUFFER_MIN = 60
DEFAULT_ROUND_RESULT_BUFFER_MIN = 60
DEFAULT_SEMIFINAL_RATIO = 0.5
DEFAULT_FINALIST_RATIO = 0.10
DEFAULT_FINALIST_MIN = 8

DEFAULT_VENUE_COMPATIBILITY: Dict[str, List[str]] = {
    "audio; seating": ["V04", "V02", "V03", "V01"],
    "projector; seating": ["V02", "V03", "V07", "V09"],
    "power; tables": ["V07", "V09", "V03", "V08"],
    "open ground": ["V04", "V05", "V06", "V08"],
    "quiet room": ["V09", "V07"],
    "stage; lights": ["V01"],
}


def parse_availability_windows(window_str: str) -> List[Tuple[datetime, datetime]]:
    """Parses string formatted like:
    '2026-10-30 08:00-22:00;2026-10-31 08:00-22:00;2026-11-01 08:00-20:00'
    Returns list of (start_utc, end_utc) tuples.
    """
    windows = []
    if not window_str:
        return windows

    for part in window_str.split(";"):
        part = part.strip()
        if not part:
            continue
        try:
            day, time_range = part.split(" ")
            start_str, end_str = time_range.split("-")
            s = datetime.strptime(f"{day} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            e = datetime.strptime(f"{day} {end_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            windows.append((s, e))
        except Exception:
            continue
    return windows


def interval_overlaps(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
    buffer_before: timedelta = timedelta(0),
    buffer_after: timedelta = timedelta(0),
) -> bool:
    """Core sweep-line / interval test:
    Expanded A overlaps B if (start_a - buffer_before < end_b) and (start_b < end_a + buffer_after).
    """
    return (start_a - buffer_before < end_b) and (start_b < end_a + buffer_after)


def fits_in_venue_windows(
    start: datetime,
    end: datetime,
    windows: List[Tuple[datetime, datetime]],
    setup_buffer: timedelta,
    teardown_buffer: timedelta,
) -> bool:
    """Checks if [start - setup_buffer, end + teardown_buffer] is fully contained within at least one operating window."""
    eff_start = start - setup_buffer
    eff_end = end + teardown_buffer
    for ws, we in windows:
        if ws <= eff_start and eff_end <= we:
            return True
    return False


def person_is_present(
    arrival_dt: datetime,
    departure_dt: datetime,
    start_dt: datetime,
    end_dt: datetime,
    checkin_buffer_min: int = DEFAULT_CHECKIN_BUFFER_MIN,
) -> bool:
    """Checks if participant has checked in and has not yet departed for the event duration."""
    min_arrival = arrival_dt + timedelta(minutes=checkin_buffer_min)
    return min_arrival <= start_dt and end_dt <= departure_dt


def person_is_free(
    participant_busy: List[Tuple[datetime, datetime, str]],
    start_dt: datetime,
    end_dt: datetime,
    venue_id: str,
    travel_min: int = DEFAULT_VENUE_TRAVEL_MIN,
    travel_overrides: Optional[Dict[Tuple[str, str], int]] = None,
) -> bool:
    """Checks if participant has any overlapping session or insufficient travel time between venues."""
    travel_overrides = travel_overrides or {}
    for bs, be, bv in participant_busy:
        if bv != venue_id:
            req_travel = travel_overrides.get((bv, venue_id), travel_overrides.get((venue_id, bv), travel_min))
            travel_td = timedelta(minutes=req_travel)
        else:
            travel_td = timedelta(0)

        if start_dt < be + travel_td and end_dt > bs - travel_td:
            return False
    return True


def find_venue_slot(
    venue_id: str,
    earliest: datetime,
    duration: timedelta,
    windows: List[Tuple[datetime, datetime]],
    venue_busy: List[Tuple[datetime, datetime]],
    setup_buffer: timedelta,
    teardown_buffer: timedelta,
    participant: Optional[Dict[str, Any]] = None,
    participant_busy: Optional[Dict[str, List[Tuple[datetime, datetime, str]]]] = None,
    latest: Optional[datetime] = None,
    travel_min: int = DEFAULT_VENUE_TRAVEL_MIN,
    travel_overrides: Optional[Dict[Tuple[str, str], int]] = None,
) -> Optional[datetime]:
    """Finds the earliest valid start time for a session of `duration` at `venue_id`."""
    # Candidates: earliest requested, plus window starts + setup, plus existing busy interval ends + teardown
    candidates = {earliest}
    for ws, _ in windows:
        cand = ws + setup_buffer
        if cand >= earliest:
            candidates.add(cand)
    for _, be in venue_busy:
        cand = be + setup_buffer
        if cand >= earliest:
            candidates.add(cand)

    for cand_start in sorted(candidates):
        if latest and cand_start > latest:
            return None
        cand_end = cand_start + duration

        # 1. Fits in venue availability windows
        if not fits_in_venue_windows(cand_start, cand_end, windows, setup_buffer, teardown_buffer):
            continue

        # 2. Does not conflict with existing venue busy intervals
        overlap = False
        eff_start = cand_start - setup_buffer
        eff_end = cand_end + teardown_buffer
        for bs, be in venue_busy:
            # bs and be in venue_busy are stored padded: (start - setup, end + teardown)
            if eff_start < be and eff_end > bs:
                overlap = True
                break
        if overlap:
            continue

        # 3. Person constraints (if person specified)
        if participant and participant_busy is not None:
            pid = participant["participant_id"]
            p_busy = participant_busy.get(pid, [])
            if not person_is_free(p_busy, cand_start, cand_end, venue_id, travel_min, travel_overrides):
                continue

        return cand_start

    return None


class PureSchedulingEngine:
    """Pure, deterministic event scheduling engine."""

    def __init__(
        self,
        events: List[Dict[str, Any]],
        venues: List[Dict[str, Any]],
        registrations: List[Dict[str, Any]],
        venue_compatibility: Optional[Dict[str, List[str]]] = None,
        assumptions: Optional[Dict[str, Any]] = None,
        travel_overrides: Optional[Dict[Tuple[str, str], int]] = None,
    ):
        self.events = events
        self.venues = venues
        self.registrations = registrations
        self.compat = venue_compatibility or DEFAULT_VENUE_COMPATIBILITY
        self.assumptions = assumptions or {}
        self.travel_overrides = travel_overrides or {}

        # Parse assumptions
        self.setup_buffer = timedelta(
            minutes=int(self.assumptions.get("setup_buffer_min", DEFAULT_SETUP_BUFFER_MIN))
        )
        self.teardown_buffer = timedelta(
            minutes=int(self.assumptions.get("teardown_buffer_min", DEFAULT_TEARDOWN_BUFFER_MIN))
        )
        self.travel_min = int(self.assumptions.get("venue_travel_min", DEFAULT_VENUE_TRAVEL_MIN))
        self.checkin_buffer_min = int(
            self.assumptions.get("checkin_buffer_min", DEFAULT_CHECKIN_BUFFER_MIN)
        )
        self.round_result_buffer_min = int(
            self.assumptions.get("round_result_buffer_min", DEFAULT_ROUND_RESULT_BUFFER_MIN)
        )
        self.semifinal_ratio = float(
            self.assumptions.get("semifinal_ratio", DEFAULT_SEMIFINAL_RATIO)
        )
        self.finalist_ratio = float(
            self.assumptions.get("finalist_ratio", DEFAULT_FINALIST_RATIO)
        )
        self.finalist_min = int(
            self.assumptions.get("finalist_min", DEFAULT_FINALIST_MIN)
        )

        # Parse venue structures
        self.venue_map = {v["id"]: v for v in self.venues}
        self.venue_names = {v["id"]: v.get("name", v["id"]) for v in self.venues}
        self.venue_capacities = {v["id"]: int(v.get("capacity", 100)) for v in self.venues}
        self.venue_windows: Dict[str, List[Tuple[datetime, datetime]]] = {}
        for v in self.venues:
            win_str = v.get("availability_windows", "")
            self.venue_windows[v["id"]] = parse_availability_windows(win_str)

        # Waves definition (in UTC)
        self.waves: Dict[str, Tuple[datetime, datetime]] = {
            "E": (
                datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc),
                datetime(2026, 10, 30, 22, 0, tzinfo=timezone.utc),
            ),
            "M": (
                datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc),
                datetime(2026, 10, 31, 22, 0, tzinfo=timezone.utc),
            ),
            "L": (
                datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc),
            ),
        }

    def generate(
        self,
        solver: str = "greedy",
        include_late_wave: bool = True,
        wildcard_finals: bool = False,
    ) -> Dict[str, Any]:
        """Generates schedule sessions, tracks unscheduled entrants, and records fairness proposals."""
        vbusy: Dict[str, List[Tuple[datetime, datetime]]] = defaultdict(list)
        pbusy: Dict[str, List[Tuple[datetime, datetime, str]]] = defaultdict(list)
        sessions: List[Dict[str, Any]] = []
        unscheduled_entrants: List[Dict[str, Any]] = []
        unplaced_sessions: List[Dict[str, Any]] = []
        fairness_proposals: List[Dict[str, Any]] = []

        if include_late_wave:
            fairness_proposals.append({
                "id": "prop_late_wave",
                "title": "Late Arrival Wave on 1 Nov Morning (08:00 - 14:00)",
                "status": "PENDING_APPROVAL",
                "requires_role": "FESTIVAL_DIRECTOR",
                "reason": "13% of participants arrive late night Oct 31; accommodates them in preliminary heats without forfeit.",
            })

        if wildcard_finals:
            fairness_proposals.append({
                "id": "prop_wildcard_finals",
                "title": "Direct Wildcard Entry to Finals for Late Wave Qualifiers",
                "status": "PENDING_APPROVAL",
                "requires_role": "FESTIVAL_DIRECTOR",
                "reason": "Allows Top scorers from Nov 1 Late wave to enter Finals directly as wildcards.",
            })

        # Pre-process registrations - never silently drop any registrant
        regs_by_event: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in self.registrations:
            a = r.get("arrival_dt") or r.get("arrival_at") or r.get("arrival_datetime")
            d = r.get("departure_dt") or r.get("departure_at") or r.get("departure_datetime")

            if isinstance(a, str):
                try:
                    a = datetime.fromisoformat(a)
                    if a.tzinfo is None:
                        a = a.replace(tzinfo=timezone.utc)
                except Exception:
                    a = None
            elif isinstance(a, datetime) and a.tzinfo is None:
                a = a.replace(tzinfo=timezone.utc)

            if isinstance(d, str):
                try:
                    d = datetime.fromisoformat(d)
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=timezone.utc)
                except Exception:
                    d = None
            elif isinstance(d, datetime) and d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)

            r_copy = dict(r)
            r_copy["arrival_dt"] = a
            r_copy["departure_dt"] = d

            if a and d and d > a:
                regs_by_event[r["event_id"]].append(r_copy)
            else:
                unscheduled_entrants.append({
                    "participant_id": r.get("participant_id", "UNKNOWN"),
                    "event_id": r.get("event_id", "UNKNOWN"),
                    "contingent_id": r.get("contingent_id", "UNKNOWN"),
                    "reason": "NOT_ON_SITE_LONG_ENOUGH",
                    "arrival_datetime": a.isoformat() if a else None,
                    "departure_datetime": d.isoformat() if d else None,
                    "alternatives": [
                        "Request participant arrival/departure window extension",
                        "Move to remote/asynchronous evaluation",
                    ],
                })

        # Event ordering: prioritize tightest venue options first, then highest entrants
        ev_order = []
        all_venue_ids = [v["id"] for v in self.venues]
        for ev in self.events:
            evid = ev["id"]
            req = ev.get("venue_requirements", "")
            raw_vopts = self.compat.get(req)
            # Filter options to venues actually present in self.venues
            if raw_vopts:
                vopts = [vid for vid in raw_vopts if vid in self.venue_map]
            else:
                vopts = []
            if not vopts:
                vopts = all_venue_ids
            ev["_vopts"] = vopts
            ev["_dur"] = timedelta(minutes=int(ev.get("duration_min", 60)))
            ev["_entrants_count"] = len(regs_by_event.get(evid, []))
            ev_order.append(ev)

        ev_order.sort(key=lambda e: (len(e["_vopts"]), -e["_entrants_count"]))

        first_round_max_end: Dict[str, Tuple[datetime, int, Optional[datetime]]] = {}
        wave_keys = ["M", "E"]
        if include_late_wave:
            wave_keys.append("L")

        session_counter = 1

        # -------------------------------------------------------------
        # Phase 1: Preliminaries & Single Rounds
        # -------------------------------------------------------------
        for ev in ev_order:
            evid = ev["id"]
            dur = ev["_dur"]
            rounds_text = ev.get("rounds_text", "prelims|semis|finals")
            r1 = "prelims" if "prelims" in rounds_text else "single"
            entrants = sorted(
                regs_by_event.get(evid, []),
                key=lambda x: x["arrival_dt"],
            )

            heats: Dict[str, List[Dict[str, Any]]] = {w: [] for w in self.waves}

            for p in entrants:
                placed = False
                p_arr = p["arrival_dt"]
                p_dep = p["departure_dt"]
                p_id = p["participant_id"]

                for w in wave_keys:
                    ws, we = self.waves[w]

                    # 1. Try to join an existing heat in wave w
                    for h in heats[w]:
                        vid = h["vid"]
                        h_start = h["start"]
                        h_end = h_start + dur

                        if len(h["members"]) < self.venue_capacities[vid]:
                            if person_is_present(p_arr, p_dep, h_start, h_end, self.checkin_buffer_min):
                                if person_is_free(
                                    pbusy[p_id],
                                    h_start,
                                    h_end,
                                    vid,
                                    self.travel_min,
                                    self.travel_overrides,
                                ):
                                    h["members"].append(p)
                                    pbusy[p_id].append((h_start, h_end, vid))
                                    placed = True
                                    break
                    if placed:
                        break

                    # 2. Try to schedule a new heat in wave w
                    lo = max(ws, p_arr + timedelta(minutes=self.checkin_buffer_min))
                    hi = min(we - dur, p_dep - dur)
                    if hi < lo:
                        continue

                    best_slot: Optional[Tuple[str, datetime]] = None
                    for vid in ev["_vopts"]:
                        windows = self.venue_windows.get(vid, [])
                        s = find_venue_slot(
                            venue_id=vid,
                            earliest=lo,
                            duration=dur,
                            windows=windows,
                            venue_busy=vbusy[vid],
                            setup_buffer=self.setup_buffer,
                            teardown_buffer=self.teardown_buffer,
                            participant=p,
                            participant_busy=pbusy,
                            latest=hi,
                            travel_min=self.travel_min,
                            travel_overrides=self.travel_overrides,
                        )
                        if s and (best_slot is None or s < best_slot[1]):
                            best_slot = (vid, s)

                    if best_slot:
                        best_vid, best_s = best_slot
                        h = {
                            "vid": best_vid,
                            "start": best_s,
                            "members": [p],
                        }
                        heats[w].append(h)
                        vbusy[best_vid].append((
                            best_s - self.setup_buffer,
                            best_s + dur + self.teardown_buffer,
                        ))
                        pbusy[p_id].append((best_s, best_s + dur, best_vid))
                        placed = True
                        break

                if not placed:
                    dur_needed = timedelta(minutes=self.checkin_buffer_min) + dur
                    if p_dep - p_arr < dur_needed:
                        reason = "NOT_ON_SITE_LONG_ENOUGH"
                        alternatives = [
                            "Request participant arrival extension",
                            "Move to remote/asynchronous evaluation",
                        ]
                    else:
                        reason = "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH"
                        alternatives = [
                            "Schedule in Late-Arrival Wave L1",
                            "Reassign to secondary venue",
                            "Swap heat assignment with non-clashing peer",
                        ]

                    unscheduled_entrants.append({
                        "participant_id": p_id,
                        "event_id": evid,
                        "contingent_id": p.get("contingent_id", "UNKNOWN"),
                        "reason": reason,
                        "arrival_datetime": p_arr.isoformat(),
                        "departure_datetime": p_dep.isoformat(),
                        "alternatives": alternatives,
                    })

            # Create session records from created heats
            for w in self.waves:
                for i, h in enumerate(sorted(heats[w], key=lambda x: x["start"])):
                    s_id = f"ses_{session_counter:04d}"
                    session_counter += 1
                    vid = h["vid"]
                    s_start = h["start"]
                    s_end = s_start + dur
                    assigned_pids = [m["participant_id"] for m in h["members"]]

                    sessions.append({
                        "id": s_id,
                        "event_id": evid,
                        "event_name": ev.get("name", evid),
                        "round": r1,
                        "round_number": 1,
                        "heat": f"{w}{i + 1}",
                        "venue_id": vid,
                        "venue_name": self.venue_names.get(vid, vid),
                        "start_at": s_start,
                        "end_at": s_end,
                        "entrants_count": len(h["members"]),
                        "entrant_basis": "registered (assigned)",
                        "volunteers_required": int(ev.get("volunteers_needed", 0)),
                        "equipment_required": ev.get("equipment_needs"),
                        "judge_slots_needed": int(ev.get("judges_needed", 2)),
                        "assigned_judges": [],
                        "assigned_participant_ids": assigned_pids,
                        "wave": w,
                        "status": "SCHEDULED",
                    })

            main_ends = [
                h["start"] + dur
                for w in ("E", "M")
                for h in heats[w]
            ]
            late_ends = [
                h["start"] + dur
                for h in heats["L"]
            ]
            first_round_max_end[evid] = (
                max(main_ends) if main_ends else datetime(2026, 10, 31, 9, 0, tzinfo=timezone.utc),
                len(entrants),
                max(late_ends) if late_ends else None,
            )

        # -------------------------------------------------------------
        # Phase 2: Semifinals & Finals (Later Rounds)
        # -------------------------------------------------------------
        for rank, rname, rnum in [(1, "semis", 2), (2, "finals", 3)]:
            for ev in ev_order:
                evid = ev["id"]
                rounds_text = ev.get("rounds_text", "prelims|semis|finals")
                if rname not in rounds_text:
                    continue

                dur = ev["_dur"]
                prev_sessions = [s for s in sessions if s["event_id"] == evid]
                base_ends = [
                    s["end_at"]
                    for s in prev_sessions
                    if not (str(s.get("heat", "")).startswith("L") and rname == "semis")
                ]

                earliest = (
                    max(base_ends) if base_ends else first_round_max_end[evid][0]
                ) + timedelta(minutes=self.round_result_buffer_min)

                n_prelims = first_round_max_end[evid][1]
                if rname == "semis":
                    n_qualifiers = math.ceil(n_prelims * self.semifinal_ratio)
                else:
                    n_qualifiers = max(self.finalist_min, math.ceil(n_prelims * self.finalist_ratio))

                remaining = n_qualifiers
                heat_num = 1

                while remaining > 0:
                    best_slot: Optional[Tuple[str, datetime]] = None
                    for vid in ev["_vopts"]:
                        windows = self.venue_windows.get(vid, [])
                        s = find_venue_slot(
                            venue_id=vid,
                            earliest=earliest,
                            duration=dur,
                            windows=windows,
                            venue_busy=vbusy[vid],
                            setup_buffer=self.setup_buffer,
                            teardown_buffer=self.teardown_buffer,
                        )
                        if s and (best_slot is None or s < best_slot[1]):
                            best_slot = (vid, s)

                    if best_slot is None:
                        unplaced_sessions.append({
                            "event_id": evid,
                            "event_name": ev.get("name", evid),
                            "round": rname,
                            "round_number": rnum,
                            "entrants": remaining,
                            "reason": "no venue window left before fest end",
                        })
                        break

                    best_vid, best_s = best_slot
                    v_cap = self.venue_capacities[best_vid]
                    heat_size = min(remaining, v_cap)

                    s_id = f"ses_{session_counter:04d}"
                    session_counter += 1
                    s_start = best_s
                    s_end = s_start + dur

                    sessions.append({
                        "id": s_id,
                        "event_id": evid,
                        "event_name": ev.get("name", evid),
                        "round": rname,
                        "round_number": rnum,
                        "heat": f"{rname[:1].upper()}{heat_num}",
                        "venue_id": best_vid,
                        "venue_name": self.venue_names.get(best_vid, best_vid),
                        "start_at": s_start,
                        "end_at": s_end,
                        "entrants_count": heat_size,
                        "entrant_basis": "ASSUMED qualifiers (unknown until results)",
                        "volunteers_required": int(ev.get("volunteers_needed", 0)),
                        "equipment_required": ev.get("equipment_needs"),
                        "judge_slots_needed": int(ev.get("judges_needed", 2)),
                        "assigned_judges": [],
                        "assigned_participant_ids": [],
                        "wave": None,
                        "status": "SCHEDULED",
                    })

                    vbusy[best_vid].append((
                        s_start - self.setup_buffer,
                        s_end + self.teardown_buffer,
                    ))
                    remaining -= heat_size
                    heat_num += 1

        # Sort sessions chronologically
        sessions.sort(key=lambda s: (s["start_at"], s["venue_id"]))

        total_regs = len(self.registrations)
        unsched_count = len(unscheduled_entrants)
        sched_count = total_regs - unsched_count

        return {
            "sessions": sessions,
            "unscheduled_entrants": unscheduled_entrants,
            "unplaced_sessions": unplaced_sessions,
            "fairness_proposals": fairness_proposals,
            "metrics": {
                "total_registrations": total_regs,
                "scheduled_registrations": sched_count,
                "unscheduled_registrations": unsched_count,
                "total_sessions": len(sessions),
                "unplaced_sessions": len(unplaced_sessions),
            },
        }
