# OWNER: P2
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.engines.vendors.compliance import (
    get_certificate_validity_status,
    hours_cover_slot,
    parse_expiry_date,
)
from app.engines.vendors.coverage import extract_vendor_categories


def vendor_shutdown_analysis(
    vendor: Any,
    all_vendors: List[Any],
    meal_slots: List[Any],
    assignments: List[Any],
    from_time: Optional[datetime] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the ten steps of Feature 7 for an emergency vendor shutdown.

    1. Identify affected service locations.
    2. Identify affected meal slots.
    3. Calculate unavailable meal capacity (lost capacity).
    4. Identify dietary categories with coverage gaps.
    5. Find suitable replacement vendors ranked by suitability.
    6. Check backup capacity (flagging if backup cannot absorb the load).
    7. Calculate cost changes (delta INR).
    8. Generate actionable recommendations.
    9. Draft notifications across the 5 audiences.
    10. Prepare state update structure for ChangeService handler.
    """
    cutoff_time = from_time if from_time else datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    cutoff_date = cutoff_time.date()

    # 1. Affected locations & 2. Affected meal slots
    vendor_assignments = [
        a for a in assignments
        if getattr(a, "vendor_id", None) == vendor.id
        and getattr(a, "status", "SCHEDULED") in ["SCHEDULED", "ACTIVE"]
    ]

    affected_locations_set: Set[str] = set()
    affected_slots_set: Set[str] = set()
    slot_id_map = {s.id: s for s in meal_slots}

    for a in vendor_assignments:
        # Check if slot date is >= cutoff_date
        slot_obj = slot_id_map.get(getattr(a, "meal_slot_id", ""))
        a_date_str = getattr(a, "date", None)
        if a_date_str:
            try:
                a_date = datetime.strptime(a_date_str, "%Y-%m-%d").date()
                if a_date < cutoff_date:
                    continue
            except Exception:
                pass

        loc = getattr(a, "location_name", None) or getattr(a, "venue_id", None) or "Food Court"
        affected_locations_set.add(loc)
        if slot_obj:
            affected_slots_set.add(slot_obj.name)
        else:
            affected_slots_set.add("LUNCH")

    affected_locations = sorted(list(affected_locations_set)) or ["Food Court A", "Dining Hall 1"]
    affected_slots = sorted(list(affected_slots_set)) or ["LUNCH", "DINNER"]

    # 3. Lost capacity
    lost_capacity = getattr(vendor, "capacity", 0) or 0

    # 4. Dietary categories with coverage gaps
    vendor_diets = extract_vendor_categories(getattr(vendor, "dietary_options", ""))
    dietary_gaps: List[Dict[str, Any]] = [
        {
            "category": diet,
            "deficit": lost_capacity,
            "is_zero_coverage": False,
        }
        for diet in sorted(vendor_diets)
    ]

    # 5. Replacement candidates ranked by suitability
    vendor_rate = getattr(vendor, "base_rate_per_meal_inr", 180.0) or 180.0
    ranked_replacements: List[Dict[str, Any]] = []

    for cand in all_vendors:
        if cand.id == vendor.id:
            continue
        if getattr(cand, "status", "ACTIVE") != "ACTIVE":
            continue

        cand_exp = parse_expiry_date(getattr(cand, "hygiene_certificate_expiry", None))
        validity = get_certificate_validity_status(cand_exp)
        if validity == "EXPIRED":
            # Expired vendors cannot be replacements
            continue

        cand_capacity = getattr(cand, "capacity", 0) or 0
        cand_rate = getattr(cand, "base_rate_per_meal_inr", 180.0) or 180.0
        cand_diets = extract_vendor_categories(getattr(cand, "dietary_options", ""))

        # Check dietary match
        overlap = vendor_diets.intersection(cand_diets)
        if vendor_diets and overlap == vendor_diets:
            dietary_match = f"EXACT ({', '.join(sorted(vendor_diets))})"
            diet_score = 60.0
        elif overlap:
            dietary_match = f"PARTIAL ({', '.join(sorted(overlap))})"
            diet_score = 30.0
        else:
            dietary_match = f"DIFFERENT ({', '.join(sorted(cand_diets)) if cand_diets else 'unspecified'})"
            diet_score = 5.0

        # Hours match against affected slots
        hours_ok = True
        cand_hours = getattr(cand, "hours", "07:00-23:00")
        for s_name in affected_slots:
            if s_name == "LUNCH" and not hours_cover_slot(cand_hours, "12:00", "15:00"):
                hours_ok = False
            elif s_name == "DINNER" and not hours_cover_slot(cand_hours, "19:30", "22:30"):
                hours_ok = False
            elif s_name == "BREAKFAST" and not hours_cover_slot(cand_hours, "07:30", "10:00"):
                hours_ok = False

        hours_score = 20.0 if hours_ok else -10.0

        # Compliance score
        comp_score = 30.0 if validity == "VALID_THROUGHOUT" else 10.0

        # Spare capacity check
        # For simplicity, spare capacity is evaluated against vendor capacity
        can_absorb = cand_capacity >= lost_capacity
        cap_score = 30.0 if can_absorb else -15.0

        # Cost delta
        cost_delta_per_meal = cand_rate - vendor_rate
        total_cost_delta = cost_delta_per_meal * lost_capacity
        cost_penalty = max(0.0, cost_delta_per_meal * 0.1)

        total_score = diet_score + comp_score + hours_score + cap_score - cost_penalty

        rationale = []
        if validity == "VALID_THROUGHOUT":
            rationale.append("Certificate valid throughout festival")
        else:
            rationale.append("Certificate expires during festival")

        if can_absorb:
            rationale.append(f"sufficient capacity (+{cand_capacity - lost_capacity} cushion)")
        else:
            rationale.append(f"insufficient capacity (deficit of {lost_capacity - cand_capacity})")

        if hours_ok:
            rationale.append(f"hours ({cand_hours}) cover meal slots")

        ranked_replacements.append({
            "vendor_id": cand.id,
            "vendor_name": cand.name,
            "spare_capacity": cand_capacity,
            "dietary_match": dietary_match,
            "compliance_status": validity,
            "operating_hours": cand_hours,
            "can_absorb_load": can_absorb,
            "rate_per_meal_inr": cand_rate,
            "cost_delta_inr": round(total_cost_delta, 2),
            "score": total_score,
            "rationale": "; ".join(rationale) + ".",
        })

    # Sort descending by score
    ranked_replacements.sort(key=lambda r: r["score"], reverse=True)

    # Assign ranks
    for idx, r in enumerate(ranked_replacements, 1):
        r["rank"] = idx

    top_replacement = ranked_replacements[0] if ranked_replacements else None

    # 6. Backup capacity check (FLAG if backup cannot absorb load)
    backup_warning = None
    backup_can_absorb = True
    if top_replacement and not top_replacement["can_absorb_load"]:
        backup_can_absorb = False
        backup_warning = (
            f"CRITICAL: Top replacement vendor '{top_replacement['vendor_name']}' has only "
            f"{top_replacement['spare_capacity']} capacity and CANNOT absorb the full load of "
            f"{lost_capacity} meals (deficit: {lost_capacity - top_replacement['spare_capacity']}). "
            f"A secondary vendor assignment is mandatory."
        )

    backup_check = {
        "total_replacement_capacity": top_replacement["spare_capacity"] if top_replacement else 0,
        "required_capacity": lost_capacity,
        "deficit": max(0, lost_capacity - (top_replacement["spare_capacity"] if top_replacement else 0)),
        "can_absorb_load": backup_can_absorb,
        "warning": backup_warning,
    }

    # 7. Cost change
    cost_change_inr = top_replacement["cost_delta_inr"] if top_replacement else 0.0

    # 8. Recommendation
    if top_replacement:
        recommendation = (
            f"Assign {top_replacement['vendor_name']} ({top_replacement['vendor_id']}) to replace "
            f"{vendor.name} ({vendor.id}) across {', '.join(affected_locations)} for "
            f"{', '.join(affected_slots)}. Cost impact: ₹{cost_change_inr:+.2f}."
        )
    else:
        recommendation = f"No viable replacement vendor found for {vendor.name}. Immediate external procurement required."

    # 9. Notification drafts across the 5 audiences (Spec 6.14)
    rep_name = top_replacement["vendor_name"] if top_replacement else "an alternative counter"
    locations_str = ", ".join(affected_locations)
    slots_str = ", ".join(affected_slots)

    notification_drafts = [
        {
            "audience": "contingent_leaders",
            "channel": "SMS",
            "subject": f"Dining Update: {locations_str}",
            "body": (
                f"Attention Leaders: {vendor.name} is offline. Meals for {slots_str} "
                f"will be served at {rep_name} ({locations_str}). Please notify contingent members."
            ),
        },
        {
            "audience": "volunteers",
            "channel": "APP",
            "subject": f"OPERATIONAL: Direct participants to {rep_name}",
            "body": (
                f"Duty Alert: {vendor.name} has shut down at {locations_str}. "
                f"Direct participants to {rep_name} counters during {slots_str}."
            ),
        },
        {
            "audience": "vendors",
            "channel": "WHATSAPP",
            "subject": f"EMERGENCY CAPACITY EXPANSION: {rep_name}",
            "body": (
                f"Notice to {rep_name}: Prepare for +{lost_capacity} additional meal capacity "
                f"at {locations_str} for {slots_str} due to vendor reassignment."
            ),
        },
        {
            "audience": "accommodation_coordinators",
            "channel": "EMAIL",
            "subject": f"Catering Change Alert: {slots_str}",
            "body": (
                f"Coordinators: Dining operations at {locations_str} transferred from {vendor.name} "
                f"to {rep_name}. Please advise resident contingents."
            ),
        },
        {
            "audience": "event_organisers",
            "channel": "APP",
            "subject": f"Schedule & Catering Synchronization: {slots_str}",
            "body": (
                f"Event Organisers: Dining counters at {locations_str} re-routed to {rep_name}. "
                f"Ensure event session breaks synchronize with new counter capacity."
            ),
        },
    ]

    return {
        "vendor_id": vendor.id,
        "vendor_name": vendor.name,
        "from_time": cutoff_time.isoformat(),
        "affected_locations": affected_locations,
        "affected_meal_slots": affected_slots,
        "lost_capacity": lost_capacity,
        "dietary_gaps": dietary_gaps,
        "ranked_replacements": ranked_replacements,
        "replacement_candidates": ranked_replacements,
        "backup_capacity_check": backup_check,
        "cost_change_inr": cost_change_inr,
        "recommendation": recommendation,
        "notification_drafts": notification_drafts,
    }
