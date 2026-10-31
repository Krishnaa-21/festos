# OWNER: P2
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models.accommodation import ExternalProperty, Room
from app.models.events import EventSession
from app.models.inventory import InventoryItem
from app.models.participants import Participant
from app.models.staff import Shift
from app.models.vendors import Vendor
from app.services.assumptions.service import get_assumption

logger = logging.getLogger("festos.forecasting.engine")

FESTIVAL_START = datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
FESTIVAL_END = datetime(2026, 11, 1, 22, 0, tzinfo=timezone.utc)


def forecast_arrivals_and_queues(
    session: Session,
    desks_open: int = 6,
    service_rate_per_min: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Forecasts arrival volumes and simulates check-in queues using a discrete queue model.
    Strictly labels each series as PROJECTION (derived from data) or ASSUMPTION (parameter-driven).
    """
    # 1. Resolve service rate parameter (from assumption table or argument)
    if service_rate_per_min is None:
        try:
            assumed_rate = get_assumption(session, "checkin_service_rate_per_min")
            srv_rate = float(assumed_rate.value) if assumed_rate and assumed_rate.value else 0.5
        except Exception:
            srv_rate = 0.5
    else:
        srv_rate = float(service_rate_per_min)

    desks = max(1, desks_open)
    hourly_capacity = int(round(desks * srv_rate * 60.0))

    start = start_time or FESTIVAL_START
    end = end_time or FESTIVAL_END

    # 2. Group participants by arrival hour
    participants = session.exec(
        select(Participant).where(Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]))
    ).all()

    known_arrivals: Dict[str, int] = {}
    unknown_arrival_count = 0

    for p in participants:
        if p.arrival_at:
            arr_utc = p.arrival_at if p.arrival_at.tzinfo else p.arrival_at.replace(tzinfo=timezone.utc)
            bucket_key = arr_utc.replace(minute=0, second=0, microsecond=0).isoformat()
            known_arrivals[bucket_key] = known_arrivals.get(bucket_key, 0) + 1
        else:
            unknown_arrival_count += 1

    # 3. Simulate queue hour by hour
    timeline = []
    curr = start
    queue_length = 0
    max_queue = 0
    max_wait = 0.0
    peak_hour = start.isoformat()

    # Distribute unknown arrivals as an ASSUMPTION across daytime windows if any
    unknown_buffer_per_hour = int(unknown_arrival_count / max(1, 24)) if unknown_arrival_count > 0 else 0

    while curr <= end:
        bucket_iso = curr.isoformat()
        projected_arrivals = known_arrivals.get(bucket_iso, 0)
        assumed_arrivals = unknown_buffer_per_hour if (8 <= curr.hour <= 20) else 0
        total_arrivals = projected_arrivals + assumed_arrivals

        q_start = queue_length
        total_waiting = q_start + total_arrivals
        processed = min(total_waiting, hourly_capacity)
        q_end = total_waiting - processed
        wait_time = round((q_end / max(1, hourly_capacity)) * 60.0, 1) if q_end > 0 else 0.0

        if q_end > max_queue:
            max_queue = q_end
            max_wait = wait_time
            peak_hour = bucket_iso

        timeline.append({
            "timestamp": bucket_iso,
            "expected_arrivals": projected_arrivals,
            "arrivals_series_type": "PROJECTION",
            "unspecified_arrival_buffer": assumed_arrivals,
            "buffer_series_type": "ASSUMPTION",
            "queue_length_start": q_start,
            "processed_count": processed,
            "queue_length_end": q_end,
            "wait_time_minutes": wait_time,
            "queue_series_type": "ASSUMPTION",
        })

        queue_length = q_end
        curr += timedelta(hours=1)

    warnings = []
    if unknown_arrival_count > 0:
        warnings.append(
            f"{unknown_arrival_count} participants have UNKNOWN arrival times; assumed evenly buffered across 08:00-20:00 arrival windows."
        )

    return {
        "parameters": {
            "desks_open": desks,
            "service_rate_per_desk_per_min": srv_rate,
            "service_capacity_per_hour": hourly_capacity,
            "parameter_source": "ASSUMPTION",
        },
        "timeline": timeline,
        "peak_queue_hour": peak_hour,
        "max_queue_length": max_queue,
        "max_wait_time_minutes": max_wait,
        "meta": {
            "arrival_data_points": len(participants) - unknown_arrival_count,
            "unspecified_arrival_count": unknown_arrival_count,
        },
        "warnings": warnings,
    }


def forecast_demand_timeline(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Consolidated hourly multi-domain demand forecast for meals, accommodation, merchandise, equipment, volunteers.
    Labels every single series PROJECTION or ASSUMPTION.
    """
    start = start_time or FESTIVAL_START
    end = end_time or FESTIVAL_END

    participants = session.exec(
        select(Participant).where(Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]))
    ).all()
    rooms = session.exec(select(Room)).all()
    properties = session.exec(select(ExternalProperty)).all()
    total_beds = sum(r.capacity for r in rooms if r.status in ["READY", "OCCUPIED", "AVAILABLE"]) + sum(p.beds for p in properties if p.status == "ACTIVE")

    # Merchandise Breakdown
    tshirt_counts = Counter(
        str(p.tshirt_size or "UNKNOWN").upper().strip() for p in participants
    )
    merch_summary = {
        "tshirt_size_breakdown": {
            "S": {"demand": tshirt_counts.get("S", 0), "stock": 250, "series_type": "PROJECTION"},
            "M": {"demand": tshirt_counts.get("M", 0), "stock": 600, "series_type": "PROJECTION"},
            "L": {"demand": tshirt_counts.get("L", 0), "stock": 450, "series_type": "PROJECTION"},
            "XL": {"demand": tshirt_counts.get("XL", 0), "stock": 250, "series_type": "PROJECTION"},
            "UNKNOWN": {
                "demand": tshirt_counts.get("UNKNOWN", 0) + tshirt_counts.get("NONE", 0),
                "buffer_policy": "ALLOCATE_M_L",
                "series_type": "ASSUMPTION",
            },
        }
    }

    timeline = []
    curr = start
    while curr <= end:
        # 1. Meals
        is_meal = curr.hour in [8, 9, 13, 14, 20, 21]
        active_parts = [
            p for p in participants
            if (not p.arrival_at or p.arrival_at <= curr) and (not p.departure_at or p.departure_at >= curr)
        ]
        active_count = len(active_parts)

        veg_count = sum(1 for p in active_parts if "VEG" in str(p.diet or "").upper() and "NON" not in str(p.diet or "").upper())
        nonveg_count = sum(1 for p in active_parts if "NON" in str(p.diet or "").upper())
        jain_count = sum(1 for p in active_parts if "JAIN" in str(p.diet or "").upper())
        unknown_diet = sum(1 for p in active_parts if str(p.diet or "UNKNOWN").upper() in ["UNKNOWN", "NONE", "NULL", "UNSPECIFIED"])

        meals_data = {
            "total_demand": active_count if is_meal else int(active_count * 0.15),
            "confirmed_veg": veg_count if is_meal else int(veg_count * 0.15),
            "confirmed_nonveg": nonveg_count if is_meal else int(nonveg_count * 0.15),
            "confirmed_jain": jain_count if is_meal else int(jain_count * 0.15),
            "unconfirmed_buffer": unknown_diet if is_meal else int(unknown_diet * 0.15),
            "series_type": "PROJECTION",
            "buffer_series_type": "ASSUMPTION",
        }

        # 2. Accommodation
        confirmed_beds = sum(
            1 for p in active_parts if str(p.accommodation_requested or "").upper() == "YES"
        )
        possible_beds = sum(
            1 for p in active_parts if str(p.accommodation_requested or "UNKNOWN").upper() == "UNKNOWN"
        )
        acc_data = {
            "confirmed_beds_demanded": confirmed_beds,
            "possible_beds_demanded": possible_beds,
            "total_beds_available": total_beds,
            "deficit": max(0, (confirmed_beds + possible_beds) - total_beds),
            "confirmed_series_type": "PROJECTION",
            "possible_series_type": "ASSUMPTION",
        }

        # 3. Equipment & Volunteers
        sessions = session.exec(
            select(EventSession).where(EventSession.status.in_(["SCHEDULED", "CONFIRMED", "ACTIVE", "IN_PROGRESS"]))
        ).all()
        active_ses = [
            s for s in sessions
            if s.start_at and s.end_at and s.start_at <= curr <= s.end_at
        ]
        eq_data = {
            "active_scheduled_events": len(active_ses),
            "units_demanded": len(active_ses) * 6,
            "series_type": "PROJECTION",
        }

        shifts = session.exec(select(Shift)).all()
        filled_shifts = len([
            s for s in shifts
            if getattr(s, "status", "SCHEDULED") in ["SCHEDULED", "CONFIRMED", "ACTIVE"]
        ])
        vol_req = max(len(active_ses) * 4, 10 if (8 <= curr.hour <= 22) else 4)
        vol_data = {
            "volunteers_required": vol_req,
            "volunteers_scheduled": filled_shifts,
            "gap": max(0, vol_req - filled_shifts),
            "series_type": "PROJECTION",
        }

        timeline.append({
            "timestamp": curr.isoformat(),
            "meals": meals_data,
            "accommodation": acc_data,
            "equipment": eq_data,
            "volunteers": vol_data,
        })

        curr += timedelta(hours=1)

    return {
        "timeline": timeline,
        "merchandise_summary": merch_summary,
        "meta": {
            "total_hours": len(timeline),
            "data_provenance": "PROJECTION derived strictly from DB records; ASSUMPTION parameter-driven buffers.",
        },
    }
