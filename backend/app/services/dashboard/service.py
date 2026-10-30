# OWNER: P1
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlmodel import Session, func, select

from app.core import bus
from app.core.clock import now
from app.core.registry import iter_public_modules
from app.core.scoring import (
    calculate_attention_score,
    heatmap_bucket,
    urgency_from_hours,
)
from app.models.accommodation import ExternalProperty, Room, StayAssignment
from app.models.audit import Approval, Override
from app.models.events import Conflict, EventSession
from app.models.ops import Incident
from app.models.participants import DuplicateCandidate, Participant
from app.models.staff import Staff
from app.models.vendors import Vendor
from app.schemas.common import ActionRef, EntityRef, RiskItem, Role, Severity

logger = logging.getLogger("festos.dashboard.service")

# In-memory metrics cache
_metrics_cache: Optional[Dict[str, Any]] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 15


def invalidate_metrics_cache() -> None:
    """Invalidates the in-memory aggregated dashboard metrics cache."""
    global _metrics_cache, _cache_timestamp
    _metrics_cache = None
    _cache_timestamp = None
    logger.debug("Dashboard metrics cache invalidated")


@bus.subscribe("*")
def _on_bus_mutation_event(payload: Any = None) -> None:
    """Bus subscriber listening for wildcard domain events to invalidate metrics cache."""
    invalidate_metrics_cache()


def get_metrics(
    session: Session,
    actor_role: str = Role.FESTIVAL_DIRECTOR.value,
    bypass_cache: bool = False,
    now_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Aggregates every module's public.summary() into the canonical festival metrics list.

    Caches aggregated output with a 15-second TTL and invalidates on domain events.
    Applies role-aware filtering: VOLUNTEER users receive no sensitive governance or incident data.
    """
    global _metrics_cache, _cache_timestamp
    current_now = now_dt or now()

    is_cache_hit = False
    if (
        not bypass_cache
        and _metrics_cache is not None
        and _cache_timestamp is not None
        and (current_now - _cache_timestamp).total_seconds() < CACHE_TTL_SECONDS
    ):
        base_metrics = dict(_metrics_cache)
        is_cache_hit = True
    else:
        # 1. Gather all module public.summary() outputs
        module_summaries: Dict[str, Any] = {}
        for mod_meta in iter_public_modules():
            slug = mod_meta["slug"]
            if mod_meta["has_summary"] and mod_meta["module"]:
                try:
                    summary_fn = getattr(mod_meta["module"], "summary")
                    summary_res = summary_fn(session, current_now)
                    if isinstance(summary_res, dict):
                        module_summaries[slug] = summary_res
                except Exception as e:
                    logger.warning(f"Error calling public.summary() for module '{slug}': {e}")

        # 2. Extract or query each spec metric with robust fallbacks
        # Participants
        part_sum = module_summaries.get("participants", {})
        try:
            total_participants = part_sum.get("total_canonical") or session.exec(
                select(func.count(Participant.id)).where(Participant.status != "MERGED")
            ).one()
            arrived = part_sum.get("arrived") or session.exec(
                select(func.count(Participant.id)).where(Participant.status == "ARRIVED")
            ).one()
            checked_in = part_sum.get("checked_in") or session.exec(
                select(func.count(Participant.id)).where(Participant.status == "CHECKED_IN")
            ).one()
            pending_arrivals = part_sum.get("expected") or session.exec(
                select(func.count(Participant.id)).where(Participant.status == "EXPECTED")
            ).one()
        except Exception:
            total_participants, arrived, checked_in, pending_arrivals = 0, 0, 0, 0

        # Accommodation
        accom_sum = module_summaries.get("accommodation", {})
        try:
            rooms = session.exec(select(Room)).all()
            ext_props = session.exec(select(ExternalProperty)).all()
            total_beds = sum(r.capacity for r in rooms if r.status == "AVAILABLE") + sum(p.beds for p in ext_props)
            active_stays = len(session.exec(select(StayAssignment).where(StayAssignment.status == "ACTIVE")).all())
            available_beds = accom_sum.get("available_beds", max(0, total_beds - active_stays))
            occupancy_pct = accom_sum.get("occupancy_pct", round((active_stays / total_beds * 100), 1) if total_beds > 0 else 0.0)

            # Unplaced: participants expecting housing with no active stay assignment
            assigned_ids = select(StayAssignment.participant_id).where(StayAssignment.status == "ACTIVE")
            unplaced = accom_sum.get("unplaced_participants")
            if unplaced is None:
                unplaced = session.exec(
                    select(func.count(Participant.id)).where(
                        Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]),
                        Participant.accommodation_requested.in_(["YES", "UNKNOWN"]),
                        ~Participant.id.in_(assigned_ids),
                    )
                ).one()
        except Exception:
            available_beds, occupancy_pct, unplaced = 0, 0.0, 0

        # Schedule
        sched_sum = module_summaries.get("schedule", {})
        try:
            active_sessions = sched_sum.get("total_sessions") or session.exec(
                select(func.count(EventSession.id)).where(EventSession.status != "CANCELLED")
            ).one()
            open_conflicts = sched_sum.get("active_conflicts") or session.exec(
                select(func.count(Conflict.id)).where(Conflict.status == "OPEN")
            ).one()
        except Exception:
            active_sessions, open_conflicts = 0, 0

        # Logistics
        log_sum = module_summaries.get("logistics", {})
        try:
            equipment_availability = log_sum.get("total_available", 0)
            equipment_in_transit = log_sum.get("total_in_transit", 0)
            equipment_under_repair = log_sum.get("total_under_repair", 0)
        except Exception:
            equipment_availability, equipment_in_transit, equipment_under_repair = 0, 0, 0

        # Merchandise
        merch_sum = module_summaries.get("merchandise", {})
        try:
            merchandise_stock = merch_sum.get("total_available", 0)
            merch_issued = merch_sum.get("total_claims_issued", 0)
            merch_total_stock = merch_sum.get("total_on_hand", 0)
        except Exception:
            merchandise_stock, merch_issued, merch_total_stock = 0, 0, 0

        # Food & Vendors
        food_sum = module_summaries.get("food", {})
        vendor_sum = module_summaries.get("vendors", {})
        try:
            active_vendors_count = session.exec(select(func.count(Vendor.id)).where(Vendor.status == "ACTIVE")).one()
            vendor_status = vendor_sum.get("status") or ("OPERATIONAL" if active_vendors_count > 0 else "DEGRADED")
            food_coverage_gaps = food_sum.get("coverage_gaps", 0)
            uncovered_meals = food_sum.get("uncovered_meals", 0)
        except Exception:
            active_vendors_count, vendor_status, food_coverage_gaps, uncovered_meals = 0, "UNKNOWN", 0, 0

        # Staff
        staff_sum = module_summaries.get("staff", {})
        try:
            staff_availability = staff_sum.get("peak_available_on_shift", 0)
            core_team_active = staff_sum.get("total_staff_core_team") or session.exec(select(func.count(Staff.id))).one()
            peak_staffing_gap = staff_sum.get("max_staffing_gap", 0)
        except Exception:
            staff_availability, core_team_active, peak_staffing_gap = 0, 0, 0

        # Governance & Incidents
        try:
            open_incidents = session.exec(
                select(func.count(Incident.id)).where(Incident.status.in_(["OPEN", "IN_PROGRESS", "INVESTIGATING"]))
            ).one()
            pending_approvals = session.exec(
                select(func.count(Approval.id)).where(Approval.status == "PENDING")
            ).one()
            active_overrides = session.exec(
                select(func.count(Override.id)).where(Override.status == "ACTIVE")
            ).one()
        except Exception:
            open_incidents, pending_approvals, active_overrides = 0, 0, 0

        # Assemble full unmasked metrics
        base_metrics = {
            # Flat canonical spec metrics
            "total_participants": total_participants,
            "arrived": arrived,
            "checked_in": checked_in,
            "pending_arrivals": pending_arrivals,
            "occupancy": occupancy_pct,
            "available_beds": available_beds,
            "unplaced": unplaced,
            "active_sessions": active_sessions,
            "open_conflicts": open_conflicts,
            "equipment_availability": equipment_availability,
            "merchandise_stock": merchandise_stock,
            "vendor_status": vendor_status,
            "food_coverage_gaps": food_coverage_gaps,
            "staff_availability": staff_availability,
            "open_incidents": open_incidents,
            "pending_approvals": pending_approvals,
            "active_overrides": active_overrides,
            # Structured categorised subsets
            "participants": {
                "total": total_participants,
                "arrived": arrived,
                "checked_in": checked_in,
                "pending_arrivals": pending_arrivals,
            },
            "accommodation": {
                "occupancy_pct": occupancy_pct,
                "available_beds": available_beds,
                "unplaced_participants": unplaced,
            },
            "schedule": {
                "active_sessions": active_sessions,
                "open_conflicts": open_conflicts,
            },
            "logistics": {
                "equipment_available": equipment_availability,
                "equipment_in_transit": equipment_in_transit,
                "equipment_under_repair": equipment_under_repair,
            },
            "merchandise": {
                "total_stock": merch_total_stock,
                "issued_count": merch_issued,
                "available_stock": merchandise_stock,
            },
            "food": {
                "active_vendors": active_vendors_count,
                "vendor_status": vendor_status,
                "coverage_gaps": food_coverage_gaps,
                "uncovered_meals": uncovered_meals,
            },
            "staff": {
                "core_team_active": core_team_active,
                "volunteers_on_shift": staff_availability,
                "peak_staffing_gap": peak_staffing_gap,
            },
            "governance": {
                "open_incidents": open_incidents,
                "pending_approvals": pending_approvals,
                "active_overrides": active_overrides,
            },
            "cached_at": current_now.isoformat(),
        }

        # Cache unmasked data
        _metrics_cache = dict(base_metrics)
        _cache_timestamp = current_now

    # 3. Apply role-aware filtering
    out_data = dict(base_metrics)
    out_data["is_cached"] = is_cache_hit

    if actor_role == Role.VOLUNTEER.value:
        # Strip all sensitive governance, incident, approval, and override details
        out_data["open_incidents"] = None
        out_data["pending_approvals"] = None
        out_data["active_overrides"] = None
        out_data["governance"] = {
            "open_incidents": None,
            "pending_approvals": None,
            "active_overrides": None,
            "note": "REDACTED_FOR_ROLE",
        }

    return out_data


def _gather_spec_risks_if_missing(session: Session, current_now: datetime, existing_keys: Set[str]) -> List[RiskItem]:
    """Generates spec-required risk classes if not already reported by individual modules."""
    generated: List[RiskItem] = []

    # 1. Unconfirmed accessibility needs arriving within 6 hours
    if "accommodation:ACCESSIBILITY_ARRIVAL_IMMINENT" not in existing_keys:
        window_end = current_now + timedelta(hours=6)
        urgent_accessible_candidates = session.exec(
            select(Participant).where(
                Participant.status == "EXPECTED",
                Participant.arrival_at >= current_now,
                Participant.arrival_at <= window_end,
                Participant.accessibility_needs.isnot(None),
            )
        ).all()
        urgent_accessible = [
            p for p in urgent_accessible_candidates
            if p.accessibility_needs and p.accessibility_needs != {}
        ]
        if urgent_accessible:
            hours_impact = 2.0
            if urgent_accessible[0].arrival_at:
                hours_impact = max(0.5, (urgent_accessible[0].arrival_at - current_now).total_seconds() / 3600.0)
            generated.append(
                RiskItem(
                    id="risk_unconfirmed_accessibility",
                    module="accommodation",
                    kind="ACCESSIBILITY_ARRIVAL_IMMINENT",
                    title=f"{len(urgent_accessible)} Participants with unconfirmed accessibility needs arriving within 6h",
                    severity=Severity.CRITICAL,
                    hours_to_impact=hours_impact,
                    people_affected=len(urgent_accessible),
                    uncertainty=0.05,
                    resource_criticality=5,
                    entity_refs=[EntityRef(type="participant", id=p.id, label=p.name) for p in urgent_accessible[:5]],
                    action=ActionRef(
                        label="Assign Accessible Rooms",
                        route="/accommodation/rooms",
                        api="/api/v1/accommodation/allocate",
                    ),
                    explanation="Arriving participants require ground-floor or wheelchair-accessible accommodation.",
                )
            )

    # 2. Unplaced participants
    if "accommodation:UNPLACED_PARTICIPANTS" not in existing_keys:
        assigned_ids = select(StayAssignment.participant_id).where(StayAssignment.status == "ACTIVE")
        unplaced_p = session.exec(
            select(Participant).where(
                Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]),
                Participant.accommodation_requested.in_(["YES", "UNKNOWN"]),
                ~Participant.id.in_(assigned_ids),
            )
        ).all()
        if unplaced_p:
            generated.append(
                RiskItem(
                    id="risk_unplaced_participants",
                    module="accommodation",
                    kind="UNPLACED_PARTICIPANTS",
                    title=f"{len(unplaced_p)} participants currently have no confirmed room placement",
                    severity=Severity.HIGH,
                    hours_to_impact=2.0,
                    people_affected=len(unplaced_p),
                    uncertainty=0.1,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="participant", id=p.id, label=p.name) for p in unplaced_p[:5]],
                    action=ActionRef(
                        label="Auto-Allocate Rooms",
                        route="/accommodation/rooms",
                        api="/api/v1/accommodation/allocate",
                    ),
                    explanation="Arrival wave exceeds currently assigned on-campus beds.",
                )
            )

    # 3. Bed shortages
    if "accommodation:BED_SHORTAGE" not in existing_keys:
        rooms = session.exec(select(Room)).all()
        ext_props = session.exec(select(ExternalProperty)).all()
        total_beds = sum(r.capacity for r in rooms if r.status == "AVAILABLE") + sum(p.beds for p in ext_props)
        needing_beds = session.exec(
            select(func.count(Participant.id)).where(
                Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]),
                Participant.accommodation_requested == "YES",
            )
        ).one()
        if needing_beds > total_beds:
            shortage = needing_beds - total_beds
            generated.append(
                RiskItem(
                    id="risk_bed_shortage",
                    module="accommodation",
                    kind="BED_SHORTAGE",
                    title=f"Critical bed deficit: shortage of {shortage} beds campus-wide",
                    severity=Severity.CRITICAL,
                    hours_to_impact=3.0,
                    people_affected=shortage,
                    uncertainty=0.05,
                    resource_criticality=5,
                    entity_refs=[EntityRef(type="module", id="accommodation", label="Campus Hostels")],
                    action=ActionRef(
                        label="Contract External Stays",
                        route="/accommodation/external",
                        api="/api/v1/accommodation/properties",
                    ),
                    explanation="Capacity ceiling reached. Emergency external properties must be chartered.",
                )
            )

    # 4. Expired hygiene certificates
    if "vendors:EXPIRED_HYGIENE_CERTIFICATE" not in existing_keys:
        vendors = session.exec(select(Vendor).where(Vendor.status == "ACTIVE")).all()
        expired_vendors = []
        for v in vendors:
            is_expired = False
            if v.hygiene_valid_to and v.hygiene_valid_to < current_now:
                is_expired = True
            elif v.hygiene_certificate_expiry:
                try:
                    exp_dt = datetime.fromisoformat(v.hygiene_certificate_expiry)
                    if exp_dt < current_now:
                        is_expired = True
                except Exception:
                    pass
            if is_expired:
                expired_vendors.append(v)
        if expired_vendors:
            v0 = expired_vendors[0]
            generated.append(
                RiskItem(
                    id=f"risk_vendor_expired_cert_{v0.id}",
                    module="vendors",
                    kind="EXPIRED_HYGIENE_CERTIFICATE",
                    title=f"Food safety alert: vendor '{v0.name}' hygiene certificate expired",
                    severity=Severity.HIGH,
                    hours_to_impact=1.0,
                    people_affected=v0.capacity or 200,
                    uncertainty=0.0,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="vendor", id=v0.id, label=v0.name)],
                    action=ActionRef(
                        label="Inspect Food Vendor",
                        route="/vendors",
                        api=f"/api/v1/vendors/{v0.id}",
                    ),
                    explanation="Statutory compliance breach: vendor operating with invalid food safety certificate.",
                )
            )

    # 5. Dietary gaps
    if "food:DIETARY_COVERAGE_GAP" not in existing_keys:
        special_diet_count = session.exec(
            select(func.count(Participant.id)).where(
                Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]),
                Participant.diet.in_(["JAIN", "VEGAN", "HALAL"]),
            )
        ).one()
        if special_diet_count > 0:
            # Check if any vendor serves this
            vendors = session.exec(select(Vendor).where(Vendor.status == "ACTIVE")).all()
            if len(vendors) < 2:  # shortage
                generated.append(
                    RiskItem(
                        id="risk_dietary_gap_special",
                        module="food",
                        kind="DIETARY_COVERAGE_GAP",
                        title=f"Dietary gap: {special_diet_count} participants with specialized dietary needs",
                        severity=Severity.MEDIUM,
                        hours_to_impact=5.0,
                        people_affected=special_diet_count,
                        uncertainty=0.15,
                        resource_criticality=3,
                        entity_refs=[EntityRef(type="module", id="food", label="Catering Operations")],
                        action=ActionRef(
                            label="Reallocate Meal Slots",
                            route="/food/allocations",
                            api="/api/v1/food/allocate",
                        ),
                        explanation="Insufficient specialized vendor capacity for Jain and Vegan attendees.",
                    )
                )

    # 6. Duplicates awaiting review
    if "participants:DUPLICATE_CANDIDATES_PENDING" not in existing_keys:
        pending_dups = session.exec(
            select(DuplicateCandidate).where(DuplicateCandidate.status == "PENDING")
        ).all()
        if pending_dups:
            generated.append(
                RiskItem(
                    id="risk_par_unresolved_duplicates",
                    module="participants",
                    kind="DUPLICATE_CANDIDATES_PENDING",
                    title=f"{len(pending_dups)} duplicate candidate registrations awaiting review",
                    severity=Severity.HIGH,
                    hours_to_impact=2.0,
                    people_affected=len(pending_dups) * 2,
                    uncertainty=0.1,
                    resource_criticality=3,
                    entity_refs=[EntityRef(type="duplicate_candidate", id=d.id, label=f"Dup {d.id}") for d in pending_dups[:5]],
                    action=ActionRef(
                        label="Open Reconciliation",
                        route="/reconciliation",
                        api="/api/v1/reconciliation/duplicates",
                    ),
                    explanation="Unresolved duplicates risk double bed and merch issuance.",
                )
            )

    # 7. Late/missing arrivals
    if "participants:OVERDUE_ARRIVALS" not in existing_keys:
        overdue = session.exec(
            select(Participant).where(
                Participant.status == "EXPECTED",
                Participant.arrival_at < current_now,
            )
        ).all()
        if overdue:
            generated.append(
                RiskItem(
                    id="risk_par_overdue_arrivals",
                    module="participants",
                    kind="OVERDUE_ARRIVALS",
                    title=f"{len(overdue)} Participants overdue for scheduled arrival",
                    severity=Severity.MEDIUM,
                    hours_to_impact=1.0,
                    people_affected=len(overdue),
                    uncertainty=0.2,
                    resource_criticality=2,
                    entity_refs=[EntityRef(type="participant", id=p.id, label=p.name) for p in overdue[:5]],
                    action=ActionRef(
                        label="Review Expected Arrivals",
                        route="/participants",
                        api="/api/v1/participants?status=EXPECTED",
                    ),
                    explanation="Participants have missed scheduled arrival time. Contingent leads must be contacted.",
                )
            )

    # 8. Pending high-risk approvals
    if "approvals:PENDING_APPROVAL_BOTTLENECK" not in existing_keys:
        pending_appr = session.exec(
            select(Approval).where(Approval.status == "PENDING")
        ).all()
        if pending_appr:
            a0 = pending_appr[0]
            generated.append(
                RiskItem(
                    id=f"risk_approval_{a0.id}",
                    module="approvals",
                    kind="PENDING_APPROVAL_BOTTLENECK",
                    title=f"Pending High-Risk Approval: {a0.entity_type} ({len(pending_appr)} awaiting sign-off)",
                    severity=Severity.HIGH,
                    hours_to_impact=2.0,
                    people_affected=len(pending_appr) * 10,
                    uncertainty=0.1,
                    resource_criticality=4,
                    entity_refs=[EntityRef(type="approval", id=a.id, label=a.id) for a in pending_appr[:5]],
                    action=ActionRef(
                        label="Review Approvals Queue",
                        route="/audit",
                        api=f"/api/v1/approvals/{a0.id}",
                    ),
                    explanation="Operational mutations blocked awaiting Festival Director sign-off.",
                )
            )

    return generated


def get_attention_queue(
    session: Session,
    limit: int = 20,
    min_severity: Optional[int] = None,
    module: Optional[str] = None,
    now_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Gathers public.risks() from all modules, deduplicates, and ranks strictly by core.scoring.

    Attention Score = Severity (1-4) x Urgency (1-5) x max(people_affected, 1).
    Guarantees every alert carries a direct actionable route and API endpoint.
    """
    current_now = now_dt or now()
    all_raw_risks: List[RiskItem] = []

    # 1. Collect from all public modules
    for mod_meta in iter_public_modules():
        slug = mod_meta["slug"]
        if mod_meta["has_risks"] and mod_meta["module"]:
            try:
                risks_fn = getattr(mod_meta["module"], "risks")
                r_list = risks_fn(session, current_now)
                if isinstance(r_list, list):
                    all_raw_risks.extend(r_list)
            except Exception as e:
                logger.warning(f"Error calling public.risks() for module '{slug}': {e}")

    # 2. Add spec classes if not already reported by a module
    existing_keys: Set[str] = {f"{r.module}:{r.kind}" for r in all_raw_risks}
    supplementary_risks = _gather_spec_risks_if_missing(session, current_now, existing_keys)
    all_raw_risks.extend(supplementary_risks)

    # 3. Deduplicate by unique (module, kind, id)
    seen_keys: Set[str] = set()
    deduped_risks: List[RiskItem] = []
    for r in all_raw_risks:
        dedup_key = f"{r.module}:{r.kind}:{r.id}"
        if dedup_key not in seen_keys:
            seen_keys.add(dedup_key)
            deduped_risks.append(r)

    # 4. Rank using core.scoring.calculate_attention_score ONLY
    scored_items: List[Dict[str, Any]] = []
    for r in deduped_risks:
        sev_val = r.severity.value if isinstance(r.severity, Severity) else int(r.severity)
        if min_severity is not None and sev_val < min_severity:
            continue
        if module is not None and r.module.lower() != module.lower():
            continue

        urgency_val = urgency_from_hours(r.hours_to_impact)
        # Strict core.scoring calculation
        score = calculate_attention_score(sev_val, r.hours_to_impact, r.people_affected)

        # Guarantee direct action exists
        action_dict = (
            r.action.model_dump()
            if r.action
            else {"label": "Investigate Risk", "route": f"/{r.module}", "api": f"/api/v1/{r.module}"}
        )

        item_data = {
            "id": r.id,
            "module": r.module,
            "kind": r.kind,
            "title": r.title,
            "severity": sev_val,
            "hours_to_impact": r.hours_to_impact,
            "urgency": urgency_val,
            "people_affected": r.people_affected,
            "score": score,
            "resource_criticality": r.resource_criticality,
            "uncertainty": r.uncertainty,
            "entity_refs": [ref.model_dump() for ref in r.entity_refs],
            "action": action_dict,
            "explanation": r.explanation,
        }
        scored_items.append(item_data)

    # Sort descending strictly by score, then severity, then people_affected
    scored_items.sort(key=lambda x: (x["score"], x["severity"], x["people_affected"]), reverse=True)

    total_unresolved = len(scored_items)
    paged_items = scored_items[:limit]

    return {
        "attention_items": paged_items,
        "total_unresolved": total_unresolved,
        "limit": limit,
    }


def get_risk_heatmap(session: Session, now_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """Returns 2D Severity x Time-to-Impact risk heatmap cells with aggregates and top contributors.

    Organized in a 4 (Severity 1-4) x 5 (Urgency 1-5) matrix using core.scoring.
    """
    current_now = now_dt or now()
    # Gather all deduplicated risks
    queue_data = get_attention_queue(session, limit=1000, now_dt=current_now)
    items = queue_data.get("attention_items", [])

    time_window_map = {
        5: "<= 1 hour",
        4: "<= 4 hours",
        3: "<= 12 hours",
        2: "<= 24 hours",
        1: "> 24 hours",
    }

    # Group into cells: (sev, urg)
    cells: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for it in items:
        sev = it["severity"]
        urg = it["urgency"]
        cells.setdefault((sev, urg), []).append(it)

    matrix: List[Dict[str, Any]] = []
    critical_quadrant_risks = 0

    for (sev, urg), cell_items in cells.items():
        cell_info = heatmap_bucket(sev, cell_items[0]["hours_to_impact"] if cell_items else None)
        is_crit = cell_info["is_critical_quadrant"]
        if is_crit:
            critical_quadrant_risks += len(cell_items)

        total_people = sum(it["people_affected"] for it in cell_items)
        avg_uncertainty = round(sum(it["uncertainty"] for it in cell_items) / len(cell_items), 2)
        max_crit = max(it["resource_criticality"] for it in cell_items)

        # Top 3 contributors by attention score
        sorted_cell = sorted(cell_items, key=lambda x: x["score"], reverse=True)
        top_risks = [
            {
                "id": c["id"],
                "title": c["title"],
                "module": c["module"],
                "score": c["score"],
                "action_route": c["action"]["route"] if c.get("action") else f"/{c['module']}",
            }
            for c in sorted_cell[:3]
        ]

        matrix.append({
            "severity": sev,
            "urgency": urg,
            "urgency_label": cell_info["urgency_label"],
            "time_window": time_window_map.get(urg, "unknown"),
            "risk_count": len(cell_items),
            "people_affected": total_people,
            "avg_uncertainty": avg_uncertainty,
            "max_criticality": max_crit,
            "is_critical_quadrant": is_crit,
            "top_risks": top_risks,
        })

    # Sort matrix by severity desc, urgency desc
    matrix.sort(key=lambda c: (c["severity"], c["urgency"]), reverse=True)

    return {
        "matrix": matrix,
        "summary": {
            "critical_quadrant_risks": critical_quadrant_risks,
            "total_risks_mapped": len(items),
        },
    }
