# OWNER: P1
"""Pure business logic engine for Duty of Care and Shuttle Planning.

No database or framework dependencies; deterministic and unit-testable.
"""
import math
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional


class PureTransportEngine:
    @staticmethod
    def calculate_required_runs(passengers: int, capacity: int) -> int:
        """Computes required shuttle runs using ceil(passengers / capacity).

        Handles edge cases:
        - 0 passengers -> 0 runs
        - exact multiple: 30 / 15 -> 2 runs
        - remainder: 31 / 15 -> 3 runs
        """
        if passengers <= 0 or capacity <= 0:
            return 0
        return math.ceil(passengers / capacity)

    @staticmethod
    def calculate_shuttle_plan(
        external_passengers: List[Dict[str, Any]],
        external_properties: List[Dict[str, Any]],
        assumptions: Optional[Dict[str, Any]] = None,
        scheduled_runs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Groups journeys by property and time window, calculating required runs vs fleet capacity."""
        assump = assumptions or {}
        capacity = int(assump.get("shuttle_capacity_seats", 15))
        fleet_vehicles = int(assump.get("shuttle_vehicle_count", 4))

        runs = scheduled_runs or []
        prop_map = {p.get("id"): p for p in external_properties}

        # Group passengers by property and window (arrival/departure or session)
        def _get_time_key(val: Any) -> str:
            if isinstance(val, datetime):
                return val.strftime("%Y-%m-%dT%H:00:00Z")
            if isinstance(val, str) and len(val) >= 13:
                return f"{val[:13]}:00:00Z"
            return "2026-10-31T08:00:00Z"

        property_windows: Dict[str, Dict[str, int]] = {}
        for p in external_passengers:
            prop_id = p.get("property_id") or "EXT04"
            # Use movement timestamp or arrival/departure
            t_val = p.get("movement_time") or p.get("arrival_at") or p.get("departure_at") or "2026-10-31T00:30:00Z"
            w_key = _get_time_key(t_val)

            property_windows.setdefault(prop_id, {})
            property_windows[prop_id][w_key] = property_windows[prop_id].get(w_key, 0) + 1

        total_passengers = sum(
            sum(w.values()) for w in property_windows.values()
        )
        total_required_runs = 0
        total_confirmed_runs = 0
        property_plans = []

        for prop_id, prop_info in prop_map.items():
            dist = float(prop_info.get("distance_km", 0.0))
            trans_avail = str(prop_info.get("transport_availability", "yes")).lower()
            risk_level = "HIGH" if (dist >= 8.0 or trans_avail == "limited") else ("MEDIUM" if dist >= 5.0 else "LOW")

            windows_data = []
            prop_win = property_windows.get(prop_id, {})
            for w_start, count in sorted(prop_win.items()):
                req_runs = PureTransportEngine.calculate_required_runs(count, capacity)
                total_required_runs += req_runs

                # Count runs scheduled for this property in this window
                conf_runs = sum(
                    1 for r in runs
                    if r.get("property_id") == prop_id and _get_time_key(r.get("departure_at")) == w_start
                )
                total_confirmed_runs += conf_runs
                shortage = max(0, req_runs - conf_runs)

                try:
                    dt = datetime.fromisoformat(w_start.replace("Z", "+00:00"))
                    w_end = (dt + timedelta(hours=1)).isoformat()
                except Exception:
                    w_end = w_start

                windows_data.append({
                    "window_start": w_start,
                    "window_end": w_end,
                    "passengers": count,
                    "required_runs": req_runs,
                    "confirmed_runs": conf_runs,
                    "shortage": shortage,
                    "is_uncovered": shortage > 0,
                })

            property_plans.append({
                "property_id": prop_id,
                "property_name": prop_info.get("name") or prop_info.get("property_name") or prop_id,
                "distance_km": dist,
                "transport_availability": trans_avail,
                "risk_level": risk_level,
                "windows": windows_data,
            })

        shortage_runs = max(0, total_required_runs - total_confirmed_runs)
        return {
            "plan_summary": {
                "total_passengers_external": total_passengers,
                "total_runs_required": total_required_runs,
                "total_runs_capacity": len(runs),
                "fleet_vehicles_available": fleet_vehicles,
                "shortage_runs": shortage_runs,
                "is_capacity_deficit": shortage_runs > 0,
            },
            "property_plans": property_plans,
        }

    @staticmethod
    def is_late_night(dt: datetime, late_night_start: str = "22:00", late_night_end: str = "06:00") -> bool:
        """Returns True if time falls within late-night window (e.g. 22:00 to 06:00)."""
        try:
            start_parts = [int(p) for p in late_night_start.split(":")]
            end_parts = [int(p) for p in late_night_end.split(":")]
            t_start = time(start_parts[0], start_parts[1])
            t_end = time(end_parts[0], end_parts[1])
        except Exception:
            t_start = time(22, 0)
            t_end = time(6, 0)

        t_cur = dt.time()
        if t_start > t_end:  # Over midnight: e.g. 22:00 to 06:00
            return t_cur >= t_start or t_cur <= t_end
        else:
            return t_start <= t_cur <= t_end

    @staticmethod
    def build_night_safety_roster(
        participants: List[Dict[str, Any]],
        external_properties: List[Dict[str, Any]],
        assumptions: Optional[Dict[str, Any]] = None,
        shuttle_assignments: Optional[List[Dict[str, Any]]] = None,
        escort_assignments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Identifies participants moving during late-night hours without verified escort and shuttle."""
        assump = assumptions or {}
        ln_start = assump.get("late_night_start", "22:00")
        ln_end = assump.get("late_night_end", "06:00")

        prop_map = {p.get("id"): p for p in external_properties}
        assignments = {a.get("participant_id"): a for a in (shuttle_assignments or [])}
        escorts = {e.get("participant_id"): e for e in (escort_assignments or [])}

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

        late_night_movements = []
        for p in participants:
            pid = p.get("id")
            prop_id = p.get("property_id")
            # Check arrivals and departures
            arr = _to_dt(p.get("arrival_at"))
            dep = _to_dt(p.get("departure_at"))

            movements_to_check = []
            if arr and PureTransportEngine.is_late_night(arr, ln_start, ln_end):
                movements_to_check.append(("ARRIVAL", arr))
            if dep and PureTransportEngine.is_late_night(dep, ln_start, ln_end):
                movements_to_check.append(("DEPARTURE", dep))

            # Also check if participant has an assigned movement_time
            mv_time = _to_dt(p.get("movement_time"))
            if mv_time and PureTransportEngine.is_late_night(mv_time, ln_start, ln_end):
                movements_to_check.append(("TRANSFER", mv_time))

            for m_type, m_dt in movements_to_check:
                shuttle_asn = assignments.get(pid)
                escort_asn = escorts.get(pid)
                has_shuttle = bool(shuttle_asn and shuttle_asn.get("shuttle_run_id"))
                has_escort = bool(escort_asn and escort_asn.get("staff_id"))
                safety_verified = bool(p.get("safety_verified") or (shuttle_asn and shuttle_asn.get("safety_verified")))

                p_info = prop_map.get(prop_id, {})
                prop_name = p_info.get("name") or p_info.get("property_name") or (prop_id or "External Property")

                age = p.get("age")
                is_minor = (age is not None and age < 18)

                late_night_movements.append({
                    "participant_id": pid,
                    "name": p.get("name", "Unknown"),
                    "contingent_id": p.get("contingent_id"),
                    "contingent_name": p.get("contingent_name") or p.get("college"),
                    "property_id": prop_id or "EXT04",
                    "property_name": prop_name,
                    "scheduled_time": m_dt.isoformat(),
                    "movement_type": m_type,
                    "is_minor": is_minor,
                    "shuttle_assigned": has_shuttle,
                    "escort_assigned": has_escort,
                    "safety_verified": safety_verified,
                })

        unverified_count = sum(1 for m in late_night_movements if not m["safety_verified"])
        return {
            "late_night_movements": late_night_movements,
            "total_unverified": unverified_count,
        }

    @staticmethod
    def evaluate_guardian_queue(
        minors: List[Dict[str, Any]],
        approvals: Optional[List[Dict[str, Any]]] = None,
        external_properties: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Evaluates guardian approval queue for minors residing off-campus (~71 baseline)."""
        prop_map = {p.get("id"): p for p in (external_properties or [])}
        approvals_map = {a.get("participant_id"): a for a in (approvals or [])}

        queue = []
        for m in minors:
            pid = m.get("id") or m.get("participant_id")
            appr = approvals_map.get(pid, {})
            prop_id = m.get("property_id") or appr.get("property_id") or "EXT03"
            p_info = prop_map.get(prop_id, {})
            prop_name = p_info.get("name") or p_info.get("property_name") or prop_id

            status = appr.get("approval_status") or m.get("approval_status") or "PENDING"
            queue.append({
                "approval_id": appr.get("id") or f"gdn_{pid}",
                "participant_id": pid,
                "participant_name": m.get("name") or m.get("participant_name") or "Minor Participant",
                "age": m.get("age", 17),
                "contingent_id": m.get("contingent_id"),
                "contingent_name": m.get("contingent_name") or m.get("college"),
                "property_id": prop_id,
                "property_name": prop_name,
                "stay_duration_days": int(appr.get("stay_duration_days") or m.get("stay_duration_days") or 3),
                "approval_status": status,
                "escort_staff_id": appr.get("escort_staff_id") or m.get("escort_staff_id"),
                "escort_staff_name": appr.get("escort_staff_name") or m.get("escort_staff_name"),
                "transport_arrangement": appr.get("transport_arrangement") or "Assigned Campus Shuttle",
                "responsible_coordinator_id": appr.get("responsible_coordinator_id") or "ST02",
                "responsible_coordinator_name": appr.get("responsible_coordinator_name") or "Ananya Patel",
            })

        pending_count = sum(1 for q in queue if q["approval_status"] == "PENDING")
        return {
            "minors_queue": queue,
            "total": len(queue),
            "pending_count": pending_count,
        }

    @staticmethod
    def generate_transport_alerts(
        shuttle_plan: Dict[str, Any],
        night_roster: Dict[str, Any],
        guardian_queue: Dict[str, Any],
    ) -> List[str]:
        """Generates clear, actionable plain-text safety alerts for festival operators."""
        alerts = []

        # 1. Unverified late night movements
        unverified = [m for m in night_roster.get("late_night_movements", []) if not m["safety_verified"]]
        if unverified:
            by_prop: Dict[str, List[Dict[str, Any]]] = {}
            for u in unverified:
                by_prop.setdefault(u["property_name"], []).append(u)
            for prop_name, items in by_prop.items():
                t_str = items[0]["scheduled_time"][11:16]
                alerts.append(
                    f"{len(items)} participants are scheduled to leave {prop_name} at {t_str}, but no verified shuttle is assigned."
                )

        # 2. Minors pending guardian approvals
        pending_minors = guardian_queue.get("pending_count", 0)
        if pending_minors > 0:
            alerts.append(
                f"{pending_minors} minors in external accommodation are pending guardian and escort verification."
            )

        # 3. Peak shuttle run deficits
        for prop in shuttle_plan.get("property_plans", []):
            p_name = prop.get("property_name")
            for win in prop.get("windows", []):
                if win.get("shortage", 0) > 0:
                    w_start = win["window_start"].replace("Z", "").replace("T", " ")
                    alerts.append(
                        f"Peak window at {p_name} on {w_start} has a deficit of {win['shortage']} shuttle runs ({win['passengers']} passengers uncovered)."
                    )

        # 4. High-risk properties
        for prop in shuttle_plan.get("property_plans", []):
            if prop.get("risk_level") == "HIGH":
                alerts.append(
                    f"Property {prop.get('property_name')} ({prop.get('distance_km')}km) has limited commercial transport availability and high duty-of-care risk."
                )

        if not alerts:
            alerts.append("All external property transit runs and duty-of-care arrangements verified.")

        return alerts

    @staticmethod
    def check_transport_feasibility(
        property_id: str,
        target_time: datetime,
        external_properties: List[Dict[str, Any]],
        assumptions: Optional[Dict[str, Any]] = None,
        scheduled_runs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Exposed for accommodation engine rule 6: checks if transport to/from external property is feasible."""
        assump = assumptions or {}
        hours_start = assump.get("transport_hours_start", "06:00")
        hours_end = assump.get("transport_hours_end", "24:00")

        prop_map = {p.get("id"): p for p in external_properties}
        p_info = prop_map.get(property_id)
        if not p_info:
            return {"property_id": property_id, "time": target_time.isoformat(), "is_feasible": False, "reason": f"Unknown external property {property_id}"}

        # Check operating hours
        try:
            h_start = int(hours_start.split(":")[0])
            h_end = int(hours_end.split(":")[0])
            cur_h = target_time.hour
            is_within_hours = (h_start <= cur_h <= h_end) if h_end >= h_start else (cur_h >= h_start or cur_h <= h_end)
        except Exception:
            is_within_hours = (6 <= target_time.hour <= 23)

        # Check for dedicated shuttle run
        has_scheduled_run = False
        runs = scheduled_runs or []
        for r in runs:
            if r.get("property_id") == property_id and r.get("departure_at"):
                r_dep = r["departure_at"]
                if isinstance(r_dep, str):
                    try:
                        r_dep = datetime.fromisoformat(r_dep.replace("Z", "+00:00"))
                    except Exception:
                        continue
                if abs((r_dep - target_time).total_seconds()) <= 1800:  # within 30 mins
                    has_scheduled_run = True
                    break

        if is_within_hours or has_scheduled_run:
            return {
                "property_id": property_id,
                "time": target_time.isoformat(),
                "is_feasible": True,
                "reason": "Within standard transport hours or dedicated shuttle run confirmed",
            }
        else:
            return {
                "property_id": property_id,
                "time": target_time.isoformat(),
                "is_feasible": False,
                "reason": f"Outside standard transport hours ({hours_start}-{hours_end}) with no scheduled dedicated shuttle run",
            }
