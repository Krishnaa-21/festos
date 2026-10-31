# OWNER: P2
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.core.db import get_session
from app.core.deps import require_permission
from app.schemas.accommodation import (
    AccommodationPlanSchema,
    CleaningCompleteRequest,
    CommitPlanRequest,
    DemandTimelineResponseData,
    FreezePlanRequest,
    GeneratePlanRequest,
    IncrementalAllocateRequest,
    ManualAssignRequest,
    PlansResponseData,
    PropertyItemSchema,
    PropertyUpdateRequest,
    RepairPlanRequest,
    RoomItemSchema,
    RoomUpdateRequest,
    ShortagesResponseData,
    WhyNotResponseData,
)
from app.schemas.common import Actor, DecisionCard, Envelope
from app.services.accommodation.service import (
    allocate_incremental,
    commit_plan_to_live,
    compare_plans,
    complete_room_cleaning,
    freeze_live_plan,
    generate_plans,
    get_decision_card,
    get_demand_timeline,
    get_live_plan,
    get_plan_by_id,
    get_plan_shortages,
    get_plans,
    get_properties,
    get_report_csv,
    get_rooms,
    get_why_not,
    manual_assign,
    repair_accommodation,
    update_property_resource,
    update_room_resource,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

router = APIRouter(prefix="/accommodation", tags=["Accommodation"])


# -----------------------------------------------------------------------------
# 1. Plan Generation
# -----------------------------------------------------------------------------
@router.post("/plans/generate", response_model=Envelope[PlansResponseData])
@router.post("/generate-plan", response_model=Envelope[PlansResponseData])
def generate_candidate_plans(
    body: GeneratePlanRequest,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Generate candidate accommodation plans (A, B, C) using pure staged allocation engine."""
    # Handle both request formats
    # `kind` is the legacy single-plan request. It must override the schema
    # default for `kinds`, otherwise {"kind": "A"} creates A/B/C.
    kinds = [body.kind] if body.kind else body.kinds

    params: Dict[str, Any] = {}
    if body.params:
        params = body.params.model_dump()
    else:
        if body.cleaning_buffer_minutes is not None:
            params["cleaning_buffer_minutes"] = body.cleaning_buffer_minutes
        if body.max_distance_km is not None:
            params["max_distance_km"] = body.max_distance_km
        if body.weights is not None:
            params["weights"] = body.weights

    plan_results = generate_plans(session=session, kinds=kinds, params=params)

    # Fetch stored plans
    plans, is_budget_unset, budget_val = get_plans(session)
    plan_schemas = [
        AccommodationPlanSchema(
            plan_id=p.plan_id,
            kind=p.kind,
            name=p.name,
            status=p.status,
            on_campus_placed=p.on_campus_placed,
            external_placed=p.external_placed,
            unplaced_count=p.unplaced_count,
            contingent_splits=p.contingent_splits,
            total_cost_inr=p.total_cost_inr,
            safety_flags_count=p.safety_flags_count,
            accessibility_issues_count=p.accessibility_issues_count,
            relaxed_constraints_count=p.relaxed_constraints_count,
            minors_external_count=p.minors_external_count,
            plan_hash=p.plan_hash,
            sacrifices_summary=p.sacrifices_summary,
            parameters_applied=json.loads(p.parameters_applied) if p.parameters_applied else {},
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in plans
        if p.kind in kinds
    ]

    warnings = []
    if is_budget_unset:
        warnings.append("external_budget_inr is UNSET (NULL). Engine running in budget-unset mode; cost thresholds flagged.")

    return Envelope(
        data=PlansResponseData(
            plans=plan_schemas,
            budget_ceiling_inr=budget_val,
            is_budget_unset=is_budget_unset,
        ),
        meta={"generated_count": len(plan_results)},
        warnings=warnings,
    )


# -----------------------------------------------------------------------------
# 2. Plan Retrieval & Compare
# -----------------------------------------------------------------------------
@router.get("/plans", response_model=Envelope[PlansResponseData])
def list_candidate_plans(
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Retrieve all candidate accommodation plans and budget status."""
    plans, is_budget_unset, budget_val = get_plans(session)

    plan_schemas = [
        AccommodationPlanSchema(
            plan_id=p.plan_id,
            kind=p.kind,
            name=p.name,
            status=p.status,
            on_campus_placed=p.on_campus_placed,
            external_placed=p.external_placed,
            unplaced_count=p.unplaced_count,
            contingent_splits=p.contingent_splits,
            total_cost_inr=p.total_cost_inr,
            safety_flags_count=p.safety_flags_count,
            accessibility_issues_count=p.accessibility_issues_count,
            relaxed_constraints_count=p.relaxed_constraints_count,
            minors_external_count=p.minors_external_count,
            plan_hash=p.plan_hash,
            sacrifices_summary=p.sacrifices_summary,
            parameters_applied=json.loads(p.parameters_applied) if p.parameters_applied else {},
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in plans
    ]

    warnings = []
    if is_budget_unset:
        warnings.append("Operating in Budget-Unset Mode: external_budget_inr = NULL.")

    return Envelope(
        data=PlansResponseData(
            plans=plan_schemas,
            budget_ceiling_inr=budget_val,
            is_budget_unset=is_budget_unset,
        ),
        meta={"total": len(plan_schemas)},
        warnings=warnings,
    )


@router.get("/plans/compare", response_model=Envelope[Dict[str, Any]])
def compare_candidate_plans(
    ids: Optional[str] = Query(None, description="Comma-separated plan IDs or kinds to compare (e.g. A,B,C)"),
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Side-by-side comparison of plan metrics, trade-offs, and plain-language sacrifices."""
    plan_ids_list = [i.strip() for i in ids.split(",") if i.strip()] if ids else None
    result = compare_plans(session=session, plan_ids=plan_ids_list)
    return Envelope(data=result)


# -----------------------------------------------------------------------------
# 3. Shortages & Why-Not Diagnoses
# -----------------------------------------------------------------------------
@router.get("/plans/{id}/shortages", response_model=Envelope[ShortagesResponseData])
@router.get("/shortages", response_model=Envelope[ShortagesResponseData])
def get_shortages(
    id: Optional[str] = None,
    plan_id: Optional[str] = Query(None),
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Retrieve unplaced participants grouped by the 7-item fixed blocking reason taxonomy."""
    target_id = id or plan_id
    result = get_plan_shortages(session=session, plan_id=target_id)
    return Envelope(data=result)


@router.get("/why-not/{participant_id}", response_model=Envelope[WhyNotResponseData])
def get_why_not_diagnosis(
    participant_id: str,
    plan_id: Optional[str] = Query(None),
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Explainable diagnostic panel detailing why a participant cannot be accommodated and counterfactuals."""
    diagnosis = get_why_not(session=session, participant_id=participant_id, plan_id=plan_id)
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant '{participant_id}' not found.",
        )
    return Envelope(data=diagnosis)


# -----------------------------------------------------------------------------
# 4. Bed-Demand Timeline
# -----------------------------------------------------------------------------
@router.get("/demand-timeline", response_model=Envelope[DemandTimelineResponseData])
def get_bed_demand_timeline_view(
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Bed-demand timeline evaluating rolling occupancy, confirmed demand, possible demand, and peak hour."""
    result = get_demand_timeline(session=session)

    timeline_points = [
        {
            "timestamp": pt.timestamp.isoformat(),
            "confirmed_demand": pt.confirmed_demand,
            "possible_demand": pt.possible_demand,
            "cleaning_beds": pt.cleaning_beds,
            "available_supply": pt.available_supply,
        }
        for pt in result.timeline
    ]

    warnings = []
    if result.peak_simultaneous_demand > 1450:
        warnings.append(
            f"Peak demand ({result.peak_simultaneous_demand}) exceeds total festival bed supply (1,450)."
        )

    return Envelope(
        data=DemandTimelineResponseData(
            total_participants_requesting=result.total_participants_requesting,
            valid_intervals_included=result.valid_intervals_included,
            invalid_intervals_count=result.invalid_intervals_count,
            invalid_intervals=result.invalid_intervals,
            confirmed_demand_count=result.confirmed_demand_count,
            possible_demand_count=result.possible_demand_count,
            peak_simultaneous_demand=result.peak_simultaneous_demand,
            peak_time=result.peak_time.isoformat() if result.peak_time else "",
            timeline=timeline_points,
        ),
        meta={"points_count": len(timeline_points)},
        warnings=warnings,
    )


# -----------------------------------------------------------------------------
# 5. Rooms and External Properties
# -----------------------------------------------------------------------------
@router.get("/rooms", response_model=Envelope[Dict[str, Any]])
def list_on_campus_rooms(
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """List on-campus rooms and beds with block, floor, accessibility, capacity, and cleaning status."""
    rooms = get_rooms(session)
    room_schemas = [
        RoomItemSchema(
            id=r.id,
            block=r.block,
            floor=r.floor,
            capacity=r.capacity,
            accessible=r.accessible,
            accessibility=r.accessibility,
            gender_class=r.gender_class,
            status=r.status,
            cleaning_status=r.cleaning_status,
            cleaning_ready_at=r.cleaning_ready_at.isoformat() if r.cleaning_ready_at else None,
        ).model_dump()
        for r in rooms
    ]

    accessible_rooms_count = sum(1 for r in rooms if r.accessible)
    accessible_beds_count = sum(r.capacity for r in rooms if r.accessible)

    return Envelope(
        data={
            "total_rooms": len(rooms),
            "total_beds": sum(r.capacity for r in rooms),
            "accessible_rooms": accessible_rooms_count,
            "accessible_beds": accessible_beds_count,
            "rooms": room_schemas,
        },
        meta={"total": len(rooms)},
    )


@router.get("/properties", response_model=Envelope[Dict[str, Any]])
def list_external_properties(
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """List external properties with beds, cost per bed-night, distance, transport availability, and verification flags."""
    properties = get_properties(session)
    prop_schemas = [
        PropertyItemSchema(
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
        ).model_dump()
        for p in properties
    ]

    return Envelope(
        data={
            "total_properties": len(properties),
            "total_beds": sum(p.beds for p in properties),
            "properties": prop_schemas,
        },
        meta={"total": len(properties)},
        warnings=["External property accessibility and gender suitability flags are UNVERIFIED."],
    )


# -----------------------------------------------------------------------------
# 6. Reports & Decision Cards
# -----------------------------------------------------------------------------
@router.get("/reports/{report_name}")
def download_accommodation_report(
    report_name: str,
    actor: Actor = Depends(require_permission("accommodation:export")),
    session: Session = Depends(get_session),
):
    """Download accommodation CSV reports (accommodation_plan_A/B/C.csv, shortage_report.csv, accommodation_summary.csv, bed_demand_timeline.csv)."""
    csv_content = get_report_csv(session=session, report_name=report_name)
    clean_filename = report_name if report_name.endswith(".csv") else f"{report_name}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={clean_filename}"},
    )


@router.get("/decision-cards/{plan_id}", response_model=Envelope[DecisionCard])
def get_plan_decision_card(
    plan_id: str,
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Get structured DecisionCard for a plan."""
    card = get_decision_card(session=session, plan_id=plan_id)
    return Envelope(data=card)


# -----------------------------------------------------------------------------
# 7. Live Plan & Approvals
# -----------------------------------------------------------------------------
@router.post("/plans/{id}/commit", response_model=Envelope[Dict[str, Any]])
def commit_candidate_plan_endpoint(
    id: str,
    body: Optional[CommitPlanRequest] = None,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Commit candidate plan to LIVE via approvals workflow."""
    reason = body.reason if body else "Commit candidate plan to LIVE"
    override_budget = body.override_budget_rationale if body else None
    result = commit_plan_to_live(
        session=session,
        plan_id=id,
        actor=actor,
        reason=reason,
        override_budget_rationale=override_budget,
    )
    if result.get("status") == "PENDING_APPROVAL":
        return Envelope(
            data=result,
            meta={"requires_director_approval": True, "approval_id": result.get("change_set_id")},
            warnings=["High-risk plan commit requires Festival Director sign-off."],
        )
    return Envelope(data=result)


@router.get("/plans/live", response_model=Envelope[Dict[str, Any]])
def get_live_plan_endpoint(
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Retrieve the currently operational LIVE accommodation plan."""
    live = get_live_plan(session)
    if not live:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No LIVE plan currently active.")
    return Envelope(
        data={
            "plan_id": live.plan_id,
            "kind": live.kind,
            "name": live.name,
            "status": live.status,
            "is_frozen": live.is_frozen,
            "frozen_at": live.frozen_at.isoformat() if live.frozen_at else None,
            "on_campus_placed": live.on_campus_placed,
            "external_placed": live.external_placed,
            "total_cost_inr": live.total_cost_inr,
            "contingent_splits": live.contingent_splits,
        }
    )


@router.get("/plans/{id}", response_model=Envelope[Dict[str, Any]])
def get_plan_detail(
    id: str,
    actor: Actor = Depends(require_permission("accommodation:read")),
    session: Session = Depends(get_session),
):
    """Retrieve details, metrics, and parameters of a specific candidate plan."""
    plan = get_plan_by_id(session, id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{id}' not found.")
    return Envelope(data={
        "plan_id": plan.plan_id, "kind": plan.kind, "status": plan.status,
        "name": plan.name,
        "metrics": {key: getattr(plan, key) for key in (
            "on_campus_placed", "external_placed", "unplaced_count", "contingent_splits",
            "total_cost_inr", "safety_flags_count", "accessibility_issues_count",
            "relaxed_constraints_count", "minors_external_count")},
        "plan_hash": plan.plan_hash, "sacrifices_summary": plan.sacrifices_summary,
        "parameters_applied": json.loads(plan.parameters_applied) if plan.parameters_applied else {},
        "created_at": plan.created_at.isoformat() if plan.created_at else "",
    })


@router.post("/plans/live/freeze", response_model=Envelope[Dict[str, Any]])
def freeze_live_plan_endpoint(
    body: Optional[FreezePlanRequest] = None,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Freeze LIVE plan allocations ahead of festival commencement."""
    reason = body.reason if body else "Lock allocations"
    res = freeze_live_plan(session=session, actor=actor, reason=reason)
    return Envelope(data=res)


@router.post("/plans/live/allocate-incremental", response_model=Envelope[Dict[str, Any]])
def allocate_incremental_endpoint(
    body: Optional[IncrementalAllocateRequest] = None,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Incrementally allocate late arrivals while preserving all approved assignments."""
    p_ids = body.participant_ids if body else None
    c_id = body.contingent_id if body else None
    result = allocate_incremental(session=session, participant_ids=p_ids, contingent_id=c_id, actor=actor)
    return Envelope(data=result)


# -----------------------------------------------------------------------------
# 8. Operational Resource Management & Cleaning
# -----------------------------------------------------------------------------
@router.patch("/rooms/{id}", response_model=Envelope[Dict[str, Any]])
def update_room_endpoint(
    id: str,
    body: RoomUpdateRequest,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Update room operational status, cleaning, or accessibility attributes via ChangeService."""
    payload = body.model_dump(exclude_unset=True, exclude={"expected_version", "reason"})
    res = update_room_resource(
        session=session,
        room_id=id,
        payload=payload,
        actor=actor,
        reason=body.reason,
        expected_version=body.expected_version,
    )
    return Envelope(data=res.data, meta={"change_set_id": res.change_set_id})


@router.post("/rooms/{id}/cleaning-complete", response_model=Envelope[Dict[str, Any]])
def complete_cleaning_endpoint(
    id: str,
    body: Optional[CleaningCompleteRequest] = None,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Mark housekeeping inspection complete, transitioning room status to READY."""
    notes = body.notes if body else "Cleaning complete"
    exp_v = body.expected_version if body else None
    res = complete_room_cleaning(
        session=session,
        room_id=id,
        actor=actor,
        notes=notes,
        expected_version=exp_v,
    )
    return Envelope(data=res.data, meta={"change_set_id": res.change_set_id})


@router.patch("/properties/{id}", response_model=Envelope[Dict[str, Any]])
def update_property_endpoint(
    id: str,
    body: PropertyUpdateRequest,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Update external property pricing, transport windows, and verification flags via ChangeService."""
    payload = body.model_dump(exclude_unset=True, exclude={"expected_version", "reason"})
    res = update_property_resource(
        session=session,
        property_id=id,
        payload=payload,
        actor=actor,
        reason=body.reason,
        expected_version=body.expected_version,
    )
    return Envelope(data=res.data, meta={"change_set_id": res.change_set_id})


# -----------------------------------------------------------------------------
# 9. Manual Assignment & Minimal-Change Repair
# -----------------------------------------------------------------------------
@router.post("/assignments/manual", response_model=Envelope[Dict[str, Any]])
def manual_assignment_endpoint(
    body: ManualAssignRequest,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Manually assign or move participant with mandatory reason and Director override enforcement."""
    res = manual_assign(session=session, req=body, actor=actor)
    return Envelope(data=res)


@router.post("/repair", response_model=Envelope[Dict[str, Any]])
def repair_accommodation_endpoint(
    body: RepairPlanRequest,
    actor: Actor = Depends(require_permission("accommodation:write")),
    session: Session = Depends(get_session),
):
    """Minimal-change repair engine: re-plans displaced participants while preserving unaffected stays."""
    diff = repair_accommodation(session=session, req=body)
    return Envelope(data=diff)

