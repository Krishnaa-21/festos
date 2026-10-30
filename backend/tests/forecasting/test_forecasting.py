# OWNER: P2
from datetime import datetime, timezone
import pytest
from sqlmodel import Session

from app.engines.forecasting.engine import (
    forecast_arrivals_and_queues,
    forecast_demand_timeline,
)
from app.models.accommodation import Room
from app.models.events import EventSession
from app.models.participants import Participant
from app.services.forecasting.public import risks as forecasting_risks, summary as forecasting_summary
from app.services.forecasting.reports import generate_forecasting_report


def test_arrivals_queue_model_with_editable_service_rate(session: Session):
    """Arrivals queue model simulates arrivals, wait times, and queue lengths based on editable service rate."""
    # Seed participants with known arrival times
    base_dt = datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)
    for i in range(120):
        p = Participant(
            id=f"p_arr_{i:03d}",
            name=f"Participant {i}",
            arrival_at=base_dt,
            departure_at=datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc),
            status="EXPECTED",
        )
        session.add(p)
    session.commit()

    # 1. Run with 4 desks, service rate 0.5 (30 per desk/hr = 120 capacity/hr)
    res_120_cap = forecast_arrivals_and_queues(
        session,
        desks_open=4,
        service_rate_per_min=0.5,
        start_time=base_dt,
        end_time=base_dt,
    )
    hour_interval = res_120_cap["timeline"][0]
    assert hour_interval["expected_arrivals"] == 120
    assert hour_interval["processed_count"] == 120
    assert hour_interval["queue_length_end"] == 0
    assert hour_interval["wait_time_minutes"] == 0.0

    # 2. Run with constrained capacity (2 desks, 0.5 rate = 60 capacity/hr)
    res_60_cap = forecast_arrivals_and_queues(
        session,
        desks_open=2,
        service_rate_per_min=0.5,
        start_time=base_dt,
        end_time=base_dt,
    )
    hour_interval_60 = res_60_cap["timeline"][0]
    assert hour_interval_60["expected_arrivals"] == 120
    assert hour_interval_60["processed_count"] == 60
    assert hour_interval_60["queue_length_end"] == 60
    assert hour_interval_60["wait_time_minutes"] > 0.0


def test_series_provenance_tagging_projection_vs_assumption(session: Session):
    """Every series in arrivals and demand forecasts carries an explicit PROJECTION or ASSUMPTION label."""
    p1 = Participant(
        id="p_tag_01",
        name="Tag User",
        arrival_at=datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc),
        tshirt_size="M",
        diet="Jain",
        accommodation_requested="YES",
        status="EXPECTED",
    )
    p2 = Participant(
        id="p_tag_02",
        name="Untag User",
        arrival_at=None,
        tshirt_size=None,
        diet="UNKNOWN",
        accommodation_requested="UNKNOWN",
        status="EXPECTED",
    )
    session.add_all([p1, p2])
    session.commit()

    # Arrivals Queue
    q_data = forecast_arrivals_and_queues(session)
    assert q_data["parameters"]["parameter_source"] == "ASSUMPTION"
    for row in q_data["timeline"]:
        assert row["arrivals_series_type"] == "PROJECTION"
        assert row["queue_series_type"] == "ASSUMPTION"
        assert row["buffer_series_type"] == "ASSUMPTION"

    # Demand Timeline
    d_data = forecast_demand_timeline(session)
    for row in d_data["timeline"]:
        assert row["meals"]["series_type"] == "PROJECTION"
        assert row["meals"]["buffer_series_type"] == "ASSUMPTION"
        assert row["accommodation"]["confirmed_series_type"] == "PROJECTION"
        assert row["accommodation"]["possible_series_type"] == "ASSUMPTION"
        assert row["equipment"]["series_type"] == "PROJECTION"
        assert row["volunteers"]["series_type"] == "PROJECTION"

    # Merchandise Breakdown
    merch = d_data["merchandise_summary"]["tshirt_size_breakdown"]
    assert merch["M"]["series_type"] == "PROJECTION"
    assert merch["UNKNOWN"]["series_type"] == "ASSUMPTION"


def test_forecasting_reports_json_and_csv(session: Session):
    """Forecasting report functions correctly export structured CSV and JSON outputs."""
    p = Participant(
        id="p_rep_01",
        name="Report User",
        arrival_at=datetime(2026, 10, 29, 11, 0, tzinfo=timezone.utc),
        diet="Vegetarian",
        status="EXPECTED",
    )
    session.add(p)
    session.commit()

    # JSON report
    rep_json = generate_forecasting_report(session, "arrivals_queue", output_format="json")
    assert isinstance(rep_json, dict)
    assert rep_json["report_name"] == "arrivals_queue"
    assert "summary" in rep_json
    assert len(rep_json["rows"]) > 0

    # CSV report
    rep_csv = generate_forecasting_report(session, "arrivals_queue", output_format="csv")
    assert isinstance(rep_csv, str)
    assert "Timestamp,Expected Arrivals" in rep_csv
    assert "PROJECTION" in rep_csv
    assert "ASSUMPTION" in rep_csv

    # Meal report
    rep_meals_csv = generate_forecasting_report(session, "meal_demand", output_format="csv")
    assert "Total Demand,Confirmed Veg" in rep_meals_csv


def test_forecasting_public_risks_reports_data_gaps(session: Session):
    """Forecasting public.py risks function surfaces data gaps blocking accurate forecasts."""
    p_gap = Participant(
        id="p_gap_01",
        name="Gap User",
        arrival_at=None,
        diet="UNKNOWN",
        status="EXPECTED",
    )
    session.add(p_gap)
    session.commit()

    risks_list = forecasting_risks(session, datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc))
    gap_ids = [r.id for r in risks_list]
    assert "risk_fc_arr_gap" in gap_ids

    summ = forecasting_summary(session, datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc))
    assert "unspecified_arrivals" in summ["data_gaps"]
    assert summ["data_gaps"]["unspecified_arrivals"] >= 1
