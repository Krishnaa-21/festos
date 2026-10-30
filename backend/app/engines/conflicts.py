# OWNER: P1
"""Pure Conflict Detection Engine.

No DB access, no FastAPI imports.
Implements sweep-line interval checking for all 10 festival conflict types:
1. PARTICIPANT_CLASH
2. TEAM_CLASH
3. JUDGE_DOUBLE_BOOKING
4. VOLUNTEER_DOUBLE_BOOKING
5. VENUE_DOUBLE_BOOKING
6. CAPACITY_VIOLATION
7. EQUIPMENT_CONFLICT
8. INSUFFICIENT_TRAVEL_TIME
9. SETUP_TEARDOWN_CONFLICT
10. OPERATING_HOUR_CONFLICT
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.engines.scheduling import (
    DEFAULT_SETUP_BUFFER_MIN,
    DEFAULT_TEARDOWN_BUFFER_MIN,
    DEFAULT_VENUE_TRAVEL_MIN,
    fits_in_venue_windows,
    interval_overlaps,
    parse_availability_windows,
)


class EquipmentAvailabilityPort(Protocol):
    """Port for querying available equipment stock."""

    def get_available_quantity(self, item_name: str) -> int:
        ...


class DefaultEquipmentAdapter:
    """Default in-memory adapter for equipment availability.

    Reads a known inventory dictionary or defaults to default_qty.
    """

    def __init__(self, stock_map: Optional[Dict[str, int]] = None, default_qty: int = 5):
        self.stock_map = {k.lower(): v for k, v in (stock_map or {}).items()}
        self.default_qty = default_qty

    def get_available_quantity(self, item_name: str) -> int:
        if not item_name:
            return 999
        clean = item_name.strip().lower()
        return self.stock_map.get(clean, self.default_qty)


class PureConflictDetector:
    """Pure conflict detection engine executing sweep-line checks across scheduled sessions."""

    def __init__(
        self,
        venues: List[Dict[str, Any]],
        travel_overrides: Optional[Dict[Tuple[str, str], int]] = None,
        equipment_port: Optional[EquipmentAvailabilityPort] = None,
        assumptions: Optional[Dict[str, Any]] = None,
        available_volunteers_total: int = 50,
    ):
        self.venues = venues
        self.venue_map = {v["id"]: v for v in self.venues}
        self.venue_windows = {
            v["id"]: parse_availability_windows(v.get("availability_windows", ""))
            for v in self.venues
        }
        self.travel_overrides = travel_overrides or {}
        self.equipment_port = equipment_port or DefaultEquipmentAdapter()
        self.assumptions = assumptions or {}
        self.available_volunteers_total = available_volunteers_total

        self.setup_buffer_min = int(
            self.assumptions.get("setup_buffer_min", DEFAULT_SETUP_BUFFER_MIN)
        )
        self.teardown_buffer_min = int(
            self.assumptions.get("teardown_buffer_min", DEFAULT_TEARDOWN_BUFFER_MIN)
        )
        self.venue_travel_min = int(
            self.assumptions.get("venue_travel_min", DEFAULT_VENUE_TRAVEL_MIN)
        )

        self.setup_td = timedelta(minutes=self.setup_buffer_min)
        self.teardown_td = timedelta(minutes=self.teardown_buffer_min)
        self.travel_td = timedelta(minutes=self.venue_travel_min)

    def _get_travel_time(self, v1: str, v2: str) -> timedelta:
        if v1 == v2:
            return timedelta(0)
        minutes = self.travel_overrides.get(
            (v1, v2),
            self.travel_overrides.get((v2, v1), self.venue_travel_min),
        )
        return timedelta(minutes=minutes)

    def detect_conflicts(
        self,
        sessions: List[Dict[str, Any]],
        participant_teams: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Scans all sessions and returns detected conflicts categorized by type and severity."""
        conflicts: List[Dict[str, Any]] = []
        participant_teams = participant_teams or {}

        # -----------------------------------------------------------------
        # 1. VENUE DOUBLE-BOOKING, SETUP_TEARDOWN_CONFLICT, OPERATING_HOUR_CONFLICT, CAPACITY_VIOLATION
        # -----------------------------------------------------------------
        by_venue: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for s in sessions:
            vid = s.get("venue_id")
            if vid:
                by_venue[vid].append(s)

        for vid, s_list in by_venue.items():
            venue_info = self.venue_map.get(vid, {})
            v_cap = int(venue_info.get("capacity", 100))
            windows = self.venue_windows.get(vid, [])

            # Check individual session validity
            for s in s_list:
                start_dt = s["start_at"]
                end_dt = s["end_at"]
                entrants = s.get("entrants_count", 0)

                # 6. CAPACITY_VIOLATION
                if entrants > v_cap:
                    conflicts.append({
                        "conflict_type": "CAPACITY_VIOLATION",
                        "severity": 4,  # Critical / Blocking
                        "description": (
                            f"Session {s['id']} ({s.get('event_name')}) has {entrants} entrants, "
                            f"exceeding venue {venue_info.get('name', vid)} capacity of {v_cap}."
                        ),
                        "entity_refs": {
                            "session_id": s["id"],
                            "venue_id": vid,
                            "entrants": entrants,
                            "capacity": v_cap,
                        },
                    })

                # 10. OPERATING_HOUR_CONFLICT
                in_window = False
                for ws, we in windows:
                    if ws <= start_dt and end_dt <= we:
                        in_window = True
                        break
                if not in_window:
                    conflicts.append({
                        "conflict_type": "OPERATING_HOUR_CONFLICT",
                        "severity": 3,
                        "description": (
                            f"Session {s['id']} ({s.get('event_name')}) runs from {start_dt.isoformat()} to {end_dt.isoformat()}, "
                            f"which is outside the operating hours of venue {venue_info.get('name', vid)}."
                        ),
                        "entity_refs": {"session_id": s["id"], "venue_id": vid},
                    })

                # 9. SETUP_TEARDOWN_CONFLICT against window boundary
                if in_window and not fits_in_venue_windows(start_dt, end_dt, windows, self.setup_td, self.teardown_td):
                    conflicts.append({
                        "conflict_type": "SETUP_TEARDOWN_CONFLICT",
                        "severity": 2,
                        "description": (
                            f"Session {s['id']} requires {self.setup_buffer_min}m setup and {self.teardown_buffer_min}m teardown, "
                            f"which extends beyond operating window boundaries at venue {venue_info.get('name', vid)}."
                        ),
                        "entity_refs": {"session_id": s["id"], "venue_id": vid},
                    })

            # Check pairwise venue overlaps
            sorted_venue_sessions = sorted(s_list, key=lambda x: x["start_at"])
            for i in range(len(sorted_venue_sessions)):
                for j in range(i + 1, len(sorted_venue_sessions)):
                    s1 = sorted_venue_sessions[i]
                    s2 = sorted_venue_sessions[j]

                    # 5. VENUE_DOUBLE_BOOKING (Direct overlap: start_a < end_b and start_b < end_a)
                    if interval_overlaps(s1["start_at"], s1["end_at"], s2["start_at"], s2["end_at"]):
                        conflicts.append({
                            "conflict_type": "VENUE_DOUBLE_BOOKING",
                            "severity": 4,  # Blocking
                            "description": (
                                f"Direct venue overlap at {venue_info.get('name', vid)} between "
                                f"Session {s1['id']} ({s1.get('event_name')}) and Session {s2['id']} ({s2.get('event_name')})."
                            ),
                            "entity_refs": {
                                "venue_id": vid,
                                "session_a_id": s1["id"],
                                "session_b_id": s2["id"],
                            },
                        })

                    # 9. SETUP_TEARDOWN_CONFLICT between adjacent sessions
                    elif interval_overlaps(
                        s1["start_at"], s1["end_at"],
                        s2["start_at"], s2["end_at"],
                        buffer_before=self.setup_td,
                        buffer_after=self.teardown_td,
                    ):
                        conflicts.append({
                            "conflict_type": "SETUP_TEARDOWN_CONFLICT",
                            "severity": 2,
                            "description": (
                                f"Setup/teardown buffer collision at {venue_info.get('name', vid)} between "
                                f"Session {s1['id']} and Session {s2['id']}."
                            ),
                            "entity_refs": {
                                "venue_id": vid,
                                "session_a_id": s1["id"],
                                "session_b_id": s2["id"],
                            },
                        })

        # -----------------------------------------------------------------
        # 2. PARTICIPANT_CLASH & INSUFFICIENT_TRAVEL_TIME
        # -----------------------------------------------------------------
        participant_sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for s in sessions:
            pids = s.get("assigned_participant_ids") or []
            for pid in pids:
                participant_sessions[pid].append(s)

        for pid, p_sess in participant_sessions.items():
            if len(p_sess) < 2:
                continue
            sorted_ps = sorted(p_sess, key=lambda x: x["start_at"])
            for i in range(len(sorted_ps)):
                for j in range(i + 1, len(sorted_ps)):
                    s1 = sorted_ps[i]
                    s2 = sorted_ps[j]
                    v1 = s1.get("venue_id", "")
                    v2 = s2.get("venue_id", "")
                    t_td = self._get_travel_time(v1, v2)

                    # 1. PARTICIPANT_CLASH
                    if interval_overlaps(s1["start_at"], s1["end_at"], s2["start_at"], s2["end_at"]):
                        conflicts.append({
                            "conflict_type": "PARTICIPANT_CLASH",
                            "severity": 4,  # Blocking
                            "description": (
                                f"Participant {pid} is scheduled in overlapping sessions: "
                                f"{s1['id']} ({s1.get('event_name')}) and {s2['id']} ({s2.get('event_name')})."
                            ),
                            "entity_refs": {
                                "participant_id": pid,
                                "session_a_id": s1["id"],
                                "session_b_id": s2["id"],
                            },
                        })
                    # 8. INSUFFICIENT_TRAVEL_TIME
                    elif v1 != v2 and interval_overlaps(
                        s1["start_at"], s1["end_at"],
                        s2["start_at"], s2["end_at"],
                        buffer_before=t_td,
                        buffer_after=t_td,
                    ):
                        conflicts.append({
                            "conflict_type": "INSUFFICIENT_TRAVEL_TIME",
                            "severity": 2,
                            "description": (
                                f"Participant {pid} has insufficient travel time between venue {v1} and {v2} "
                                f"between Session {s1['id']} and Session {s2['id']} (needs {int(t_td.total_seconds() / 60)}m)."
                            ),
                            "entity_refs": {
                                "participant_id": pid,
                                "from_venue_id": v1,
                                "to_venue_id": v2,
                                "session_a_id": s1["id"],
                                "session_b_id": s2["id"],
                            },
                        })

        # -----------------------------------------------------------------
        # 3. TEAM_CLASH
        # -----------------------------------------------------------------
        team_sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for s in sessions:
            team_id = s.get("team_id")
            if team_id:
                team_sessions[team_id].append(s)

        for tid, t_sess in team_sessions.items():
            if len(t_sess) < 2:
                continue
            sorted_ts = sorted(t_sess, key=lambda x: x["start_at"])
            for i in range(len(sorted_ts)):
                for j in range(i + 1, len(sorted_ts)):
                    s1 = sorted_ts[i]
                    s2 = sorted_ts[j]
                    if interval_overlaps(s1["start_at"], s1["end_at"], s2["start_at"], s2["end_at"]):
                        conflicts.append({
                            "conflict_type": "TEAM_CLASH",
                            "severity": 3,
                            "description": (
                                f"Team {tid} is scheduled in overlapping sessions: "
                                f"{s1['id']} and {s2['id']}."
                            ),
                            "entity_refs": {
                                "team_id": tid,
                                "session_a_id": s1["id"],
                                "session_b_id": s2["id"],
                            },
                        })

        # -----------------------------------------------------------------
        # 4. JUDGE_DOUBLE_BOOKING
        # -----------------------------------------------------------------
        judge_sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for s in sessions:
            judges = s.get("assigned_judges") or []
            for jid in judges:
                judge_sessions[jid].append(s)

        for jid, j_sess in judge_sessions.items():
            if len(j_sess) < 2:
                continue
            sorted_js = sorted(j_sess, key=lambda x: x["start_at"])
            for i in range(len(sorted_js)):
                for j in range(i + 1, len(sorted_js)):
                    s1 = sorted_js[i]
                    s2 = sorted_js[j]
                    v1 = s1.get("venue_id", "")
                    v2 = s2.get("venue_id", "")
                    t_td = self._get_travel_time(v1, v2)

                    if interval_overlaps(
                        s1["start_at"], s1["end_at"],
                        s2["start_at"], s2["end_at"],
                        buffer_before=t_td,
                        buffer_after=t_td,
                    ):
                        conflicts.append({
                            "conflict_type": "JUDGE_DOUBLE_BOOKING",
                            "severity": 3,
                            "description": (
                                f"Judge {jid} is double-booked or lacks travel buffer between "
                                f"Session {s1['id']} and Session {s2['id']}."
                            ),
                            "entity_refs": {
                                "judge_id": jid,
                                "session_a_id": s1["id"],
                                "session_b_id": s2["id"],
                            },
                        })

        # -----------------------------------------------------------------
        # 5. VOLUNTEER_DOUBLE_BOOKING
        # -----------------------------------------------------------------
        # Sweep-line concurrency test for total volunteer requirement
        vol_events: List[Tuple[datetime, int, str]] = []
        for s in sessions:
            v_req = int(s.get("volunteers_required", 0))
            if v_req > 0:
                vol_events.append((s["start_at"], v_req, s["id"]))
                vol_events.append((s["end_at"], -v_req, s["id"]))

        vol_events.sort(key=lambda x: x[0])
        current_volunteers = 0
        active_session_ids = set()

        for t, v_delta, s_id in vol_events:
            current_volunteers += v_delta
            if v_delta > 0:
                active_session_ids.add(s_id)
            else:
                active_session_ids.discard(s_id)

            if current_volunteers > self.available_volunteers_total:
                conflicts.append({
                    "conflict_type": "VOLUNTEER_DOUBLE_BOOKING",
                    "severity": 1,  # Warning
                    "description": (
                        f"Simultaneous volunteer requirement ({current_volunteers}) at {t.isoformat()} "
                        f"exceeds total volunteer availability ({self.available_volunteers_total})."
                    ),
                    "entity_refs": {
                        "time": t.isoformat(),
                        "required": current_volunteers,
                        "available": self.available_volunteers_total,
                        "active_sessions": list(active_session_ids),
                    },
                })
                break  # Record one peak warning

        # -----------------------------------------------------------------
        # 6. EQUIPMENT_CONFLICT
        # -----------------------------------------------------------------
        # Track simultaneous equipment requirements across active sessions
        eq_events: Dict[str, List[Tuple[datetime, int, str]]] = defaultdict(list)
        for s in sessions:
            eq_str = s.get("equipment_required")
            if eq_str and eq_str != "no special equipment":
                for item in eq_str.split(";"):
                    clean_item = item.strip().lower()
                    if clean_item:
                        # Simple extraction: if starts with number like '2 mics'
                        parts = clean_item.split(" ")
                        qty = 1
                        if parts[0].isdigit():
                            qty = int(parts[0])
                            clean_item = " ".join(parts[1:])
                        eq_events[clean_item].append((s["start_at"], qty, s["id"]))
                        eq_events[clean_item].append((s["end_at"], -qty, s["id"]))

        for item, events_list in eq_events.items():
            avail_stock = self.equipment_port.get_available_quantity(item)
            events_list.sort(key=lambda x: x[0])
            cur_req = 0
            for t, delta, s_id in events_list:
                cur_req += delta
                if cur_req > avail_stock:
                    conflicts.append({
                        "conflict_type": "EQUIPMENT_CONFLICT",
                        "severity": 2,
                        "description": (
                            f"Equipment demand for '{item}' ({cur_req}) at {t.isoformat()} "
                            f"exceeds available stock ({avail_stock})."
                        ),
                        "entity_refs": {
                            "item": item,
                            "required": cur_req,
                            "available": avail_stock,
                            "session_id": s_id,
                        },
                    })
                    break

        return conflicts
