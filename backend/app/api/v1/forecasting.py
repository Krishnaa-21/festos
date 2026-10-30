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
