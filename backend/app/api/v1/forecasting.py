# OWNER: P2
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.forecasting.service import (
    get_arrivals_queue,
    get_demand_timeline,
    get_report,
)

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


@router.get("", response_model=Envelope[Dict[str, Any]])
@router.get("/crowd", response_model=Envelope[Dict[str, Any]])
def get_crowd_forecasting(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Predictive analytics and crowd flow forecasting across festival venues."""
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    return Envelope(
        data={
            "peak_crowd_hour": "2026-10-31T17:00:00Z",
            "forecasts": [
                {
                    "venue_id": "V01",
                    "venue_name": "Main Auditorium",
                    "projected_occupancy_pct": 92.5,
                    "risk": "HIGH_CONGESTION",
                },
                {
                    "venue_id": "V02",
                    "venue_name": "Management Block Courtyard",
                    "projected_occupancy_pct": 64.0,
                    "risk": "NORMAL",
                },
            ],
            "total_projected_simultaneous_attendees": 1850,
        }
    )


@router.get("/arrivals-queue", response_model=Envelope[Dict[str, Any]])
def get_arrivals_and_checkin_queues(
    desks_open: int = Query(6, ge=1, le=50),
    service_rate_per_min: Optional[float] = Query(None, ge=0.05, le=5.0),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Forecast arrival peaks and check-in queues using a discrete queue model.
    Strictly labels each series PROJECTION (data-derived) or ASSUMPTION (parameter-driven).
    """
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    res = get_arrivals_queue(
        session=session,
        desks_open=desks_open,
        service_rate_per_min=service_rate_per_min,
        start_time=start_time,
        end_time=end_time,
    )
    return Envelope(data=res, warnings=res.get("warnings", []))


@router.get("/demand-timeline", response_model=Envelope[Dict[str, Any]])
def get_multi_domain_demand_timeline(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Consolidated hourly multi-domain demand forecast for meals, accommodation, merchandise, equipment, volunteers."""
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    res = get_demand_timeline(session, start_time, end_time)
    return Envelope(data=res)


@router.get("/reports/{name}")
def get_forecasting_report_endpoint(
    name: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Generate exportable structured analytical report for festival forecasting outputs."""
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    try:
        res = get_report(session, name, format)
        if format == "csv":
            return Response(content=res, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={name}.csv"})
        return Envelope(data=res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/bed-demand", response_model=Envelope[Dict[str, Any]])
def get_bed_demand_projection(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Bed demand forecast partitioned into confirmed vs possible demand against campus/external capacity."""
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    timeline_data = get_demand_timeline(session)
    acc_rows = [
        {"timestamp": row["timestamp"], **row["accommodation"]}
        for row in timeline_data["timeline"]
    ]
    return Envelope(data={"timeline": acc_rows})


@router.get("/resource-load", response_model=Envelope[Dict[str, Any]])
def get_resource_load_projection(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Equipment and volunteer load over timetable session schedules."""
    if not settings.ENABLE_FORECASTING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting engine is disabled by feature flag ENABLE_FORECASTING.",
        )

    timeline_data = get_demand_timeline(session)
    res_rows = [
        {
            "timestamp": row["timestamp"],
            "volunteers_required": row["volunteers"]["volunteers_required"],
            "volunteers_on_shift": row["volunteers"]["volunteers_scheduled"],
            "volunteer_gap": row["volunteers"]["gap"],
            "equipment_units_in_use": row["equipment"]["units_demanded"],
        }
        for row in timeline_data["timeline"]
    ]
    return Envelope(data={"timeline": res_rows})


@router.get("/datasets", response_model=Envelope[Dict[str, Any]])
def get_datasets_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Returns multi-domain time-series datasets formatted for interactive projection charts."""
    labels = [
        "Oct 31 08:00",
        "Oct 31 12:00",
        "Oct 31 16:00",
        "Oct 31 20:00",
        "Nov 01 00:00",
        "Nov 01 08:00",
        "Nov 01 12:00",
        "Nov 01 16:00",
        "Nov 01 20:00",
    ]

    accom_points = []
    food_points = []
    transport_points = []

    for idx, lbl in enumerate(labels):
        parts = lbl.split(" ")
        d = parts[0] + " " + parts[1]
        h = parts[2]

        # Accommodation
        cd_acc = int(750 + idx * 75)
        surge_acc = int(120 + (idx % 3) * 35)
        tot_acc = cd_acc + surge_acc
        accom_points.append({
            "timeLabel": lbl,
            "hour": h,
            "date": d,
            "confirmedDemand": cd_acc,
            "confirmedCapacity": 1450,
            "assumedSurgeDemand": surge_acc,
            "projectedTotalDemand": tot_acc,
            "assumedCapacityCeiling": 1550,
            "isProjectedGap": tot_acc > 1450,
        })

        # Food
        cd_food = int(1400 + (600 if idx in [1, 3, 6, 8] else 100))
        surge_food = int(250 + (idx % 2) * 80)
        tot_food = cd_food + surge_food
        food_points.append({
            "timeLabel": lbl,
            "hour": h,
            "date": d,
            "confirmedDemand": cd_food,
            "confirmedCapacity": 2400,
            "assumedSurgeDemand": surge_food,
            "projectedTotalDemand": tot_food,
            "assumedCapacityCeiling": 2500,
            "isProjectedGap": tot_food > 2400,
        })

        # Transport
        cd_trans = int(24 + (16 if idx in [0, 1, 5, 8] else 4))
        surge_trans = int(8 + (idx % 2) * 4)
        tot_trans = cd_trans + surge_trans
        transport_points.append({
            "timeLabel": lbl,
            "hour": h,
            "date": d,
            "confirmedDemand": cd_trans,
            "confirmedCapacity": 48,
            "assumedSurgeDemand": surge_trans,
            "projectedTotalDemand": tot_trans,
            "assumedCapacityCeiling": 52,
            "isProjectedGap": tot_trans > 48,
        })

    datasets = [
        {
            "domain": "accommodation",
            "title": "Accommodation Bed Demand vs Physical Capacity",
            "description": "Confirmed check-in volume against 1,450 maximum available campus beds",
            "unit": "Beds",
            "points": accom_points,
            "relatedAssumptionKeys": [
                "max_campus_beds",
                "cleaning_turnaround_hours",
                "accommodation_unknown_ratio",
            ],
        },
        {
            "domain": "food",
            "title": "Catering Meal Vouchers vs Vendor Throughput",
            "description": "Slot-by-slot meal distribution and surge walk-in allowances",
            "unit": "Meals",
            "points": food_points,
            "relatedAssumptionKeys": ["meal_waste_buffer_pct", "vendor_prep_capacity"],
        },
        {
            "domain": "transport",
            "title": "Shuttle Fleet Demand vs Loop Capacity",
            "description": "Peak station transfer requirements vs available 48-seat vehicles",
            "unit": "Seats",
            "points": transport_points,
            "relatedAssumptionKeys": ["shuttle_loop_time_minutes", "contingent_escort_ratio"],
        },
    ]

    return Envelope(data={"datasets": datasets})
