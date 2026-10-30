# OWNER: P2
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.engines.accommodation.types import (
    DemandTimelineResult,
    ParticipantSnapshot,
    TimelinePoint,
)


def validate_stay_interval(
    participant_id: str,
    name: str,
    arrival_at: Optional[datetime],
    departure_at: Optional[datetime],
) -> Tuple[bool, Optional[str]]:
    """Validate arrival and departure timestamps for a stay interval.

    Returns (is_valid, failure_reason).
    """
    if arrival_at is None:
        return False, "Missing arrival_datetime."
    if departure_at is None:
        return False, "Missing departure_datetime."
    if departure_at <= arrival_at:
        return False, "Departure is on or before arrival (zero or negative duration)."
    # Basic sanity limit (festival window is late October to early November 2026)
    duration_days = (departure_at - arrival_at).total_seconds() / 86400.0
    if duration_days > 14:
        return False, f"Stay duration exceeds 14 days ({duration_days:.1f} days)."
    return True, None


def partition_demand(
    participants: List[ParticipantSnapshot],
    include_leaders_escorts: bool = True,
) -> Tuple[List[ParticipantSnapshot], List[ParticipantSnapshot], List[Dict[str, str]]]:
    """Partition participants into confirmed demand, possible demand, and invalid intervals.

    Returns:
        confirmed: participants with accommodation_requested == 'YES' and valid intervals
        possible: participants with accommodation_requested == 'UNKNOWN' and valid intervals
        invalid: list of dicts detailing excluded participants with reasons
    """
    confirmed: List[ParticipantSnapshot] = []
    possible: List[ParticipantSnapshot] = []
    invalid: List[Dict[str, str]] = []

    for p in participants:
        req = (p.accommodation_requested or "").strip().upper()
        if req not in ("YES", "UNKNOWN"):
            continue

        if not include_leaders_escorts and (p.is_contingent_leader or p.is_faculty_escort):
            continue

        is_valid, reason = validate_stay_interval(p.id, p.name, p.arrival_at, p.departure_at)
        if not is_valid:
            invalid.append({
                "participant_id": p.id,
                "name": p.name,
                "contingent_id": p.contingent_id,
                "arrival_at": p.arrival_at.isoformat() if p.arrival_at else "",
                "departure_at": p.departure_at.isoformat() if p.departure_at else "",
                "reason": reason or "Invalid interval",
            })
            continue

        if req == "YES":
            confirmed.append(p)
        elif req == "UNKNOWN":
            possible.append(p)

    return confirmed, possible, invalid


def compute_bed_demand_timeline(
    confirmed_participants: List[ParticipantSnapshot],
    possible_participants: Optional[List[ParticipantSnapshot]] = None,
    invalid_intervals: Optional[List[Dict[str, str]]] = None,
    total_beds_supply: int = 1450,
    cleaning_buffer_minutes: int = 180,
    time_step_hours: int = 1,
    include_leaders_escorts: bool = True,
) -> DemandTimelineResult:
    """Compute time-series bed demand, rolling occupancy, cleaning buffers, and peak demand.

    Spec reference: ~1,601 simultaneous bed demand at 30 Oct 2026, 6 PM (18:00).
    """
    if possible_participants is None:
        confirmed_participants, possible_participants, invalid_intervals = partition_demand(
            confirmed_participants, include_leaders_escorts=include_leaders_escorts
        )
    if invalid_intervals is None:
        invalid_intervals = []

    all_valid = confirmed_participants + possible_participants
    if not all_valid:
        dummy_time = datetime(2026, 10, 30, 18, 0)
        return DemandTimelineResult(
            total_participants_requesting=0,
            valid_intervals_included=0,
            invalid_intervals_count=len(invalid_intervals),
            invalid_intervals=invalid_intervals,
            confirmed_demand_count=0,
            possible_demand_count=0,
            peak_simultaneous_demand=0,
            peak_time=dummy_time,
            timeline=[],
        )

    # Determine timeline boundaries rounded to full hour
    earliest_arr = min(p.arrival_at for p in all_valid if p.arrival_at)
    latest_dep = max(p.departure_at for p in all_valid if p.departure_at)

    start_hour = earliest_arr.replace(minute=0, second=0, microsecond=0)
    end_hour = latest_dep.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    timeline_points: List[TimelinePoint] = []
    peak_demand = 0
    peak_timestamp = start_hour

    cleaning_buffer_td = timedelta(minutes=cleaning_buffer_minutes)
    cur_time = start_hour

    while cur_time <= end_hour:
        # Confirmed demand present at cur_time (arrival <= cur_time < departure)
        conf_count = sum(
            1 for p in confirmed_participants
            if p.arrival_at and p.departure_at and p.arrival_at <= cur_time < p.departure_at
        )

        # Possible demand present at cur_time
        poss_count = sum(
            1 for p in possible_participants
            if p.arrival_at and p.departure_at and p.arrival_at <= cur_time < p.departure_at
        )

        # Beds undergoing cleaning: departure <= cur_time < departure + cleaning_buffer
        cleaning_count = sum(
            1 for p in confirmed_participants
            if p.departure_at and p.departure_at <= cur_time < (p.departure_at + cleaning_buffer_td)
        )

        timeline_points.append(
            TimelinePoint(
                timestamp=cur_time,
                confirmed_demand=conf_count,
                possible_demand=poss_count,
                cleaning_beds=cleaning_count,
                available_supply=total_beds_supply,
            )
        )

        # Track peak confirmed demand
        if conf_count > peak_demand:
            peak_demand = conf_count
            peak_timestamp = cur_time

        cur_time += timedelta(hours=time_step_hours)

    return DemandTimelineResult(
        total_participants_requesting=len(confirmed_participants) + len(invalid_intervals),
        valid_intervals_included=len(confirmed_participants),
        invalid_intervals_count=len(invalid_intervals),
        invalid_intervals=invalid_intervals,
        confirmed_demand_count=len(confirmed_participants),
        possible_demand_count=len(possible_participants),
        peak_simultaneous_demand=peak_demand,
        peak_time=peak_timestamp,
        timeline=timeline_points,
    )
