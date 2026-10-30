# OWNER: P2
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.engines.vendors.compliance import (
    hours_cover_slot,
    is_certificate_valid_at,
    parse_expiry_date,
)

ALL_DIETARY_CATEGORIES = [
    "vegetarian",
    "non-vegetarian",
    "vegan",
    "jain",
    "halal",
    "gluten-free",
    "nut-allergy",
    "other",
    "unknown",
]


def normalize_dietary_category(raw_diet: Optional[str]) -> str:
    """Normalize raw dietary string into one of the 8 canonical categories or unknown."""
    if not raw_diet or not str(raw_diet).strip():
        return "unknown"

    val = str(raw_diet).lower().strip()
    if val in ["none", "n/a", "null", "unknown", "unspecified"]:
        return "unknown"
    if "non" in val and "veg" in val:
        return "non-vegetarian"
    if "vegan" in val:
        return "vegan"
    if "jain" in val:
        return "jain"
    if "halal" in val:
        return "halal"
    if "gluten" in val:
        return "gluten-free"
    if "nut" in val:
        return "nut-allergy"
    if "veg" in val:
        return "vegetarian"

    return "other"


def extract_vendor_categories(dietary_options_str: Optional[str]) -> Set[str]:
    """Parse a vendor's dietary_options string into normalized categories."""
    if not dietary_options_str:
        return set()
    raw_tokens = re.split(r"[;,/]+", str(dietary_options_str).lower().strip())
    categories: Set[str] = set()
    for tok in raw_tokens:
        norm = normalize_dietary_category(tok)
        if norm != "unknown":
            categories.add(norm)
    return categories


def is_participant_on_site(
    arrival_at: Optional[datetime],
    departure_at: Optional[datetime],
    status: Optional[str],
    slot_dt: datetime,
) -> bool:
    """Check if participant is physically on site during a given meal timestamp."""
    if status in ["CANCELLED", "NO_SHOW", "WITHDRAWN", "INVALID"]:
        return False

    if arrival_at and departure_at:
        # Normalize timezones to UTC
        arr = arrival_at if arrival_at.tzinfo else arrival_at.replace(tzinfo=timezone.utc)
        dep = departure_at if departure_at.tzinfo else departure_at.replace(tzinfo=timezone.utc)
        sdt = slot_dt if slot_dt.tzinfo else slot_dt.replace(tzinfo=timezone.utc)
        return arr <= sdt <= dep

    # If times missing, rely on active status
    return status in ["EXPECTED", "ARRIVED", "CHECKED_IN"]


def evaluate_dietary_matrix(
    participants: List[Any],
    vendors: List[Any],
    meal_slots: List[Any],
    assignments: List[Any],
    target_date: date,
) -> Dict[str, Any]:
    """Evaluate 3D dietary coverage matrix (category x meal_slot x venue).

    - Demand is derived from participant on-site headcount.
    - UNKNOWN dietary stays separate and is presented as a demand range, never assumed vegetarian.
    - Certificate expiry drops capacity from the expiry moment.
    - Categories with zero compliant vendors trigger critical alerts.
    """
    matrix: List[Dict[str, Any]] = []
    zero_coverage_set: Set[str] = set()
    max_headcount_on_site = 0
    total_valid_throughout_capacity = 0

    # Index assignments by (vendor_id, meal_slot_id)
    assign_map: Dict[Tuple[str, str], Any] = {}
    for a in assignments:
        assign_map[(a.vendor_id, a.meal_slot_id)] = a

    # Date slots
    date_str = target_date.isoformat()
    slots_for_date = [s for s in meal_slots if s.date == date_str]

    if not slots_for_date and meal_slots:
        # Fallback to all slots if specific date has none
        slots_for_date = meal_slots

    for slot in slots_for_date:
        # Approximate mid-slot datetime
        s_parts = slot.start_time.split(":")
        slot_dt = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            int(s_parts[0]),
            int(s_parts[1]),
            tzinfo=timezone.utc,
        )

        # 1. Compute participant headcount and demand breakdown
        on_site_parts = [p for p in participants if is_participant_on_site(p.arrival_at, p.departure_at, p.status, slot_dt)]
        slot_headcount = len(on_site_parts)
        if slot_headcount > max_headcount_on_site:
            max_headcount_on_site = slot_headcount

        cat_counts: Dict[str, int] = {cat: 0 for cat in ALL_DIETARY_CATEGORIES}
        for p in on_site_parts:
            diet_raw = getattr(p, "diet", None) or getattr(p, "dietary_needs", None)
            diet = normalize_dietary_category(diet_raw)
            cat_counts[diet] = cat_counts.get(diet, 0) + 1

        unknown_count = cat_counts.get("unknown", 0)

        # 2. Compute valid vendor capacity in this slot
        # A vendor is valid if ACTIVE and certificate valid on target_date and hours cover slot
        valid_vendors: List[Any] = []
        for v in vendors:
            if getattr(v, "status", "ACTIVE") != "ACTIVE":
                continue
            exp_date = parse_expiry_date(getattr(v, "hygiene_certificate_expiry", None))
            if not is_certificate_valid_at(exp_date, target_date):
                continue
            if not hours_cover_slot(getattr(v, "hours", None), slot.start_time, slot.end_time):
                continue
            valid_vendors.append(v)

        # 3. Build matrix row per dietary category
        for cat in ALL_DIETARY_CATEGORIES:
            if cat == "unknown":
                continue

            demand_conf = cat_counts.get(cat, 0)
            demand_max = demand_conf + unknown_count

            # Find vendors serving this category
            serving_vendors = [v for v in valid_vendors if cat in extract_vendor_categories(getattr(v, "dietary_options", ""))]
            cat_capacity = sum(getattr(v, "capacity", 0) or 0 for v in serving_vendors)

            deficit = max(0, demand_conf - cat_capacity)
            is_zero = (cat_capacity == 0 and demand_conf > 0)
            if is_zero:
                zero_coverage_set.add(cat)

            row = {
                "meal_slot": slot.name,
                "meal_slot_id": slot.id,
                "date": date_str,
                "category": cat,
                "demand_confirmed": demand_conf,
                "demand_max_with_unknown": demand_max,
                "valid_capacity": cat_capacity,
                "deficit": deficit,
                "is_zero_coverage": is_zero,
                "active_vendors": [v.id for v in serving_vendors],
            }
            matrix.append(row)

    # Calculate aggregate capacity of all vendors valid throughout festival
    valid_throughout_vendors = [
        v for v in vendors
        if getattr(v, "status", "ACTIVE") == "ACTIVE"
        and is_certificate_valid_at(parse_expiry_date(getattr(v, "hygiene_certificate_expiry", None)), date(2026, 11, 2))
    ]
    total_valid_throughout_capacity = sum(getattr(v, "capacity", 0) or 0 for v in valid_throughout_vendors)

    # Shortfall against peak headcount
    aggregate_shortfall = max(0, max_headcount_on_site - total_valid_throughout_capacity)

    critical_alerts: List[Dict[str, Any]] = []
    for z_cat in sorted(zero_coverage_set):
        critical_alerts.append({
            "code": "ZERO_COMPLIANT_VENDORS",
            "category": z_cat,
            "severity": "CRITICAL",
            "message": f"Zero compliant vendors available for '{z_cat}' dietary requirements.",
        })

    summary = {
        "on_site_headcount": max_headcount_on_site,
        "valid_aggregate_capacity": total_valid_throughout_capacity,
        "aggregate_shortfall": aggregate_shortfall,
        "zero_coverage_categories": sorted(list(zero_coverage_set)),
        "unknown_dietary_headcount": sum(
            1 for p in participants
            if normalize_dietary_category(getattr(p, "diet", None) or getattr(p, "dietary_needs", None)) == "unknown"
        ),
    }

    return {
        "date": date_str,
        "categories": ALL_DIETARY_CATEGORIES,
        "meal_slots": [s.name for s in slots_for_date],
        "summary": summary,
        "matrix": matrix,
        "critical_alerts": critical_alerts,
    }
