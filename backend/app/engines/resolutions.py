# OWNER: P1
"""Pure Resolution Recommender.

No DB access, no FastAPI imports.
Evaluates candidate venue/time moves for schedule conflicts and ranks them by:
1. Conflicts resolved (higher is better)
2. New conflicts created (lower is better)
3. People affected (lower is better)
"""
from __future__ import annotations

import copy
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.engines.conflicts import PureConflictDetector


class PureResolutionRecommender:
    """Evaluates candidate schedule adjustments to resolve conflicts."""

    def __init__(
        self,
        conflict_detector: PureConflictDetector,
        events: List[Dict[str, Any]],
        venues: List[Dict[str, Any]],
        venue_compatibility: Optional[Dict[str, List[str]]] = None,
    ):
        self.detector = conflict_detector
        self.events = events
        self.venues = venues
        self.venue_map = {v["id"]: v for v in venues}
        self.compat = venue_compatibility or {}

    def recommend_for_conflict(
        self,
        conflict: Dict[str, Any],
        sessions: List[Dict[str, Any]],
        max_candidates: int = 5,
    ) -> List[Dict[str, Any]]:
        """Finds and ranks candidate resolutions for a specific conflict."""
        entity_refs = conflict.get("entity_refs", {})
        session_ids = []
        if "session_id" in entity_refs:
            session_ids.append(entity_refs["session_id"])
        if "session_a_id" in entity_refs:
            session_ids.append(entity_refs["session_a_id"])
        if "session_b_id" in entity_refs:
            session_ids.append(entity_refs["session_b_id"])

        if not session_ids:
            return []

        base_conflicts = self.detector.detect_conflicts(sessions)
        base_conflict_count = len(base_conflicts)

        candidate_plans: List[Dict[str, Any]] = []

        # Target session: evaluate moving or re-homing session_b first (or session_a)
        target_sid = session_ids[-1]
        target_session = next((s for s in sessions if s["id"] == target_sid), None)
        if not target_session:
            return []

        entrants = target_session.get("entrants_count", 1)

        # 1. Candidate time shifts (+30m, +60m, +90m, +120m, -60m)
        for offset_min in [60, 120, 180, -60]:
            offset = timedelta(minutes=offset_min)
            new_start = target_session["start_at"] + offset
            new_end = target_session["end_at"] + offset

            # Clone sessions and apply shift
            hypo_sessions = copy.deepcopy(sessions)
            for s in hypo_sessions:
                if s["id"] == target_sid:
                    s["start_at"] = new_start
                    s["end_at"] = new_end
                    break

            new_conflicts = self.detector.detect_conflicts(hypo_sessions)
            new_conflict_count = len(new_conflicts)

            resolved = max(0, base_conflict_count - new_conflict_count)
            created = max(0, new_conflict_count - (base_conflict_count - resolved))

            score = (resolved * 100) - (created * 150) - (entrants * 0.1)

            candidate_plans.append({
                "action": "schedule.move_session",
                "session_id": target_sid,
                "payload": {
                    "session_id": target_sid,
                    "new_start_at": new_start.isoformat(),
                    "new_end_at": new_end.isoformat(),
                },
                "conflicts_resolved": resolved,
                "new_conflicts_created": created,
                "people_affected": entrants,
                "score": score,
                "rationale": f"Shifts session {target_sid} by {offset_min:+d} minutes to clear overlap window.",
            })

        # 2. Candidate venue changes (alternative venues from compatibility map)
        ev_id = target_session.get("event_id")
        ev_info = next((e for e in self.events if e["id"] == ev_id), {})
        req = ev_info.get("venue_requirements", "")
        alt_venues = self.compat.get(req, [v["id"] for v in self.venues])

        for alt_vid in alt_venues:
            if alt_vid == target_session.get("venue_id"):
                continue

            alt_v_info = self.venue_map.get(alt_vid, {})
            # Check capacity
            if int(alt_v_info.get("capacity", 0)) < entrants:
                continue

            hypo_sessions = copy.deepcopy(sessions)
            for s in hypo_sessions:
                if s["id"] == target_sid:
                    s["venue_id"] = alt_vid
                    s["venue_name"] = alt_v_info.get("name", alt_vid)
                    break

            new_conflicts = self.detector.detect_conflicts(hypo_sessions)
            new_conflict_count = len(new_conflicts)
            resolved = max(0, base_conflict_count - new_conflict_count)
            created = max(0, new_conflict_count - (base_conflict_count - resolved))
            score = (resolved * 100) - (created * 150) - (entrants * 0.1)

            candidate_plans.append({
                "action": "schedule.change_venue",
                "session_id": target_sid,
                "payload": {
                    "session_id": target_sid,
                    "new_venue_id": alt_vid,
                },
                "conflicts_resolved": resolved,
                "new_conflicts_created": created,
                "people_affected": entrants,
                "score": score,
                "rationale": f"Reallocates session {target_sid} to compatible venue {alt_v_info.get('name', alt_vid)}.",
            })

        # Sort by score descending
        candidate_plans.sort(key=lambda c: c["score"], reverse=True)

        # Assign ranks
        results = []
        for rank, plan in enumerate(candidate_plans[:max_candidates], start=1):
            plan["rank"] = rank
            results.append(plan)

        return results
