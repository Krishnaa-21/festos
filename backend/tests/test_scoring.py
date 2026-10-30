# OWNER: P1
from app.core.scoring import (
    bucket_risks_for_heatmap,
    calculate_attention_score,
    heatmap_bucket,
    urgency_bucket_label,
    urgency_from_hours,
)
from app.schemas.common import RiskItem, Severity


def test_urgency_multipliers():
    assert urgency_from_hours(0.5) == 5    # <= 1h
    assert urgency_from_hours(1.0) == 5
    assert urgency_from_hours(2.5) == 4    # <= 4h
    assert urgency_from_hours(4.0) == 4
    assert urgency_from_hours(8.0) == 3    # <= 12h
    assert urgency_from_hours(12.0) == 3
    assert urgency_from_hours(20.0) == 2   # <= 24h
    assert urgency_from_hours(24.0) == 2
    assert urgency_from_hours(30.0) == 1   # > 24h
    assert urgency_from_hours(None) == 1

def test_urgency_bucket_labels():
    assert urgency_bucket_label(0.5) == "IMMEDIATE"
    assert urgency_bucket_label(3.0) == "HIGH_PRIORITY"
    assert urgency_bucket_label(10.0) == "ELEVATED"
    assert urgency_bucket_label(18.0) == "UPCOMING"
    assert urgency_bucket_label(48.0) == "MONITOR"

def test_attention_score_calculation():
    # Severity 4 (CRITICAL) x Urgency 5 (<=1h) x max(50 people, 1) = 4 x 5 x 50 = 1000
    score = calculate_attention_score(Severity.CRITICAL, hours_to_impact=0.5, people_affected=50)
    assert score == 1000.0

    # Severity 2 x Urgency 1 (>24h) x 0 people (clamps to 1) = 2 x 1 x 1 = 2
    score_low = calculate_attention_score(Severity.MEDIUM, hours_to_impact=48.0, people_affected=0)
    assert score_low == 2.0

def test_heatmap_bucket_and_grouping():
    info = heatmap_bucket(Severity.CRITICAL, hours_to_impact=1.0)
    assert info["severity"] == 4
    assert info["urgency"] == 5
    assert info["grid_key"] == "sev_4_urg_5"
    assert info["is_critical_quadrant"] is True

    # Test grouping helper
    r1 = RiskItem(
        id="risk_1",
        module="accommodation",
        kind="OVERFLOW",
        title="Bed shortfall",
        severity=Severity.CRITICAL,
        hours_to_impact=1.0,
        people_affected=10
    )
    r2 = RiskItem(
        id="risk_2",
        module="catering",
        kind="DELAY",
        title="Dinner delayed",
        severity=Severity.LOW,
        hours_to_impact=30.0,
        people_affected=5
    )
    grouped = bucket_risks_for_heatmap([r1, r2])
    assert "sev_4_urg_5" in grouped
    assert len(grouped["sev_4_urg_5"]) == 1
    assert "sev_1_urg_1" in grouped
