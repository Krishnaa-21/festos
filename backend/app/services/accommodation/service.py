# OWNER: P2
from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, delete, select

from app.core.clock import now
from app.engines.accommodation.demand import (
    compute_bed_demand_timeline,
    partition_demand,
)
from app.engines.accommodation.planner import AccommodationPlanner
from app.engines.accommodation.reports import (
    generate_accommodation_summary_csv,
    generate_bed_demand_timeline_csv,
    generate_decision_card,
    generate_plan_csv,
    generate_shortage_report_csv,
)
from app.engines.accommodation.types import (
    DemandTimelineResult,
    ParticipantSnapshot,
    PlanResult,
    PropertySnapshot,
    RoomSnapshot,
)
from app.engines.accommodation.why_not import diagnose_unplaced_participant
from app.models.accommodation import AccommodationPlan, ExternalProperty, Room, StayAssignment
from app.models.participants import Participant
from app.schemas.common import DecisionCard
from app.services.assumptions.service import get_assumption

logger = logging.getLogger("festos.services.accommodation")

# In-memory plan cache for instant response times
_PLAN_CACHE: Dict[str, PlanResult] = {}


def _get_raw_data_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "raw"


def load_participant_snapshots(session: Optional[Session] = None) -> List[ParticipantSnapshot]:
    """Load participant snapshots from database or directly from raw CSV."""
    snapshots: List[ParticipantSnapshot] = []

    # 1. Try querying Participant table if session provided
    if session is not None:
        try:
            db_participants = session.exec(select(Participant)).all()
            if db_participants:
                for p in db_participants:
                    # Parse accessibility needs
                    acc_str = "none"
                    if isinstance(p.accessibility_needs, dict):
                        acc_str = p.accessibility_needs.get("type") or p.accessibility_needs.get("need") or "none"
                    elif isinstance(p.accessibility_needs, str):
                        acc_str = p.accessibility_needs

                    has_night = False
                    if p.arrival_at and p.arrival_at.time() >= time(22, 0):
                        has_night = True

                    age_val = p.age if p.age is not None else 21

                    snapshots.append(
                        ParticipantSnapshot(
                            id=p.id,
                            name=p.name or "UNKNOWN",
                            college=p.college or "UNKNOWN",
                            contingent_id=p.contingent_id or "C00",
                            gender=p.gender or "UNKNOWN",
                            age=age_val,
                            accessibility_needs=acc_str,
                            housing_preference=p.housing_preference or "standard",
                            arrival_at=(p.arrival_at.astimezone(timezone.utc).replace(tzinfo=None) if p.arrival_at else None),
                            departure_at=(p.departure_at.astimezone(timezone.utc).replace(tzinfo=None) if p.departure_at else None),
                            accommodation_requested=p.accommodation_requested or "UNKNOWN",
                            is_contingent_leader=(p.role == "LEADER"),
                            is_faculty_escort=(p.role == "ESCORT"),
                            guardian_approved=(age_val >= 18),
                            has_night_arrival=has_night,
                            has_early_event=False,
                        )
                    )
                if snapshots:
                    return snapshots
        except Exception as e:
            logger.warning(f"Failed to load participants from database: {e}. Falling back to CSV.")

    # 2. Fallback: Parse directly from data/raw/participants.csv
    csv_file = _get_raw_data_dir() / "participants.csv"
    if csv_file.exists():
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["participant_id"].strip()
                arr_dt, dep_dt = None, None
                try:
                    arr_dt = datetime.strptime(row["arrival_datetime"].strip(), "%Y-%m-%d %H:%M")
                    dep_dt = datetime.strptime(row["departure_datetime"].strip(), "%Y-%m-%d %H:%M")
                except Exception:
                    pass

                age_val = 21
                try:
                    age_val = int(row.get("age", 21))
                except Exception:
                    pass

                has_night = False
                if arr_dt and arr_dt.time() >= time(22, 0):
                    has_night = True

                snapshots.append(
                    ParticipantSnapshot(
                        id=pid,
                        name=row.get("name", "UNKNOWN").strip(),
                        college=row.get("college", "UNKNOWN").strip(),
                        contingent_id=row.get("contingent_id", "C00").strip(),
                        gender=row.get("gender_as_given", "UNKNOWN").strip() or "BLANK",
                        age=age_val,
                        accessibility_needs=row.get("accessibility_needs", "None").strip(),
                        housing_preference="standard",
                        arrival_at=arr_dt,
                        departure_at=dep_dt,
                        accommodation_requested=row.get("accommodation_requested", "UNKNOWN").strip().upper(),
                        is_contingent_leader=False,
                        is_faculty_escort=False,
                        guardian_approved=(age_val >= 18),
                        has_night_arrival=has_night,
                        has_early_event=False,
                    )
                )

    return snapshots


def load_room_snapshots(session: Optional[Session] = None) -> List[RoomSnapshot]:
    """Load on-campus room snapshots from database or raw hostels.csv."""
    rooms: List[RoomSnapshot] = []

    if session is not None:
        try:
            db_rooms = session.exec(select(Room)).all()
            if db_rooms:
                for r in db_rooms:
                    rooms.append(
                        RoomSnapshot(
                            id=r.id,
                            block=r.block,
                            floor=r.floor,
                            capacity=r.capacity,
                            accessible=r.accessible,
                            accessibility=r.accessibility,
                            gender_class=r.gender_class,
                            status=r.status,
                            cleaning_status=r.cleaning_status,
                        )
                    )
                if rooms:
                    return rooms
        except Exception as e:
            logger.warning(f"Failed to load rooms from DB: {e}. Falling back to CSV.")

    csv_file = _get_raw_data_dir() / "hostels.csv"
    if csv_file.exists():
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                acc_str = row.get("accessibility", "no").strip().lower()
                rooms.append(
                    RoomSnapshot(
                        id=row["room_id"].strip(),
                        block=row["block"].strip(),
                        floor=int(row["floor"].strip()),
                        capacity=int(row["capacity"].strip()),
                        accessible=(acc_str == "yes"),
                        accessibility=acc_str,
                        gender_class=row.get("gender", "UNKNOWN").strip().lower(),
                        status=row.get("status", "available").strip().lower(),
                        cleaning_status="READY",
                    )
                )

    return rooms


def load_property_snapshots(session: Optional[Session] = None) -> List[PropertySnapshot]:
    """Load external property snapshots from database or raw external_stays.csv."""
    properties: List[PropertySnapshot] = []

    if session is not None:
        try:
            db_props = session.exec(select(ExternalProperty)).all()
            if db_props:
                for p in db_props:
                    properties.append(
                        PropertySnapshot(
                            id=p.id,
                            name=p.name,
                            beds=p.beds,
                            cost_per_bed_night=p.cost_per_bed_night,
                            distance_km=p.distance_km,
                            transport_availability=p.transport_availability or "yes",
                            transport_limited=p.transport_limited,
                            accessibility_verified=p.accessibility_verified,
                            gender_suitability_verified=p.gender_suitability_verified,
                            status=p.status,
                        )
                    )
                if properties:
                    return properties
        except Exception as e:
            logger.warning(f"Failed to load external properties from DB: {e}. Falling back to CSV.")

    csv_file = _get_raw_data_dir() / "external_stays.csv"
    if csv_file.exists():
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trans = row.get("transport_availability", "yes").strip().lower()
                properties.append(
                    PropertySnapshot(
                        id=row["property_id"].strip(),
                        name=row["property_name"].strip(),
                        beds=int(row["beds"].strip()),
                        cost_per_bed_night=float(row["cost_per_bed_per_night"].strip()),
                        distance_km=float(row["distance_km"].strip()),
                        transport_availability=trans,
                        transport_limited=(trans == "limited"),
                        accessibility_verified=False,
                        gender_suitability_verified=False,
                        status="ACTIVE",
                    )
                )

    return properties


def generate_plans(
    session: Session,
    kinds: Optional[List[str]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> List[PlanResult]:
    """Execute optimization engine and persist candidate plans (A, B, C) and stay assignments."""
    if not kinds:
        kinds = ["A", "B", "C"]

    params = params or {}
    cleaning_buffer = params.get("cleaning_buffer_minutes")
    if cleaning_buffer is None:
        try:
            val = get_assumption("cleaning_buffer_minutes", session)
            cleaning_buffer = int(val) if val is not None else 180
        except Exception:
            cleaning_buffer = 180

    budget_val = None
    try:
        raw_budget = get_assumption("external_budget_inr", session)
        if raw_budget and str(raw_budget).upper() != "NULL":
            budget_val = float(raw_budget)
    except Exception:
        budget_val = None

    weights = params.get("weights") or {"cohesion": 0.5, "cost": 0.3, "travel": 0.2}

    # Load snapshots
    participants = load_participant_snapshots(session)
    rooms = load_room_snapshots(session)
    properties = load_property_snapshots(session)

    planner = AccommodationPlanner(
        rooms=rooms,
        properties=properties,
        cleaning_buffer_minutes=cleaning_buffer,
        weights=weights,
        budget_inr=budget_val,
        minor_age_threshold=18,
    )

    generated_plans: List[PlanResult] = []

    for k in kinds:
        plan_result = planner.generate_plan(participants, kind=k)
        _PLAN_CACHE[plan_result.plan_id] = plan_result
        generated_plans.append(plan_result)

        # Persist / update AccommodationPlan in database
        existing_plan = session.exec(
            select(AccommodationPlan).where(AccommodationPlan.plan_id == plan_result.plan_id)
        ).first()

        # Serialize unplaced shortages
        shortages_summary = [
            {
                "participant_id": u.participant_id,
                "name": u.name,
                "contingent_id": u.contingent_id,
                "college": u.college,
                "blocking_reason": u.blocking_reason,
                "accessibility_needed": u.accessibility_needed,
                "housing_preference": u.housing_preference,
                "gender": u.gender,
                "rejected_options": u.rejected_options,
                "missing_information": u.missing_information,
                "counterfactual_impact": u.counterfactual_impact,
                "counterfactual_runs": [r.__dict__ for r in u.counterfactual_runs],
                "verification_target": u.verification_target,
            }
            for u in plan_result.unplaced
        ]

        if not existing_plan:
            db_plan = AccommodationPlan(
                plan_id=plan_result.plan_id,
                kind=plan_result.kind,
                name=plan_result.name,
                status=plan_result.status,
                on_campus_placed=plan_result.metrics.on_campus_placed,
                external_placed=plan_result.metrics.external_placed,
                unplaced_count=plan_result.metrics.unplaced_count,
                contingent_splits=plan_result.metrics.contingent_splits,
                total_cost_inr=plan_result.metrics.total_cost_inr,
                safety_flags_count=plan_result.metrics.safety_flags_count,
                accessibility_issues_count=plan_result.metrics.accessibility_issues_count,
                relaxed_constraints_count=plan_result.metrics.relaxed_constraints_count,
                minors_external_count=plan_result.metrics.minors_external_count,
                plan_hash=plan_result.plan_hash,
                sacrifices_summary=plan_result.sacrifices_summary,
                parameters_applied=json.dumps(plan_result.parameters_applied),
                shortages_data=json.dumps(shortages_summary),
                created_at=now(),
                updated_at=now(),
            )
            session.add(db_plan)
        else:
            existing_plan.on_campus_placed = plan_result.metrics.on_campus_placed
            existing_plan.external_placed = plan_result.metrics.external_placed
            existing_plan.unplaced_count = plan_result.metrics.unplaced_count
            existing_plan.contingent_splits = plan_result.metrics.contingent_splits
            existing_plan.total_cost_inr = plan_result.metrics.total_cost_inr
            existing_plan.safety_flags_count = plan_result.metrics.safety_flags_count
            existing_plan.accessibility_issues_count = plan_result.metrics.accessibility_issues_count
            existing_plan.relaxed_constraints_count = plan_result.metrics.relaxed_constraints_count
            existing_plan.minors_external_count = plan_result.metrics.minors_external_count
            existing_plan.plan_hash = plan_result.plan_hash
            existing_plan.sacrifices_summary = plan_result.sacrifices_summary
            existing_plan.parameters_applied = json.dumps(plan_result.parameters_applied)
            existing_plan.shortages_data = json.dumps(shortages_summary)
            existing_plan.updated_at = now()
            session.add(existing_plan)

        # Remove existing stay assignments for this plan and recreate
        session.exec(delete(StayAssignment).where(StayAssignment.plan_id == plan_result.plan_id))

        db_assignments = [
            StayAssignment(
                plan_id=plan_result.plan_id,
                bed_key=a.bed_key,
                participant_id=a.participant_id,
                room_id=a.resource_id if not a.is_external else None,
                property_id=a.resource_id if a.is_external else None,
                is_external=a.is_external,
                start_at=(a.start_at if (a.start_at and a.start_at.tzinfo) else (a.start_at.replace(tzinfo=timezone.utc) if a.start_at else now())),
                end_at=(a.end_at if (a.end_at and a.end_at.tzinfo) else (a.end_at.replace(tzinfo=timezone.utc) if a.end_at else now())),
                cost_inr=a.cost_inr,
                status="ACTIVE",
                explanation=json.dumps(a.explanation.to_dict()),
                version=1,
                created_at=now(),
                updated_at=now(),
            )
            for a in plan_result.assignments
        ]
        session.add_all(db_assignments)

    session.commit()
    return generated_plans


def get_plans(session: Session) -> Tuple[List[AccommodationPlan], bool, Optional[float]]:
    """Retrieve all candidate plans, budget-unset flag, and budget ceiling."""
    plans = session.exec(select(AccommodationPlan).order_by(AccommodationPlan.kind)).all()
    if not plans:
        # Generate default A, B, C plans on first access
        generate_plans(session, ["A", "B", "C"])
        plans = session.exec(select(AccommodationPlan).order_by(AccommodationPlan.kind)).all()

    budget_val = None
    try:
        raw_budget = get_assumption("external_budget_inr", session)
        if raw_budget and str(raw_budget).upper() != "NULL":
            budget_val = float(raw_budget)
    except Exception:
        budget_val = None

    is_budget_unset = (budget_val is None)
    return plans, is_budget_unset, budget_val


def get_plan_by_id(session: Session, plan_id: str) -> Optional[AccommodationPlan]:
    """Retrieve single plan by ID."""
    plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == plan_id)).first()
    if not plan:
        # Ensure plans exist
        get_plans(session)
        plan = session.exec(select(AccommodationPlan).where(AccommodationPlan.plan_id == plan_id)).first()
    return plan


def compare_plans(session: Session, plan_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Provide side-by-side comparison of plan metrics and trade-off analysis."""
    all_plans, is_budget_unset, budget_val = get_plans(session)

    if plan_ids:
        filtered = [p for p in all_plans if p.plan_id in plan_ids or p.kind in plan_ids]
    else:
        filtered = all_plans

    comparison = [
        {
            "plan_id": p.plan_id,
            "kind": p.kind,
            "name": p.name,
            "on_campus_placed": p.on_campus_placed,
            "external_placed": p.external_placed,
            "unplaced_count": p.unplaced_count,
            "contingent_splits": p.contingent_splits,
            "total_cost_inr": p.total_cost_inr,
            "safety_flags_count": p.safety_flags_count,
            "accessibility_issues_count": p.accessibility_issues_count,
            "relaxed_constraints_count": p.relaxed_constraints_count,
            "minors_external_count": p.minors_external_count,
            "sacrifices": p.sacrifices_summary,
            "plan_hash": p.plan_hash,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }
        for p in filtered
    ]

    costs = [p.total_cost_inr for p in filtered]
    cost_spread = max(costs) - min(costs) if costs else 0.0

    return {
        "comparison": comparison,
        "is_budget_unset": is_budget_unset,
        "budget_ceiling_inr": budget_val,
        "trade_off_analysis": {
            "cost_spread_inr": cost_spread,
            "cohesion_winner": "plan_A_cohesion",
            "cost_winner": "plan_A_cohesion" if costs and costs[0] <= costs[min(1, len(costs)-1)] else "plan_B_cost",
        },
    }


def get_plan_shortages(session: Session, plan_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve shortages and unplaced participants grouped by taxonomy blocking reason."""
    target_plan_id = plan_id or "plan_C_balanced"
    plan = get_plan_by_id(session, target_plan_id)

    # If plan is missing entirely from DB, generate default candidate plan
    if plan is None:
        generated = generate_plans(session, ["C"])
        if generated:
            plan = get_plan_by_id(session, "plan_C_balanced")

    shortages_list = []
    if plan and plan.shortages_data:
        try:
            shortages_list = json.loads(plan.shortages_data)
        except Exception:
            pass

    # Group unplaced items by reason_code
    grouped_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in shortages_list:
        code = item.get("blocking_reason", "CAPACITY")
        grouped_map[code].append(item)

    reason_metadata = {
        "HARD_ACCESSIBILITY": {
            "title": "Ground-Floor & Accessible Room Deficit",
            "description": "Wheelchair (72 peak) and ground-floor (80 peak) requests exceed the 10 accessible rooms (26 beds). External properties lack verified accessibility.",
            "criticality": "CRITICAL",
        },
        "GENDER_OR_HOUSING_UNKNOWN": {
            "title": "Gender Unknown or Non-Binary (Safety Gate #2)",
            "description": "Participants with unconfirmed or non-binary gender cannot be placed in gender-segregated campus blocks without neutral/single room verification.",
            "criticality": "HIGH",
        },
        "TRANSPORT_RESTRICTED": {
            "title": "Transport Window & Night Arrival Restrictions",
            "description": "Late arrivals (>22:00) or early events (<08:00) prevent placement in distant or limited-transport properties (EXT04 Lakeview Hotel).",
            "criticality": "HIGH",
        },
        "NO_ELIGIBLE_PROPERTY": {
            "title": "No Eligible Verified Property Available",
            "description": "Remaining demand exceeds available verified room capacity.",
            "criticality": "MEDIUM",
        },
        "BUDGET": {
            "title": "Budget Threshold Exceeded",
            "description": "External accommodation spend ceiling exceeded.",
            "criticality": "MEDIUM",
        },
        "MISSING_INFO": {
            "title": "Missing Escort or Guardian Consent",
            "description": "Minors residing off-campus require documented guardian approval and faculty escort verification.",
            "criticality": "HIGH",
        },
        "CAPACITY": {
            "title": "Peak Capacity Exhausted",
            "description": "All compliant on-campus and external beds occupied during the requested stay window.",
            "criticality": "MEDIUM",
        },
    }

    grouped_by_reason = []
    for code, items in grouped_map.items():
        meta = reason_metadata.get(code, {
            "title": code.replace("_", " ").title(),
            "description": "Accommodation constraint blocked automatic placement.",
            "criticality": "MEDIUM",
        })
        affected_contingents = sorted(list(set(it.get("contingent_id", "") for it in items)))
        grouped_by_reason.append({
            "reason_code": code,
            "title": meta["title"],
            "count": len(items),
            "description": meta["description"],
            "affected_contingents": affected_contingents,
            "criticality": meta["criticality"],
        })

    # Sort groups by criticality
    crit_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    grouped_by_reason.sort(key=lambda g: (crit_order.get(g["criticality"], 4), -g["count"]))

    return {
        "total_unplaced": len(shortages_list),
        "grouped_by_reason": grouped_by_reason,
        "unplaced_items": shortages_list,
    }


def get_why_not(
    session: Session,
    participant_id: str,
    plan_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Produce explainable why-not diagnosis with rejected options and counterfactual simulation."""
    target_plan_id = plan_id or "plan_C_balanced"
    shortages_resp = get_plan_shortages(session, target_plan_id)
    unplaced_items = shortages_resp.get("unplaced_items", [])

    for item in unplaced_items:
        if item.get("participant_id") == participant_id:
            blocking_code = item.get("blocking_reason", "CAPACITY")
            blocking_title = blocking_code.replace("_", " ").title()

            return {
                "participant_id": participant_id,
                "name": item.get("name", "Participant"),
                "contingent_id": item.get("contingent_id", "C00"),
                "plan_id": target_plan_id,
                "blocking_requirement": f"Rule: {blocking_title} Enforcement",
                "blocking_reason_code": blocking_code,
                "missing_information": item.get("missing_information", ""),
                "rejected_options": item.get("rejected_options", []),
                "counterfactual_impact": item.get("counterfactual_impact", ""),
                "counterfactual_runs": item.get("counterfactual_runs", []),
                "verification_target": item.get("verification_target", {
                    "field": "accommodation_needs",
                    "entity_id": participant_id,
                }),
            }

    # If participant is not found in shortages, diagnose live
    participants = load_participant_snapshots(session)
    target_p = next((p for p in participants if p.id == participant_id), None)
    if not target_p:
        return None

    rooms = load_room_snapshots(session)
    properties = load_property_snapshots(session)
    diag = diagnose_unplaced_participant(target_p, rooms, properties)

    return {
        "participant_id": target_p.id,
        "name": target_p.name,
        "contingent_id": target_p.contingent_id,
        "plan_id": target_plan_id,
        "blocking_requirement": f"Rule: {diag.blocking_reason.replace('_', ' ').title()} Enforcement",
        "blocking_reason_code": diag.blocking_reason,
        "missing_information": diag.missing_information,
        "rejected_options": diag.rejected_options,
        "counterfactual_impact": diag.counterfactual_impact,
        "counterfactual_runs": [r.__dict__ for r in diag.counterfactual_runs],
        "verification_target": diag.verification_target,
    }


def get_demand_timeline(session: Session) -> DemandTimelineResult:
    """Calculate bed-demand timeline, confirmed vs possible demand, and peak hour."""
    participants = load_participant_snapshots(session)
    confirmed, possible, invalid = partition_demand(participants, include_leaders_escorts=True)

    cleaning_buffer = 180
    try:
        val = get_assumption("cleaning_buffer_minutes", session)
        if val is not None:
            cleaning_buffer = int(val)
    except Exception:
        cleaning_buffer = 180

    return compute_bed_demand_timeline(
        confirmed_participants=confirmed,
        possible_participants=possible,
        invalid_intervals=invalid,
        total_beds_supply=1450,
        cleaning_buffer_minutes=cleaning_buffer,
        time_step_hours=1,
    )


def get_rooms(session: Session) -> List[Room]:
    """List all on-campus rooms."""
    rooms = session.exec(select(Room).order_by(Room.block, Room.floor, Room.id)).all()
    if not rooms:
        from app.seed.accommodation import seed_accommodation_resources
        seed_accommodation_resources(session)
        rooms = session.exec(select(Room).order_by(Room.block, Room.floor, Room.id)).all()
    return rooms


def get_properties(session: Session) -> List[ExternalProperty]:
    """List all external properties."""
    props = session.exec(select(ExternalProperty).order_by(ExternalProperty.cost_per_bed_night)).all()
    if not props:
        from app.seed.accommodation import seed_accommodation_resources
        seed_accommodation_resources(session)
        props = session.exec(select(ExternalProperty).order_by(ExternalProperty.cost_per_bed_night)).all()
    return props


def get_report_csv(session: Session, report_name: str) -> str:
    """Produce the requested accommodation CSV report string."""
    name_norm = report_name.lower().strip()

    if "plan_a" in name_norm or "plana" in name_norm:
        plans = generate_plans(session, ["A"])
        return generate_plan_csv(plans[0])
    elif "plan_b" in name_norm or "planb" in name_norm:
        plans = generate_plans(session, ["B"])
        return generate_plan_csv(plans[0])
    elif "plan_c" in name_norm or "planc" in name_norm:
        plans = generate_plans(session, ["C"])
        return generate_plan_csv(plans[0])
    elif "shortage" in name_norm:
        plans = generate_plans(session, ["C"])
        return generate_shortage_report_csv(plans[0].unplaced)
    elif "summary" in name_norm:
        plans = generate_plans(session, ["A", "B", "C"])
        return generate_accommodation_summary_csv(plans)
    elif "timeline" in name_norm or "demand" in name_norm:
        timeline_res = get_demand_timeline(session)
        return generate_bed_demand_timeline_csv(timeline_res)
    else:
        # Default fallback: summary
        plans = generate_plans(session, ["A", "B", "C"])
        return generate_accommodation_summary_csv(plans)


def get_decision_card(session: Session, plan_id: str) -> DecisionCard:
    """Generate structured DecisionCard for a plan."""
    plan_res = _PLAN_CACHE.get(plan_id)
    if not plan_res:
        plans = generate_plans(session, ["A", "B", "C"])
        plan_res = next((p for p in plans if p.plan_id == plan_id), plans[0])
    return generate_decision_card(plan_res)
