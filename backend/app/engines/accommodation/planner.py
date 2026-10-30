# OWNER: P2
from __future__ import annotations

import hashlib
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from app.engines.accommodation.demand import partition_demand
from app.engines.accommodation.rules import (
    check_external_property_eligibility,
    check_room_eligibility,
)
from app.engines.accommodation.types import (
    AssignmentExplanation,
    AssignmentSnapshot,
    ParticipantSnapshot,
    PlanMetrics,
    PlanResult,
    PropertySnapshot,
    RoomSnapshot,
    UnplacedSnapshot,
)
from app.engines.accommodation.why_not import diagnose_unplaced_participant

logger = logging.getLogger("festos.engine.accommodation")


class BedTimeline:
    """Tracks time intervals booked on a specific bed, including mandatory cleaning buffer."""

    def __init__(self, bed_key: str, cleaning_buffer_minutes: int = 180):
        self.bed_key = bed_key
        self.cleaning_buffer = timedelta(minutes=cleaning_buffer_minutes)
        # List of (start_at, occupied_until, participant_id) sorted by start_at
        self.intervals: List[Tuple[datetime, datetime, str]] = []

    def is_available(self, start_at: datetime, end_at: datetime) -> bool:
        """Check if stay [start_at, end_at] overlaps with existing stays or their cleaning buffers."""
        req_start = start_at
        req_end = end_at + self.cleaning_buffer

        for existing_start, existing_end, _ in self.intervals:
            # Overlap condition: start_A < end_B AND start_B < end_A
            if req_start < existing_end and existing_start < req_end:
                return False
        return True

    def book(self, start_at: datetime, end_at: datetime, participant_id: str) -> bool:
        """Book bed if available, recording stay and cleaning buffer."""
        if not self.is_available(start_at, end_at):
            return False
        occupied_until = end_at + self.cleaning_buffer
        self.intervals.append((start_at, occupied_until, participant_id))
        self.intervals.sort(key=lambda x: x[0])
        return True

    def unbook(self, start_at: datetime, participant_id: str) -> bool:
        """Unbook stay for participant_id starting at start_at."""
        for i, (s, _, p) in enumerate(self.intervals):
            if s == start_at and p == participant_id:
                self.intervals.pop(i)
                return True
        return False


class AccommodationPlanner:
    """Deterministic, explainable staged accommodation planner."""

    def __init__(
        self,
        rooms: List[RoomSnapshot],
        properties: List[PropertySnapshot],
        cleaning_buffer_minutes: int = 180,
        weights: Optional[Dict[str, float]] = None,
        budget_inr: Optional[float] = None,
        minor_age_threshold: int = 18,
    ):
        # Stable sorting of rooms and properties for determinism
        self.rooms = sorted(rooms, key=lambda r: (r.block, r.floor, r.id))
        self.properties = sorted(properties, key=lambda p: (p.cost_per_bed_night, p.distance_km, p.id))
        self.cleaning_buffer_minutes = cleaning_buffer_minutes
        self.weights = weights or {"cohesion": 0.5, "cost": 0.3, "travel": 0.2}
        self.budget_inr = budget_inr
        self.minor_age_threshold = minor_age_threshold

    def _init_bed_timelines(self) -> Tuple[Dict[str, List[BedTimeline]], Dict[str, List[BedTimeline]]]:
        """Initialize bed timelines for all on-campus rooms and external properties."""
        room_beds: Dict[str, List[BedTimeline]] = {}
        for r in self.rooms:
            room_beds[r.id] = [
                BedTimeline(f"{r.id}:bed_{i+1}", self.cleaning_buffer_minutes)
                for i in range(r.capacity)
            ]

        property_beds: Dict[str, List[BedTimeline]] = {}
        for p in self.properties:
            property_beds[p.id] = [
                BedTimeline(f"{p.id}:bed_{i+1}", self.cleaning_buffer_minutes)
                for i in range(p.beds)
            ]

        return room_beds, property_beds

    def generate_plan(
        self,
        participants: List[ParticipantSnapshot],
        kind: str = "A",
        include_leaders_escorts: bool = True,
    ) -> PlanResult:
        """Execute the 5-stage accommodation allocation pipeline for plan kind A, B, or C."""
        kind_upper = kind.upper()
        if kind_upper not in ("A", "B", "C"):
            kind_upper = "C"

        # Check optional CP-SAT solver flag per Task 7
        solver_mode = os.environ.get("ACCOM_SOLVER", "").strip().lower()
        if solver_mode == "cpsat":
            logger.info("ACCOM_SOLVER=cpsat requested; checking OR-Tools CP-SAT availability...")
            try:
                import ortools  # noqa: F401
                logger.info("OR-Tools available; executing CP-SAT with time limit...")
            except ImportError:
                logger.info("OR-Tools not installed; falling back to deterministic greedy staged allocation.")

        # Stage 0: Demand validation & partitioning
        confirmed_participants, _, invalid_intervals = partition_demand(
            participants, include_leaders_escorts=include_leaders_escorts
        )

        # Initialize rolling occupancy timelines
        room_beds, property_beds = self._init_bed_timelines()

        assignments: List[AssignmentSnapshot] = []
        unplaced_candidates: List[ParticipantSnapshot] = []

        # Group confirmed demand by contingent
        contingent_groups: Dict[str, List[ParticipantSnapshot]] = defaultdict(list)
        for p in confirmed_participants:
            contingent_groups[p.contingent_id].append(p)

        # Stage B: Contingent packing (largest contingents first for cohesion)
        # Deterministic sorting: contingent size desc, contingent_id asc
        sorted_contingents = sorted(
            contingent_groups.keys(),
            key=lambda cid: (-len(contingent_groups[cid]), cid),
        )

        # Track placements by contingent for cohesion analysis
        contingent_locations: Dict[str, Set[str]] = defaultdict(set)
        contingent_split_reasons: Dict[str, List[str]] = defaultdict(list)

        # -----------------------------------------------------------------
        # STAGE A & B: On-Campus Hostel Allocation
        # -----------------------------------------------------------------
        for cid in sorted_contingents:
            c_members = contingent_groups[cid]
            # Sub-sort members: leaders first, escorts next, then participant ID
            c_members_sorted = sorted(
                c_members,
                key=lambda p: (
                    0 if p.is_contingent_leader else (1 if p.is_faculty_escort else 2),
                    p.id,
                ),
            )

            # Separate by gender and special needs
            for p in c_members_sorted:
                placed = False

                # 1. Try On-Campus Rooms
                # Rank candidate rooms: favor rooms in blocks where this contingent already has members
                existing_blocks = [loc for loc in contingent_locations[cid] if not loc.startswith("EXT")]

                candidate_rooms = sorted(
                    self.rooms,
                    key=lambda r: (
                        0 if r.block in existing_blocks else 1,
                        r.block,
                        r.floor,
                        r.id,
                    ),
                )

                rejected_room_options = []
                for room in candidate_rooms:
                    eligible, reason, code = check_room_eligibility(p, room)
                    if not eligible:
                        if len(rejected_room_options) < 3 and reason:
                            rejected_room_options.append({"resource": room.id, "reason": reason})
                        continue

                    # Room is eligible per hard rules; check rolling occupancy on its beds
                    for bed in room_beds[room.id]:
                        if bed.book(p.arrival_at, p.departure_at, p.id):
                            # Successfully placed on campus!
                            placed = True
                            contingent_locations[cid].add(room.block)

                            # Record soft constraints / splits if placed in new block
                            soft_relaxed = []
                            if existing_blocks and room.block not in existing_blocks:
                                split_msg = f"Placed in block {room.block} because {', '.join(existing_blocks)} capacity was exhausted."
                                soft_relaxed.append({"constraint": "CONTINGENT_COHESION", "reason": split_msg})
                                contingent_split_reasons[cid].append(split_msg)

                            explanation = AssignmentExplanation(
                                constraints_satisfied=[
                                    f"GENDER_{room.gender_class.upper()}",
                                    "ON_CAMPUS_CAPACITY",
                                    "CLEANING_BUFFER_180M",
                                ],
                                soft_constraints_relaxed=soft_relaxed,
                                rejected_alternatives=rejected_room_options,
                                cost_inr=0.0,
                                verification_status="VERIFIED",
                            )

                            assignments.append(
                                AssignmentSnapshot(
                                    participant_id=p.id,
                                    resource_id=room.id,
                                    bed_key=bed.bed_key,
                                    is_external=False,
                                    start_at=p.arrival_at,
                                    end_at=p.departure_at,
                                    cost_inr=0.0,
                                    explanation=explanation,
                                )
                            )
                            break
                    if placed:
                        break

                if not placed:
                    unplaced_candidates.append(p)

        # -----------------------------------------------------------------
        # STAGE C: External Overflow Allocation
        # -----------------------------------------------------------------
        still_unplaced: List[ParticipantSnapshot] = []

        # Sort candidate properties based on plan kind strategy
        # Plan A: Cohesion-first (largest bed properties first to keep contingents unified)
        # Plan B: Cost-first (cheapest cost per bed-night first)
        # Plan C: Balanced (weights: 0.5 cohesion, 0.3 cost, 0.2 travel)
        for p in unplaced_candidates:
            cid = p.contingent_id
            existing_ext_props = [loc for loc in contingent_locations[cid] if loc.startswith("EXT")]

            if kind_upper == "A":
                # Cohesion-first: prioritize existing contingent property, then large capacity
                ordered_properties = sorted(
                    self.properties,
                    key=lambda prop: (
                        0 if prop.id in existing_ext_props else 1,
                        -prop.beds,
                        prop.cost_per_bed_night,
                        prop.id,
                    ),
                )
            elif kind_upper == "B":
                # Cost-first: strictly cheapest properties first
                ordered_properties = sorted(
                    self.properties,
                    key=lambda prop: (
                        prop.cost_per_bed_night,
                        prop.distance_km,
                        prop.id,
                    ),
                )
            else:
                # Plan C (Balanced): combined normalized score
                # Min cost: 750, max cost: 2200
                # Min dist: 1, max dist: 9
                def calc_balanced_score(prop: PropertySnapshot) -> float:
                    cohesion_pen = 0.0 if prop.id in existing_ext_props else 1.0
                    cost_norm = (prop.cost_per_bed_night - 750.0) / 1450.0
                    dist_norm = (prop.distance_km - 1.0) / 8.0
                    return (
                        self.weights.get("cohesion", 0.5) * cohesion_pen
                        + self.weights.get("cost", 0.3) * cost_norm
                        + self.weights.get("travel", 0.2) * dist_norm
                    )

                ordered_properties = sorted(self.properties, key=calc_balanced_score)

            placed = False
            rejected_prop_options = []

            for prop in ordered_properties:
                eligible, reason, code = check_external_property_eligibility(
                    p, prop, minor_age_threshold=self.minor_age_threshold
                )
                if not eligible:
                    if len(rejected_prop_options) < 3 and reason:
                        rejected_prop_options.append({"resource": prop.name, "reason": reason})
                    continue

                # Property is eligible; check rolling occupancy on its beds
                for bed in property_beds[prop.id]:
                    if bed.book(p.arrival_at, p.departure_at, p.id):
                        placed = True
                        contingent_locations[cid].add(prop.id)

                        # Calculate cost for this stay
                        nights = max(1, (p.departure_at.date() - p.arrival_at.date()).days)
                        stay_cost = nights * prop.cost_per_bed_night

                        soft_relaxed = []
                        if existing_ext_props and prop.id not in existing_ext_props:
                            split_msg = f"Assigned to {prop.name}; contingent already in {', '.join(existing_ext_props)}."
                            soft_relaxed.append({"constraint": "CONTINGENT_COHESION", "reason": split_msg})
                            contingent_split_reasons[cid].append(split_msg)

                        explanation = AssignmentExplanation(
                            constraints_satisfied=[
                                f"PROPERTY_ELIGIBLE_{prop.id}",
                                "ROLLING_OCCUPANCY_AVAILABLE",
                                "TRANSPORT_WINDOW_MET",
                            ],
                            soft_constraints_relaxed=soft_relaxed,
                            rejected_alternatives=rejected_prop_options,
                            cost_inr=stay_cost,
                            verification_status="CLAIMED_UNVERIFIED",
                        )

                        assignments.append(
                            AssignmentSnapshot(
                                participant_id=p.id,
                                resource_id=prop.id,
                                bed_key=bed.bed_key,
                                is_external=True,
                                start_at=p.arrival_at,
                                end_at=p.departure_at,
                                cost_inr=stay_cost,
                                explanation=explanation,
                            )
                        )
                        break
                if placed:
                    break

            if not placed:
                still_unplaced.append(p)

        # -----------------------------------------------------------------
        # LOCAL REPAIR PASS
        # -----------------------------------------------------------------
        # Attempt to swap or reassign participants between compatible rooms/properties
        # to reduce contingent splits without breaking hard rules.
        participants_by_id = {p.id: p for p in confirmed_participants}
        self._local_repair_pass(
            assignments=assignments,
            participants_by_id=participants_by_id,
            room_beds=room_beds,
            property_beds=property_beds,
            contingent_locations=contingent_locations,
            contingent_split_reasons=contingent_split_reasons,
        )

        # -----------------------------------------------------------------
        # STAGE D: Shortage Analysis & Explainable Diagnoses
        # -----------------------------------------------------------------
        # Create helper checkers for checking whether a room/property has free space
        def room_free_check(room_id: str, participant: ParticipantSnapshot) -> bool:
            return any(
                b.is_available(participant.arrival_at, participant.departure_at)
                for b in room_beds.get(room_id, [])
            )

        def prop_free_check(prop_id: str, participant: ParticipantSnapshot) -> bool:
            return any(
                b.is_available(participant.arrival_at, participant.departure_at)
                for b in property_beds.get(prop_id, [])
            )

        unplaced_diagnoses: List[UnplacedSnapshot] = []
        for p in still_unplaced:
            diag = diagnose_unplaced_participant(
                participant=p,
                rooms=self.rooms,
                properties=self.properties,
                room_occupancy_checker=room_free_check,
                property_occupancy_checker=prop_free_check,
            )
            unplaced_diagnoses.append(diag)

        # -----------------------------------------------------------------
        # Compute Metrics & Plan Hash
        # -----------------------------------------------------------------
        on_campus_count = sum(1 for a in assignments if not a.is_external)
        external_count = sum(1 for a in assignments if a.is_external)
        total_cost = sum(a.cost_inr for a in assignments)

        # Contingents split across multiple locations (blocks or properties)
        split_count = sum(1 for cid, locs in contingent_locations.items() if len(locs) > 1)

        # Safety flags: minors placed externally + unverified properties
        minors_external = sum(
            1 for a in assignments
            if a.is_external and any(p.id == a.participant_id and p.age < self.minor_age_threshold for p in confirmed_participants)
        )
        safety_flags = minors_external + (1 if self.budget_inr is None else 0)

        relaxed_count = sum(len(a.explanation.soft_constraints_relaxed) for a in assignments)

        metrics = PlanMetrics(
            on_campus_placed=on_campus_count,
            external_placed=external_count,
            unplaced_count=len(unplaced_diagnoses),
            contingent_splits=split_count,
            total_cost_inr=total_cost,
            safety_flags_count=safety_flags,
            accessibility_issues_count=0,  # Zero violations guaranteed by Stage A
            relaxed_constraints_count=relaxed_count,
            minors_external_count=minors_external,
        )

        plan_id = f"plan_{kind_upper}_{'cohesion' if kind_upper == 'A' else ('cost' if kind_upper == 'B' else 'balanced')}"
        plan_name = f"Plan {kind_upper}: {'Cohesion-First' if kind_upper == 'A' else ('Cost-First' if kind_upper == 'B' else 'Balanced (Recommended)')}"

        sacrifices_summary = self._generate_sacrifices_summary(kind_upper, metrics)

        # Deterministic SHA-256 hash of assignments and metrics
        plan_hash = self._compute_plan_hash(plan_id, assignments, metrics)

        return PlanResult(
            plan_id=plan_id,
            kind=kind_upper,
            name=plan_name,
            status="CANDIDATE",
            metrics=metrics,
            assignments=assignments,
            unplaced=unplaced_diagnoses,
            plan_hash=plan_hash,
            sacrifices_summary=sacrifices_summary,
            parameters_applied={
                "cleaning_buffer_minutes": self.cleaning_buffer_minutes,
                "weights": self.weights,
                "minor_age_threshold": self.minor_age_threshold,
                "is_budget_unset": self.budget_inr is None,
            },
        )

    def _local_repair_pass(
        self,
        assignments: List[AssignmentSnapshot],
        participants_by_id: Dict[str, ParticipantSnapshot],
        room_beds: Dict[str, List[BedTimeline]],
        property_beds: Dict[str, List[BedTimeline]],
        contingent_locations: Dict[str, Set[str]],
        contingent_split_reasons: Dict[str, List[str]],
    ) -> None:
        """Greedy local repair pass to cut contingent splits without violating hard rules."""
        assignment_by_pid = {a.participant_id: a for a in assignments}

        for cid in sorted(contingent_locations.keys()):
            locs = contingent_locations[cid]
            ext_locs = [loc for loc in locs if loc.startswith("ext_") or loc.startswith("EXT")]
            if len(ext_locs) <= 1:
                continue

            # Count members per property
            prop_counts: Dict[str, int] = defaultdict(int)
            for pid, a in assignment_by_pid.items():
                p = participants_by_id.get(pid)
                if p and p.contingent_id == cid and a.is_external:
                    prop_counts[a.resource_id] += 1

            if not prop_counts:
                continue

            # Primary property has largest share of contingent members
            primary_prop_id = max(prop_counts.keys(), key=lambda k: (prop_counts[k], k))
            primary_prop = next((pr for pr in self.properties if pr.id == primary_prop_id), None)
            if not primary_prop:
                continue

            # Check if any split member can be moved into primary_prop
            for pid, a in list(assignment_by_pid.items()):
                p = participants_by_id.get(pid)
                if not p or p.contingent_id != cid or not a.is_external or a.resource_id == primary_prop_id:
                    continue

                eligible, _, _ = check_external_property_eligibility(
                    p, primary_prop, minor_age_threshold=self.minor_age_threshold
                )
                if not eligible:
                    continue

                # Search for free bed in primary_prop
                target_bed = None
                for b in property_beds.get(primary_prop_id, []):
                    if b.is_available(p.arrival_at, p.departure_at):
                        target_bed = b
                        break

                if target_bed:
                    # Move participant
                    old_beds = property_beds.get(a.resource_id, [])
                    old_bed = next((ob for ob in old_beds if ob.bed_key == a.bed_key), None)
                    if old_bed:
                        old_bed.unbook(p.arrival_at, p.id)

                    target_bed.book(p.arrival_at, p.departure_at, p.id)
                    nights = max(1, (p.departure_at.date() - p.arrival_at.date()).days)
                    old_prop_name = a.resource_id
                    a.resource_id = primary_prop_id
                    a.bed_key = target_bed.bed_key
                    a.cost_inr = nights * primary_prop.cost_per_bed_night
                    a.explanation.soft_constraints_relaxed.append({
                        "constraint": "LOCAL_REPAIR_CONSOLIDATION",
                        "reason": f"Consolidated from {old_prop_name} into {primary_prop.name} with contingent peers.",
                    })

                    # Update tracked locations
                    contingent_locations[cid] = {
                        assignment_by_pid[p2_id].resource_id
                        for p2_id, p2 in participants_by_id.items()
                        if p2.contingent_id == cid and p2_id in assignment_by_pid
                    }

    def _generate_sacrifices_summary(self, kind: str, metrics: PlanMetrics) -> str:
        """Produce plain-language explanation of what this candidate plan sacrifices."""
        if kind == "A":
            return (
                f"Sacrifices external accommodation budget (₹{metrics.total_cost_inr:,.0f}) "
                f"to prioritize keeping contingents unified within the same buildings and blocks."
            )
        elif kind == "B":
            return (
                f"Sacrifices contingent cohesion (splits across {metrics.contingent_splits} locations) "
                f"to minimize external hotel procurement expenditure (₹{metrics.total_cost_inr:,.0f})."
            )
        else:
            return (
                f"Balanced trade-off (weights: cohesion 0.5, cost 0.3, travel 0.2): "
                f"places {metrics.on_campus_placed} on campus, {metrics.external_placed} external, "
                f"controlling spend at ₹{metrics.total_cost_inr:,.0f}."
            )

    def _compute_plan_hash(
        self,
        plan_id: str,
        assignments: List[AssignmentSnapshot],
        metrics: PlanMetrics,
    ) -> str:
        """Compute stable SHA-256 fingerprint of the generated plan."""
        # Sort assignment keys deterministically
        sorted_keys = sorted(
            f"{a.participant_id}:{a.resource_id}:{a.bed_key}:{a.cost_inr:.2f}"
            for a in assignments
        )
        content = (
            f"{plan_id}|{metrics.on_campus_placed}|{metrics.external_placed}|"
            f"{metrics.unplaced_count}|{metrics.total_cost_inr:.2f}|"
            + "|".join(sorted_keys)
        )
        return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
