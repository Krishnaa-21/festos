# OWNER: P2
from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Tuple

# Festival Date Constants (EPINOIA 2026, IIM Indore: Oct 30 - Nov 2, 2026)
FESTIVAL_START_DATE = date(2026, 10, 30)
FESTIVAL_END_DATE = date(2026, 11, 2)


def parse_expiry_date(expiry_str: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD hygiene certificate expiry date."""
    if not expiry_str:
        return None
    try:
        return datetime.strptime(expiry_str.strip()[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def get_certificate_validity_status(expiry_date: Optional[date]) -> str:
    """Classify certificate validity relative to festival dates.

    Returns:
        'EXPIRED': Expired before the festival starts (< 2026-10-30).
        'EXPIRES_DURING_FESTIVAL': Expires during the festival (2026-10-30 to 2026-11-02).
        'VALID_THROUGHOUT': Valid past the end of the festival (> 2026-11-02).
    """
    if not expiry_date:
        return "EXPIRED"

    if expiry_date < FESTIVAL_START_DATE:
        return "EXPIRED"
    elif expiry_date <= FESTIVAL_END_DATE:
        return "EXPIRES_DURING_FESTIVAL"
    else:
        return "VALID_THROUGHOUT"


def is_certificate_valid_at(expiry_date: Optional[date], at_date: date) -> bool:
    """Check if the vendor's certificate is valid on a specific day/slot.

    A vendor's capacity drops out of the coverage strictly after the expiry date.
    On or before the expiry date, the certificate remains valid.
    """
    if not expiry_date:
        return False
    return at_date <= expiry_date


def parse_operating_hours(hours_str: Optional[str]) -> Tuple[time, time]:
    """Parse operating hours string like '07:00-23:00' into start/end time objects."""
    if not hours_str or "-" not in hours_str:
        return time(7, 0), time(23, 0)
    try:
        parts = hours_str.split("-")
        s_parts = parts[0].strip().split(":")
        e_parts = parts[1].strip().split(":")
        start = time(int(s_parts[0]), int(s_parts[1]))
        end = time(int(e_parts[0]), int(e_parts[1]))
        return start, end
    except Exception:
        return time(7, 0), time(23, 0)


def hours_cover_slot(vendor_hours: Optional[str], slot_start: str, slot_end: str) -> bool:
    """Check whether a vendor's operating hours cover a meal slot window."""
    if not vendor_hours:
        return True
    try:
        v_start, v_end = parse_operating_hours(vendor_hours)
        s_parts = slot_start.split(":")
        e_parts = slot_end.split(":")
        s_time = time(int(s_parts[0]), int(s_parts[1]))
        e_time = time(int(e_parts[0]), int(e_parts[1]))

        # Handle overnight hours if any
        if v_end < v_start:
            # e.g. 23:00 to 02:00
            return (s_time >= v_start or s_time <= v_end) and (e_time >= v_start or e_time <= v_end)

        return v_start <= s_time and v_end >= e_time
    except Exception:
        return True


def verify_menu_labels(
    vendor_id: str,
    vendor_name: str,
    menu_description: Optional[str],
    declared_options_str: Optional[str],
) -> List[Dict[str, Any]]:
    """Keyword classifier of menu items against declared dietary options.

    Detects mismatches:
    - VND09: 'Jain thali' menu without Jain declared in options.
    - VND11: 'Vegan bowls' menu with non-vegetarian/halal declared in options.
    Reports as flags for human confirmation (never auto-fixes).
    """
    flags: List[Dict[str, Any]] = []
    menu_text = (menu_description or "").lower().strip()
    declared_raw = (declared_options_str or "").lower().strip()
    declared_tokens = {tok.strip() for tok in re.split(r"[;,/ ]+", declared_raw) if tok.strip()}

    # 1. Check Jain keyword
    if "jain" in menu_text:
        if "jain" not in declared_tokens:
            flags.append({
                "id": f"flg_mismatch_{vendor_id}_jain",
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "flag_type": "MENU_LABEL_MISMATCH",
                "menu_keyword": "Jain thali" if "thali" in menu_text else "Jain",
                "declared_options": list(declared_tokens),
                "severity": "HIGH",
                "status": "UNVERIFIED",
                "message": (
                    f"Menu item '{menu_description}' implies Jain preparation, but Jain is not "
                    f"declared in dietary options ({declared_options_str}). Requires manual audit."
                ),
                "requires_human_confirmation": True,
            })

    # 2. Check Vegan keyword
    if "vegan" in menu_text:
        conflicts = [tok for tok in declared_tokens if tok in ["non-vegetarian", "non_vegetarian", "non-veg"]]
        if "vegan" not in declared_tokens or conflicts:
            flags.append({
                "id": f"flg_mismatch_{vendor_id}_vegan",
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "flag_type": "MENU_LABEL_MISMATCH",
                "menu_keyword": "Vegan bowls" if "bowls" in menu_text else "Vegan",
                "declared_options": list(declared_tokens),
                "severity": "HIGH",
                "status": "UNVERIFIED",
                "message": (
                    f"Menu item '{menu_description}' advertises vegan meals, but declared options "
                    f"include conflicting categories ({declared_options_str}). Requires confirmation."
                ),
                "requires_human_confirmation": True,
            })

    # 3. Check Gluten-free keyword
    if "gluten" in menu_text or "gluten-free" in menu_text:
        if "gluten-free" not in declared_tokens and "gluten_free" not in declared_tokens:
            flags.append({
                "id": f"flg_mismatch_{vendor_id}_gf",
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "flag_type": "MENU_LABEL_MISMATCH",
                "menu_keyword": "Gluten-free",
                "declared_options": list(declared_tokens),
                "severity": "MEDIUM",
                "status": "UNVERIFIED",
                "message": f"Menu item '{menu_description}' mentions gluten-free but not in declared options.",
                "requires_human_confirmation": True,
            })

    # 4. Check Halal keyword
    if "halal" in menu_text and "halal" not in declared_tokens:
        flags.append({
            "id": f"flg_mismatch_{vendor_id}_halal",
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "flag_type": "MENU_LABEL_MISMATCH",
            "menu_keyword": "Halal",
            "declared_options": list(declared_tokens),
            "severity": "MEDIUM",
            "status": "UNVERIFIED",
            "message": f"Menu item '{menu_description}' mentions halal preparation without halal declaration.",
            "requires_human_confirmation": True,
        })

    return flags
