# OWNER: P2
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from sqlmodel import Session

from app.core.clock import now
from app.engines.forecasting.engine import (
    forecast_arrivals_and_queues,
    forecast_demand_timeline,
)


def generate_forecasting_report(
    session: Session,
    report_name: str,
    output_format: str = "json",
) -> Dict[str, Any] | str:
    """Generates structured analytical reports (JSON or CSV) for festival forecasting outputs."""
    norm_name = report_name.lower().strip()

    if norm_name in ["arrivals_queue", "arrivals", "queue"]:
        data = forecast_arrivals_and_queues(session)
        timeline = data["timeline"]

        if output_format.lower() == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow([
                "Timestamp",
                "Expected Arrivals",
                "Arrivals Series Type",
                "Queue Start",
                "Processed Count",
                "Queue End",
                "Wait Time (Minutes)",
                "Queue Series Type",
            ])
            for row in timeline:
                writer.writerow([
                    row["timestamp"],
                    row["expected_arrivals"],
                    row["arrivals_series_type"],
                    row["queue_length_start"],
                    row["processed_count"],
                    row["queue_length_end"],
                    row["wait_time_minutes"],
                    row["queue_series_type"],
                ])
            return out.getvalue()

        return {
            "report_name": "arrivals_queue",
            "generated_at": now().isoformat(),
            "summary": f"Peak queue of {data['max_queue_length']} attendees at {data['peak_queue_hour']} (max wait: {data['max_wait_time_minutes']} min)",
            "records_count": len(timeline),
            "rows": timeline,
            "meta": data["meta"],
        }

    elif norm_name in ["meal_demand", "meals", "food"]:
        data = forecast_demand_timeline(session)
        timeline = data["timeline"]

        if output_format.lower() == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow([
                "Timestamp",
                "Total Demand",
                "Confirmed Veg",
                "Confirmed NonVeg",
                "Confirmed Jain",
                "Unconfirmed Buffer",
                "Buffer Series Type",
            ])
            for row in timeline:
                m = row["meals"]
                writer.writerow([
                    row["timestamp"],
                    m["total_demand"],
                    m["confirmed_veg"],
                    m["confirmed_nonveg"],
                    m["confirmed_jain"],
                    m["unconfirmed_buffer"],
                    m["buffer_series_type"],
                ])
            return out.getvalue()

        rows = [{"timestamp": r["timestamp"], **r["meals"]} for r in timeline]
        return {
            "report_name": "meal_demand",
            "generated_at": now().isoformat(),
            "summary": "Hourly meal catering projection across confirmed diets and unconfirmed buffers",
            "records_count": len(rows),
            "rows": rows,
        }

    elif norm_name in ["accommodation_capacity", "accommodation", "beds"]:
        data = forecast_demand_timeline(session)
        timeline = data["timeline"]

        if output_format.lower() == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow([
                "Timestamp",
                "Confirmed Beds Demanded",
                "Possible Beds Demanded",
                "Total Beds Available",
                "Deficit",
            ])
            for row in timeline:
                a = row["accommodation"]
                writer.writerow([
                    row["timestamp"],
                    a["confirmed_beds_demanded"],
                    a["possible_beds_demanded"],
                    a["total_beds_available"],
                    a["deficit"],
                ])
            return out.getvalue()

        rows = [{"timestamp": r["timestamp"], **r["accommodation"]} for r in timeline]
        return {
            "report_name": "accommodation_capacity",
            "generated_at": now().isoformat(),
            "summary": "Hourly bed demand timeline comparing confirmed vs possible demand against capacity",
            "records_count": len(rows),
            "rows": rows,
        }

    elif norm_name in ["volunteer_gap", "volunteers", "staff"]:
        data = forecast_demand_timeline(session)
        timeline = data["timeline"]

        if output_format.lower() == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow([
                "Timestamp",
                "Volunteers Required",
                "Volunteers Scheduled",
                "Coverage Gap",
                "Series Type",
            ])
            for row in timeline:
                v = row["volunteers"]
                writer.writerow([
                    row["timestamp"],
                    v["volunteers_required"],
                    v["volunteers_scheduled"],
                    v["gap"],
                    v["series_type"],
                ])
            return out.getvalue()

        rows = [{"timestamp": r["timestamp"], **r["volunteers"]} for r in timeline]
        return {
            "report_name": "volunteer_gap",
            "generated_at": now().isoformat(),
            "summary": "Volunteer shift requirement vs scheduled coverage across event hours",
            "records_count": len(rows),
            "rows": rows,
        }

    elif norm_name in ["merchandise_projection", "merchandise", "merch"]:
        data = forecast_demand_timeline(session)
        sizes = data["merchandise_summary"]["tshirt_size_breakdown"]

        if output_format.lower() == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["Size", "Demand", "Stock / Policy", "Series Type"])
            for sz, info in sizes.items():
                writer.writerow([
                    sz,
                    info.get("demand", 0),
                    info.get("stock", info.get("buffer_policy", "N/A")),
                    info.get("series_type", "PROJECTION"),
                ])
            return out.getvalue()

        return {
            "report_name": "merchandise_projection",
            "generated_at": now().isoformat(),
            "summary": "T-shirt inventory sizing projections by confirmed and unconfirmed distribution",
            "breakdown": sizes,
        }

    else:
        raise ValueError(
            f"Unknown report name '{report_name}'. Valid options: arrivals_queue, meal_demand, accommodation_capacity, volunteer_gap, merchandise_projection."
        )
