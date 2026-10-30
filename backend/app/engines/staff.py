# OWNER: P1
"""Pure business logic engine for Staff and Volunteer Management.

No database or framework dependencies; deterministic and unit-testable.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


class PureStaffEngine:
    @staticmethod
    def calculate_demand_and_gaps(
        sessions: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        time_window_hours: int = 1,
    ) -> Dict[str, Any]:
        """Calculates volunteer requirement demand over time from scheduled event sessions,

        compares against core team and volunteers on shift, and reports uncovered gaps.
        """
        valid_sessions = [
            s for s in sessions
            if s.get("start_at") and s.get("end_at") and s.get("volunteers_required")
        ]
        if not valid_sessions:
            return {
                "peak_requirement": 0,
                "peak_available_on_shift": 0,
                "max_gap": 0,
                "uncovered_hours_total": 0.0,
                "demand_timeline": [],
            }

        def _to_dt(val: Any) -> Optional[datetime]:
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
            return None

        # Determine timeline range
        session_starts = [_to_dt(s["start_at"]) for s in valid_sessions]
        session_ends = [_to_dt(s["end_at"]) for s in valid_sessions]
        session_starts = [t for t in session_starts if t]
        session_ends = [t for t in session_ends if t]

        if not session_starts or not session_ends:
            return {
                "peak_requirement": 0,
                "peak_available_on_shift": 0,
                "max_gap": 0,
                "uncovered_hours_total": 0.0,
                "demand_timeline": [],
            }

        min_time = min(session_starts).replace(minute=0, second=0, microsecond=0)
        max_time = max(session_ends)

        # Parse shifts
        valid_shifts = []
        for sh in shifts:
            st = _to_dt(sh.get("start_at"))
            et = _to_dt(sh.get("end_at"))
            status = sh.get("status", "SCHEDULED").upper()
            if st and et and status not in ("CANCELLED", "MISSED"):
                valid_shifts.append({
                    "id": sh.get("id"),
                    "staff_id": sh.get("staff_id"),
                    "start_at": st,
                    "end_at": et,
                })

        timeline = []
        cur = min_time
        peak_req = 0
        peak_avail = 0
        max_gap = 0
        uncovered_hours = 0.0

        step = timedelta(hours=time_window_hours)
        while cur < max_time:
            nxt = cur + step
            # Sessions overlapping [cur, nxt)
            active_sessions = [
                s for s in valid_sessions
                if _to_dt(s["start_at"]) < nxt and _to_dt(s["end_at"]) > cur
            ]
            req = sum(s.get("volunteers_required", 0) for s in active_sessions)

            # Shifts overlapping [cur, nxt)
            active_shifts = [
                sh for sh in valid_shifts
                if sh["start_at"] < nxt and sh["end_at"] > cur
            ]
            # Distinct staff on shift
            staff_ids = set(sh["staff_id"] for sh in active_shifts if sh.get("staff_id"))
            avail = len(staff_ids)

            gap = max(0, req - avail)
            is_under = gap > 0

            if req > peak_req:
                peak_req = req
            if avail > peak_avail:
                peak_avail = avail
            if gap > max_gap:
                max_gap = gap
            if is_under and req > 0:
                uncovered_hours += time_window_hours

            timeline.append({
                "time_window_start": cur.isoformat(),
                "time_window_end": nxt.isoformat(),
                "volunteers_required": req,
                "staff_on_shift": avail,
                "gap": gap,
                "is_understaffed": is_under,
            })

            cur = nxt

        return {
            "peak_requirement": peak_req,
            "peak_available_on_shift": peak_avail,
            "max_gap": max_gap,
            "uncovered_hours_total": float(uncovered_hours),
            "demand_timeline": timeline,
        }

    @staticmethod
    def detect_overloaded_staff(
        shifts: List[Dict[str, Any]],
        max_daily_hours: float = 10.0,
        max_consecutive_hours: float = 8.0,
    ) -> List[Dict[str, Any]]:
        """Identifies staff members exceeding daily maximum hours or consecutive hours."""
        def _to_dt(val: Any) -> Optional[datetime]:
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
            return None

        # Group shifts by staff_id
        staff_shifts: Dict[str, List[Tuple[datetime, datetime, Dict[str, Any]]]] = {}
        for sh in shifts:
            staff_id = sh.get("staff_id")
            if not staff_id or sh.get("status", "SCHEDULED").upper() in ("CANCELLED", "MISSED"):
                continue
            st = _to_dt(sh.get("start_at"))
            et = _to_dt(sh.get("end_at"))
            if st and et and et > st:
                staff_shifts.setdefault(staff_id, []).append((st, et, sh))

        overloaded = []
        for staff_id, s_list in staff_shifts.items():
            s_list.sort(key=lambda x: x[0])
            staff_name = s_list[0][2].get("staff_name") or staff_id

            # Check daily hours
            daily_hours: Dict[str, float] = {}
            for st, et, _ in s_list:
                day_key = st.strftime("%Y-%m-%d")
                duration = (et - st).total_seconds() / 3600.0
                daily_hours[day_key] = daily_hours.get(day_key, 0.0) + duration

            flagged = False
            for day_key, total_h in daily_hours.items():
                if total_h > max_daily_hours:
                    overloaded.append({
                        "staff_id": staff_id,
                        "name": staff_name,
                        "scheduled_hours": round(total_h, 1),
                        "consecutive_hours": round(total_h, 1),
                        "threshold_hours": max_daily_hours,
                        "date": day_key,
                        "reason": f"Exceeds daily maximum {max_daily_hours}h limit on {day_key} ({round(total_h, 1)}h scheduled)",
                    })
                    flagged = True

            # Check consecutive hours
            if not flagged and len(s_list) > 1:
                cur_run_start = s_list[0][0]
                cur_run_end = s_list[0][1]
                for st, et, _ in s_list[1:]:
                    # If gap <= 1 hour, consider consecutive
                    gap = (st - cur_run_end).total_seconds() / 3600.0
                    if gap <= 1.0:
                        cur_run_end = max(cur_run_end, et)
                    else:
                        consec = (cur_run_end - cur_run_start).total_seconds() / 3600.0
                        if consec > max_consecutive_hours:
                            overloaded.append({
                                "staff_id": staff_id,
                                "name": staff_name,
                                "scheduled_hours": round(consec, 1),
                                "consecutive_hours": round(consec, 1),
                                "threshold_hours": max_consecutive_hours,
                                "reason": f"Consecutive working hours ({round(consec, 1)}h) exceed threshold {max_consecutive_hours}h",
                            })
                            break
                        cur_run_start = st
                        cur_run_end = et

                consec = (cur_run_end - cur_run_start).total_seconds() / 3600.0
                if consec > max_consecutive_hours and not any(o["staff_id"] == staff_id for o in overloaded):
                    overloaded.append({
                        "staff_id": staff_id,
                        "name": staff_name,
                        "scheduled_hours": round(consec, 1),
                        "consecutive_hours": round(consec, 1),
                        "threshold_hours": max_consecutive_hours,
                        "reason": f"Consecutive working hours ({round(consec, 1)}h) exceed threshold {max_consecutive_hours}h",
                    })

        return overloaded

    @staticmethod
    def detect_conflicts(
        staff_list: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        travel_matrix: Optional[Dict[Tuple[str, str], int]] = None,
        participants: Optional[List[Dict[str, Any]]] = None,
        judges: Optional[List[Dict[str, Any]]] = None,
        contingents: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Identifies staff conflict of interests, dual roles, and shift overlap/travel infeasibility."""
        def _to_dt(val: Any) -> Optional[datetime]:
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
            return None

        conflicts = []
        travel_mat = travel_matrix or {}

        # 1. Dual role: Staff member registered as active participant/competitor
        participant_names = {}
        participant_phones = {}
        for p in (participants or []):
            if p.get("name"):
                participant_names[p["name"].strip().lower()] = p
            if p.get("phone"):
                participant_phones[p["phone"].strip()] = p

        for stf in staff_list:
            sid = stf.get("id")
            sname = stf.get("name", "")
            sphone = stf.get("phone", "")
            is_part = stf.get("is_participant", False)

            matched_p = None
            if is_part:
                matched_p = True
            elif sname and sname.strip().lower() in participant_names:
                matched_p = participant_names[sname.strip().lower()]
            elif sphone and sphone.strip() in participant_phones:
                matched_p = participant_phones[sphone.strip()]

            if matched_p:
                conflicts.append({
                    "staff_id": sid,
                    "name": sname,
                    "conflict_type": "PARTICIPANT_STAFF_DUAL_ROLE",
                    "details": f"Staff member '{sname}' ({sid}) is also registered as an active participant/competitor",
                })

            # Check self-contingent escort/judge conflict
            contingent_id = stf.get("contingent_id")
            assigned_escort = stf.get("assigned_contingent_escort")
            if contingent_id and assigned_escort and contingent_id == assigned_escort:
                conflicts.append({
                    "staff_id": sid,
                    "name": sname,
                    "conflict_type": "CONGESTION_ESCORT_SELF_INTEREST",
                    "details": f"Staff member '{sname}' is acting as dedicated escort for their own home contingent ({contingent_id})",
                })

        # 2. Shift overlaps and travel infeasibility
        staff_shifts: Dict[str, List[Dict[str, Any]]] = {}
        for sh in shifts:
            sid = sh.get("staff_id")
            if not sid or sh.get("status", "SCHEDULED").upper() in ("CANCELLED", "MISSED"):
                continue
            st = _to_dt(sh.get("start_at"))
            et = _to_dt(sh.get("end_at"))
            if st and et:
                item = dict(sh)
                item["start_dt"] = st
                item["end_dt"] = et
                staff_shifts.setdefault(sid, []).append(item)

        for sid, s_list in staff_shifts.items():
            s_list.sort(key=lambda x: x["start_dt"])
            for i in range(len(s_list)):
                for j in range(i + 1, len(s_list)):
                    sh1 = s_list[i]
                    sh2 = s_list[j]
                    # Check direct time overlap
                    if sh1["start_dt"] < sh2["end_dt"] and sh1["end_dt"] > sh2["start_dt"]:
                        conflicts.append({
                            "staff_id": sid,
                            "name": sh1.get("staff_name") or sid,
                            "conflict_type": "SHIFT_OVERLAP",
                            "details": f"Staff assigned to concurrent overlapping shifts: {sh1.get('id')} and {sh2.get('id')}",
                        })
                    else:
                        # Check travel time between different venues
                        v1 = sh1.get("venue_id")
                        v2 = sh2.get("venue_id")
                        if v1 and v2 and v1 != v2:
                            transit_min = travel_mat.get((v1, v2)) or travel_mat.get((v2, v1)) or 15
                            gap_sec = (sh2["start_dt"] - sh1["end_dt"]).total_seconds()
                            if 0 <= gap_sec < (transit_min * 60):
                                conflicts.append({
                                    "staff_id": sid,
                                    "name": sh1.get("staff_name") or sid,
                                    "conflict_type": "TRAVEL_TIME_INFEASIBLE",
                                    "details": f"Insufficient travel window between {v1} and {v2} (gap {round(gap_sec/60, 1)}m < needed {transit_min}m)",
                                })

        return conflicts

    @staticmethod
    def suggest_replacements(
        window_start: datetime,
        window_end: datetime,
        venue_id: Optional[str],
        role_required: Optional[str],
        staff_list: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        travel_matrix: Optional[Dict[Tuple[str, str], int]] = None,
        max_daily_hours: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """Finds and ranks emergency replacement staff who are available, skill-matched,

        not overloaded, and have minimal travel time to the venue.
        """
        def _to_dt(val: Any) -> Optional[datetime]:
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
            return None

        w_start = _to_dt(window_start)
        w_end = _to_dt(window_end)
        if not w_start or not w_end or w_end <= w_start:
            return []

        shift_duration_h = (w_end - w_start).total_seconds() / 3600.0
        w_date = w_start.strftime("%Y-%m-%d")
        travel_mat = travel_matrix or {}

        # Map current shifts per staff
        staff_assigned_shifts: Dict[str, List[Dict[str, Any]]] = {}
        staff_daily_hours: Dict[Tuple[str, str], float] = {}

        for sh in shifts:
            sid = sh.get("staff_id")
            if not sid or sh.get("status", "SCHEDULED").upper() in ("CANCELLED", "MISSED"):
                continue
            st = _to_dt(sh.get("start_at"))
            et = _to_dt(sh.get("end_at"))
            if st and et:
                item = dict(sh)
                item["start_dt"] = st
                item["end_dt"] = et
                staff_assigned_shifts.setdefault(sid, []).append(item)
                d_key = (sid, st.strftime("%Y-%m-%d"))
                staff_daily_hours[d_key] = staff_daily_hours.get(d_key, 0.0) + ((et - st).total_seconds() / 3600.0)

        suggestions = []
        for stf in staff_list:
            sid = stf.get("id")
            if not sid or stf.get("status", "ACTIVE").upper() != "ACTIVE":
                continue

            # Check if adding this shift exceeds daily threshold
            curr_hours = staff_daily_hours.get((sid, w_date), 0.0)
            if curr_hours + shift_duration_h > max_daily_hours:
                continue

            # Check for direct shift overlap or transit collision
            has_overlap = False
            min_transit_to_venue = 15
            for existing in staff_assigned_shifts.get(sid, []):
                e_start = existing["start_dt"]
                e_end = existing["end_dt"]
                if w_start < e_end and w_end > e_start:
                    has_overlap = True
                    break

                # Check travel time if adjacent
                e_venue = existing.get("venue_id")
                if e_venue and venue_id and e_venue != venue_id:
                    transit = travel_mat.get((e_venue, venue_id)) or travel_mat.get((venue_id, e_venue)) or 15
                    min_transit_to_venue = transit
                    # If existing shift immediately precedes window
                    if 0 <= (w_start - e_end).total_seconds() < (transit * 60):
                        has_overlap = True
                        break
                    # If existing shift immediately follows window
                    if 0 <= (e_start - w_end).total_seconds() < (transit * 60):
                        has_overlap = True
                        break

            if has_overlap:
                continue

            # Calculate candidate suitability score
            score = 50.0
            stf_role = stf.get("role", "")
            skills = [s.lower() for s in (stf.get("skills") or [])]

            role_match = False
            if role_required:
                if role_required.lower() in stf_role.lower() or stf_role.lower() in role_required.lower():
                    score += 25.0
                    role_match = True
                if any(role_required.lower() in sk for sk in skills):
                    score += 15.0
                    role_match = True

            # General volunteer skills match
            skills_match = role_match or bool(skills)

            # Favor staff with lower current hours (workload balance)
            score += max(0.0, (max_daily_hours - curr_hours) * 2.0)

            # Minimal travel time bonus
            score += max(0.0, 10.0 - (min_transit_to_venue / 5.0))

            suggestions.append({
                "staff_id": sid,
                "name": stf.get("name", sid),
                "role": stf_role,
                "travel_time_min": min_transit_to_venue,
                "skills_match": skills_match,
                "current_hours": round(curr_hours, 1),
                "is_available": True,
                "score": round(score, 1),
            })

        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions
