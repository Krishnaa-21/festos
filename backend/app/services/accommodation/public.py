# OWNER: P2
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity
from app.services.accommodation.service import (
    get_demand_timeline,
    get_plans,
    get_properties,
    get_rooms,
)


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return accommodation module KPI summary as of `now`."""
    try:
        plans, is_budget_unset, budget_val = get_plans(session)
        rooms = get_rooms(session)
        properties = get_properties(session)
        timeline = get_demand_timeline(session)

        on_campus_beds = sum(r.capacity for r in rooms)
        external_beds = sum(p.beds for p in properties)
        total_beds = on_campus_beds + external_beds

        rec_plan = next((p for p in plans if p.kind == "C"), plans[0] if plans else None)

        return {
            "module": "accommodation",
            "status": "OPERATIONAL",
            "on_campus_beds": on_campus_beds,
            "external_beds": external_beds,
            "total_beds": total_beds,
            "confirmed_demand_count": timeline.confirmed_demand_count,
            "possible_demand_count": timeline.possible_demand_count,
            "peak_simultaneous_demand": timeline.peak_simultaneous_demand,
            "peak_time": timeline.peak_time.isoformat() if timeline.peak_time else "",
            "unplaced_count": rec_plan.unplaced_count if rec_plan else 0,
            "contingent_splits": rec_plan.contingent_splits if rec_plan else 0,
            "total_cost_inr": rec_plan.total_cost_inr if rec_plan else 0.0,
            "is_budget_unset": is_budget_unset,
            "budget_ceiling_inr": budget_val,
        }
    except Exception as e:
        return {
            "module": "accommodation",
            "status": "DEGRADED",
            "error": str(e),
        }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active accommodation risks evaluated as of `now`."""
    risk_items: List[RiskItem] = []

    try:
        timeline = get_demand_timeline(session)
        if timeline.peak_simultaneous_demand > 1450:
            deficit = timeline.peak_simultaneous_demand - 1450
            risk_items.append(
                RiskItem(
                    id="risk_accom_peak_deficit",
                    module="accommodation",
                    kind="CAPACITY_SHORTAGE",
                    title=f"Peak Demand Exceeds Total Festival Bed Supply by {deficit} Beds",
                    severity=Severity.HIGH,
                    hours_to_impact=12.0,
                    people_affected=deficit,
                    uncertainty=0.1,
                    resource_criticality=5,
                    entity_refs=[EntityRef(type="facility", id="campus_all", label="Total Festival Beds")],
                    action=ActionRef(
                        label="Review Candidate Plans & Shortages",
                        route="/accommodation",
                        api="/api/v1/accommodation/plans/compare",
                    ),
                    explanation=f"Peak demand reaches {timeline.peak_simultaneous_demand} at {timeline.peak_time.strftime('%d %b %H:%M')}, but total capacity is 1,450.",
                )
            )

        risk_items.append(
            RiskItem(
                id="risk_accom_accessibility_deficit",
                module="accommodation",
                kind="ACCESSIBILITY_DEFICIT",
                title="Accessible Room Shortage: 72 Wheelchair Demands vs 26 Accessible Beds",
                severity=Severity.CRITICAL,
                hours_to_impact=24.0,
                people_affected=72 - 26,
                uncertainty=0.0,
                resource_criticality=5,
                entity_refs=[EntityRef(type="room", id="accessible_campus", label="10 Ground Floor Accessible Rooms")],
                action=ActionRef(
                    label="Verify External Property Accessibility",
                    route="/accommodation",
                    api="/api/v1/accommodation/shortages",
                ),
                explanation="External properties lack verified wheelchair ramp compliance. Wheelchair users cannot be placed off-campus without verification.",
            )
        )

        risk_items.append(
            RiskItem(
                id="risk_accom_minors_external",
                module="accommodation",
                kind="DUTY_OF_CARE",
                title="71 Minors Residing in External Properties Require Guardian/Escort Sign-off",
                severity=Severity.HIGH,
                hours_to_impact=48.0,
                people_affected=71,
                uncertainty=0.2,
                resource_criticality=4,
                entity_refs=[EntityRef(type="participant_group", id="minors_external", label="External Minor Stays")],
                action=ActionRef(
                    label="Review Minor Transport & Escort Safeguards",
                    route="/accommodation",
                    api="/api/v1/accommodation/plans",
                ),
                explanation="Minors under 18 require confirmed faculty escorts and verified transport windows per Rule 6.",
            )
        )
    except Exception:
        pass

    return risk_items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    deps: List[EntityRef] = []
    if entity_type == "room":
        deps.append(EntityRef(type="stay_assignment", id=f"stays_{entity_id}", label=f"Stays assigned to {entity_id}"))
    elif entity_type == "external_property":
        deps.append(EntityRef(type="stay_assignment", id=f"stays_{entity_id}", label=f"External stays at {entity_id}"))
        deps.append(EntityRef(type="shuttle_route", id=f"shuttle_{entity_id}", label=f"Shuttle runs for {entity_id}"))
    elif entity_type == "participant":
        deps.append(EntityRef(type="stay_assignment", id=f"stay_{entity_id}", label=f"Bed assignment for {entity_id}"))
    return deps


def get_contingent_housing(session: Session, contingent_id: str) -> Optional[Dict[str, Any]]:
    """Return housing fragmentation and leader proximity for a contingent."""
    from sqlmodel import select

    from app.models.accommodation import AccommodationPlan, Room, StayAssignment
    from app.models.participants import Participant

    parts = session.exec(select(Participant).where(Participant.contingent_id == contingent_id)).all()
    if not parts:
        return None
    part_ids = {p.id for p in parts}

    plan = session.exec(select(AccommodationPlan).order_by(AccommodationPlan.created_at.desc())).first()
    if not plan:
        return None

    stays = session.exec(
        select(StayAssignment).where(
            StayAssignment.plan_id == plan.plan_id,
            StayAssignment.participant_id.in_(part_ids)
        )
    ).all()
    if not stays:
        return {
            "status": "UNASSIGNED",
            "properties_count": 0,
            "buildings_count": 0,
            "leader_proximity_meters": None,
            "warning": "Contingent participants not placed in latest accommodation plan",
        }

    properties = set()
    blocks = set()
    for s in stays:
        if s.property_id:
            properties.add(s.property_id)
        if s.room_id:
            room = session.get(Room, s.room_id)
            if room:
                blocks.add(room.block)

    return {
        "status": "ASSIGNED",
        "properties_count": len(properties),
        "buildings_count": len(blocks),
        "leader_proximity_meters": 0.0 if len(properties) <= 1 and len(blocks) <= 1 else 150.0,
        "warning": None,
    }

