# OWNER: P1
from typing import Any, Dict, List, Optional, Union

from app.schemas.common import Severity


def urgency_from_hours(hours_to_impact: Optional[float]) -> int:
    """Urgency multiplier based on hours to impact:
    <= 1h: 5
    <= 4h: 4
    <= 12h: 3
    <= 24h: 2
    otherwise or None: 1
    """
    if hours_to_impact is None or hours_to_impact < 0:
        return 1
    if hours_to_impact <= 1.0:
        return 5
    if hours_to_impact <= 4.0:
        return 4
    if hours_to_impact <= 12.0:
        return 3
    if hours_to_impact <= 24.0:
        return 2
    return 1

def urgency_bucket_label(hours_to_impact: Optional[float]) -> str:
    """Human-readable urgency bucket label."""
    urgency = urgency_from_hours(hours_to_impact)
    if urgency == 5:
        return "IMMEDIATE"       # <= 1h
    if urgency == 4:
        return "HIGH_PRIORITY"   # <= 4h
    if urgency == 3:
        return "ELEVATED"        # <= 12h
    if urgency == 2:
        return "UPCOMING"        # <= 24h
    return "MONITOR"             # > 24h or None

def calculate_attention_score(
    severity: Union[int, Severity],
    hours_to_impact: Optional[float],
    people_affected: int = 0
) -> float:
    """Attention score = Severity (1-4) x Urgency x max(people_affected, 1)."""
    sev_val = severity.value if isinstance(severity, Severity) else int(severity)
    sev_val = max(1, min(4, sev_val))
    urgency_val = urgency_from_hours(hours_to_impact)
    impact_val = max(int(people_affected), 1)
    return float(sev_val * urgency_val * impact_val)

def heatmap_bucket(
    severity: Union[int, Severity],
    hours_to_impact: Optional[float]
) -> Dict[str, Any]:
    """Helper to categorize risk into a 4x5 Severity x Urgency heatmap matrix."""
    sev_val = severity.value if isinstance(severity, Severity) else int(severity)
    sev_val = max(1, min(4, sev_val))
    urgency_val = urgency_from_hours(hours_to_impact)

    # Grid coordinate (0-indexed: row = 4 - severity, col = 5 - urgency)
    return {
        "severity": sev_val,
        "urgency": urgency_val,
        "grid_key": f"sev_{sev_val}_urg_{urgency_val}",
        "urgency_label": urgency_bucket_label(hours_to_impact),
        "is_critical_quadrant": (sev_val >= 3 and urgency_val >= 4)
    }

def bucket_risks_for_heatmap(risks: List[Any]) -> Dict[str, List[Any]]:
    """Group items by heatmap grid key."""
    buckets: Dict[str, List[Any]] = {}
    for r in risks:
        sev = getattr(r, "severity", 1)
        hours = getattr(r, "hours_to_impact", None)
        info = heatmap_bucket(sev, hours)
        key = info["grid_key"]
        buckets.setdefault(key, []).append(r)
    return buckets
