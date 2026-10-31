# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.engines.forecasting.engine import (
    forecast_arrivals_and_queues,
    forecast_demand_timeline,
)
from app.services.forecasting.reports import generate_forecasting_report


def get_arrivals_queue(
    session: Session,
    desks_open: int = 6,
    service_rate_per_min: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Retrieves check-in queue forecast with editable service rate and series provenance tags."""
    return forecast_arrivals_and_queues(
        session=session,
        desks_open=desks_open,
        service_rate_per_min=service_rate_per_min,
        start_time=start_time,
        end_time=end_time,
    )


def get_demand_timeline(
    session: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Retrieves consolidated demand forecast for meals, accommodation, merchandise, equipment, volunteers."""
    return forecast_demand_timeline(session, start_time, end_time)


def get_report(
    session: Session,
    report_name: str,
    output_format: str = "json",
) -> Dict[str, Any] | str:
    """Generates structured forecasting reports in JSON or CSV format."""
    return generate_forecasting_report(session, report_name, output_format)
