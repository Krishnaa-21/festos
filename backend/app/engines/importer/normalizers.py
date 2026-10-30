# OWNER: P2
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


def normalize_gender(val: Optional[str]) -> str:
    """Normalize gender strings to canonical variants.
    UNKNOWN is a first-class value. A blank never means a gender or NO.
    """
    if val is None:
        return "UNKNOWN"
    s = str(val).strip()
    if not s or s.lower() in ("unknown", "null", "none", "nan", ""):
        return "UNKNOWN"

    s_lower = s.lower()
    if s_lower in ("female", "f", "woman", "girl"):
        return "Female"
    elif s_lower in ("male", "m", "man", "boy"):
        return "Male"
    elif s_lower in ("non-binary", "nonbinary", "nb", "other"):
        return "Non-binary"
    elif "prefer not to say" in s_lower or "not say" in s_lower:
        return "Prefer not to say"
    return "UNKNOWN"


def normalize_diet(val: Optional[str]) -> str:
    """Normalize dietary preference labels.
    UNKNOWN is first-class. A blank never means clearance or absence of need.
    """
    if val is None:
        return "UNKNOWN"
    s = str(val).strip()
    if not s or s.lower() in ("unknown", "null", "none", "nan", ""):
        return "UNKNOWN"

    s_lower = s.lower()
    if "non-veg" in s_lower or "non vegetarian" in s_lower:
        return "Non-vegetarian"
    elif "vegetarian" in s_lower or "veg" in s_lower:
        return "Vegetarian"
    elif "jain" in s_lower:
        return "Jain"
    elif "halal" in s_lower:
        return "Halal"
    elif "gluten" in s_lower:
        return "Gluten-free"
    elif "nut" in s_lower or "allergy" in s_lower:
        return "Nut allergy"
    elif "vegan" in s_lower:
        return "Vegan"
    return "UNKNOWN"


def normalize_tri(val: Optional[str]) -> str:
    """Normalize boolean-like values to Tri = YES | NO | UNKNOWN.
    CRITICAL: Blank or unrecognized values become the literal UNKNOWN, never NO.
    """
    if val is None:
        return "UNKNOWN"
    s = str(val).strip().lower()
    if not s or s in ("unknown", "null", "none", "nan", "", "?"):
        return "UNKNOWN"
    if s in ("yes", "y", "true", "t", "1"):
        return "YES"
    if s in ("no", "n", "false", "f", "0"):
        return "NO"
    return "UNKNOWN"


normalize_tri_state = normalize_tri



def normalize_accessibility(val: Optional[str]) -> Dict[str, Any]:
    """Normalize accessibility needs into structured metadata.
    Preserves raw tags while categorizing recognized needs.
    """
    if val is None:
        return {"status": "UNKNOWN", "needs": []}
    s = str(val).strip()
    if not s or s.lower() in ("unknown", "null", "none", "nan", ""):
        return {"status": "UNKNOWN", "needs": []}

    needs: List[str] = []
    parts = [p.strip() for p in re.split(r"[;,|]", s) if p.strip()]
    for p in parts:
        p_lower = p.lower()
        if "wheelchair" in p_lower:
            needs.append("Wheelchair access")
        elif "ground floor" in p_lower or "no stairs" in p_lower:
            needs.append("Ground floor / no stairs")
        elif "washroom" in p_lower or "toilet" in p_lower:
            needs.append("Near washroom")
        elif "visual" in p_lower or "vision" in p_lower:
            needs.append("Visual assistance")
        else:
            needs.append(p)

    return {
        "status": "CLAIMED",
        "raw": s,
        "needs": needs,
        "is_wheelchair": any("Wheelchair" in n for n in needs),
        "is_ground_floor": any("Ground floor" in n for n in needs),
    }


def normalize_housing_preference(val: Optional[str]) -> str:
    """Normalize housing preferences. Blank becomes UNKNOWN."""
    if val is None:
        return "UNKNOWN"
    s = str(val).strip()
    if not s or s.lower() in ("unknown", "null", "none", "nan", ""):
        return "UNKNOWN"
    return s


def normalize_datetime(
    val: Optional[str], default_tz: ZoneInfo = IST
) -> Optional[datetime]:
    """Tolerantly parses mixed date/time strings and normalizes to timezone-aware UTC datetime.
    Raw strings are assumed in Asia/Kolkata (IST) if no timezone offset is given.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("unknown", "null", "none", "nan", ""):
        return None

    # Replace multiple spaces
    s = re.sub(r"\s+", " ", s)

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                # Localize to IST then convert to UTC
                dt = dt.replace(tzinfo=default_tz).astimezone(UTC)
            else:
                dt = dt.astimezone(UTC)
            return dt
        except ValueError:
            continue

    return None


def format_ist(dt: Optional[datetime]) -> Optional[str]:
    """Formats a UTC datetime for display in Asia/Kolkata (IST)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    ist_dt = dt.astimezone(IST)
    return ist_dt.strftime("%Y-%m-%d %H:%M")


def normalize_condition(val: Optional[str]) -> str:
    """Normalizes equipment condition."""
    if val is None:
        return "UNKNOWN"
    s = str(val).strip().lower()
    if "good" in s:
        return "GOOD"
    if "repair" in s:
        return "UNDER_REPAIR"
    if "check" in s or "inspection" in s:
        return "NEEDS_CHECK"
    if "damaged" in s:
        return "DAMAGED"
    if "new" in s:
        return "NEW"
    return "UNKNOWN"
