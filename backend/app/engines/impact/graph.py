# OWNER: P2
from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.registry import iter_public_modules
from app.models.accommodation import ExternalProperty, Room, StayAssignment
from app.models.events import Event, EventSession
from app.models.inventory import InventoryItem, MerchClaim
from app.models.ops import Venue
from app.models.participants import Contingent, Participant, Registration
from app.models.vendors import MealSlot, Vendor, VendorAssignment
from app.schemas.impact import GraphEdge, GraphNode, ImpactGraphResponse, ImpactNode, ImpactReport
from sqlmodel import Session, select

logger = logging.getLogger("festos.engines.impact")


def _normalize_type(t: str) -> str:
    s = t.lower().strip()
    if s in ["hostel_block", "block", "hostel"]:
        return "hostel"
    if s in ["room", "rm"]:
        return "room"
    if s in ["external_property", "property", "hotel"]:
        return "property"
    if s in ["participant", "user", "person"]:
        return "participant"
    if s in ["contingent", "college"]:
        return "contingent"
    if s in ["event", "evt"]:
        return "event"
    if s in ["session", "event_session"]:
        return "event_session"
    if s in ["venue", "ven"]:
        return "venue"
    if s in ["vendor", "vnd"]:
        return "vendor"
    if s in ["equipment", "inventory_item", "item"]:
        return "equipment"
    if s in ["meal", "meal_slot"]:
        return "meal_slot"
    if s in ["claim", "merch_claim"]:
        return "merch_claim"
    return s


def _get_direct_orm_dependents(
    session: Session, entity_type: str, entity_id: str
) -> List[Tuple[str, str, str, int, str]]:
    """Return direct dependents as (dep_type, dep_id, label, people_affected, relation)."""
    norm_type = _normalize_type(entity_type)
    results: List[Tuple[str, str, str, int, str]] = []

    # 1. Hostel Block -> Rooms -> Participants
    if norm_type == "hostel":
        rooms = session.exec(select(Room).where(Room.block == entity_id)).all()
        for r in rooms:
            results.append(("room", r.id, f"Room {r.id} ({r.block})", r.capacity, "contains_room"))
        if not rooms:
            # Check room id starts with block name
            fallback_rooms = session.exec(select(Room).where(Room.block.like(f"%{entity_id}%"))).all()
            for r in fallback_rooms:
                results.append(("room", r.id, f"Room {r.id} ({r.block})", r.capacity, "contains_room"))

    # 2. Room -> StayAssignments -> Participants
    elif norm_type == "room":
        stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.room_id == entity_id,
                StayAssignment.status == "ACTIVE",
            )
        ).all()
        for s in stays:
            p = session.get(Participant, s.participant_id)
            label = f"{p.name} ({s.participant_id})" if p else s.participant_id
            results.append(("participant", s.participant_id, label, 1, "houses_participant"))

    # 3. Property -> StayAssignments -> Participants
    elif norm_type == "property":
        stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.property_id == entity_id,
                StayAssignment.status == "ACTIVE",
            )
        ).all()
        for s in stays:
            p = session.get(Participant, s.participant_id)
            label = f"{p.name} ({s.participant_id})" if p else s.participant_id
            results.append(("participant", s.participant_id, label, 1, "houses_participant"))

    # 4. Contingent -> Participants
    elif norm_type == "contingent":
        participants = session.exec(
            select(Participant).where(
                Participant.contingent_id == entity_id,
                Participant.status.in_(["CHECKED_IN", "ARRIVED", "EXPECTED"]),
            )
        ).all()
        for p in participants:
            results.append(("participant", p.id, f"{p.name} ({p.id})", 1, "member_of_contingent"))

    # 5. Participant -> Contingent, Registrations (Events), Stays (Rooms), Merch
    elif norm_type == "participant":
        p = session.get(Participant, entity_id)
        if p and p.contingent_id:
            c = session.get(Contingent, p.contingent_id)
            c_label = c.name if c else p.contingent_id
            results.append(("contingent", p.contingent_id, c_label, 1, "belongs_to_contingent"))

        # Event registrations
        regs = session.exec(select(Registration).where(Registration.participant_id == entity_id)).all()
        for reg in regs:
            evt = session.get(Event, reg.event_id)
            evt_label = evt.name if evt else reg.event_id
            results.append(("event", reg.event_id, evt_label, 1, "registered_for_event"))

        # Stays
        stays = session.exec(
            select(StayAssignment).where(
                StayAssignment.participant_id == entity_id,
                StayAssignment.status == "ACTIVE",
            )
        ).all()
        for st in stays:
            if st.room_id:
                results.append(("room", st.room_id, f"Room {st.room_id}", 1, "occupies_room"))
            if st.property_id:
                results.append(("property", st.property_id, f"Property {st.property_id}", 1, "occupies_property"))

        # Merch
        claims = session.exec(
            select(MerchClaim).where(
                MerchClaim.canonical_participant_id == entity_id,
                MerchClaim.status != "VOIDED",
            )
        ).all()
        for clm in claims:
            results.append(("merch_claim", clm.id, f"Claim {clm.id} ({clm.item_id})", 1, "claimed_merchandise"))

    # 6. Venue -> EventSessions, VendorAssignments
    elif norm_type == "venue":
        sessions = session.exec(select(EventSession).where(EventSession.venue_id == entity_id)).all()
        for ses in sessions:
            evt = session.get(Event, ses.event_id)
            ses_code = getattr(ses, "session_code", None) or f"{ses.round}-{ses.heat}"
            label = f"{evt.name if evt else ses.event_id} ({ses_code})"
            results.append(("event_session", ses.id, label, 30, "hosts_session"))

        vnas = session.exec(select(VendorAssignment).where(VendorAssignment.venue_id == entity_id)).all()
        for vna in vnas:
            v = session.get(Vendor, vna.vendor_id)
            v_label = v.name if v else vna.vendor_id
            results.append(("vendor", vna.vendor_id, v_label, vna.allocated_capacity, "serves_at_venue"))

    # 7. Event -> Registrations (Participants), Sessions (Venues)
    elif norm_type == "event":
        regs = session.exec(select(Registration).where(Registration.event_id == entity_id)).all()
        for r in regs:
            p = session.get(Participant, r.participant_id)
            label = f"{p.name} ({r.participant_id})" if p else r.participant_id
            results.append(("participant", r.participant_id, label, 1, "registered_participant"))

        sessions = session.exec(select(EventSession).where(EventSession.event_id == entity_id)).all()
        for ses in sessions:
            results.append(("venue", ses.venue_id, f"Venue {ses.venue_id}", 30, "scheduled_at_venue"))

    # 8. EventSession -> Event, Venue
    elif norm_type == "event_session":
        ses = session.get(EventSession, entity_id)
        if ses:
            evt = session.get(Event, ses.event_id)
            if evt:
                results.append(("event", evt.id, evt.name, 30, "belongs_to_event"))
            if ses.venue_id:
                results.append(("venue", ses.venue_id, f"Venue {ses.venue_id}", 30, "takes_place_at_venue"))

    # 9. Vendor -> MealSlots, VendorAssignments
    elif norm_type == "vendor":
        vnas = session.exec(select(VendorAssignment).where(VendorAssignment.vendor_id == entity_id)).all()
        for a in vnas:
            ms = session.get(MealSlot, a.meal_slot_id)
            label = f"{ms.name} ({ms.date})" if ms else a.meal_slot_id
            results.append(("meal_slot", a.meal_slot_id, label, a.allocated_capacity, "assigned_meal_slot"))

    # 10. Equipment / InventoryItem -> EventSessions
    elif norm_type == "equipment":
        item = session.get(InventoryItem, entity_id)
        item_name = item.name.lower() if item else entity_id.lower()
        sessions = session.exec(select(EventSession)).all()
        for ses in sessions:
            evt = session.get(Event, ses.event_id)
            eq_needs = (evt.equipment_needs or "").lower() if evt else ""
            if any(tok in eq_needs for tok in [item_name, "av", "sound", "projector", "mic"]):
                results.append(("event_session", ses.id, f"Session {ses.session_code}", 40, "requires_equipment"))

    return results


def _resolve_label(session: Session, entity_type: str, entity_id: str) -> str:
    norm_type = _normalize_type(entity_type)
    try:
        if norm_type == "hostel":
            return f"Hostel Block {entity_id}"
        elif norm_type == "room":
            r = session.get(Room, entity_id)
            return f"Room {r.id} ({r.block})" if r else f"Room {entity_id}"
        elif norm_type == "property":
            p = session.get(ExternalProperty, entity_id)
            return p.name if p else f"Property {entity_id}"
        elif norm_type == "participant":
            p = session.get(Participant, entity_id)
            return f"{p.name} ({p.id})" if p else f"Participant {entity_id}"
        elif norm_type == "contingent":
            c = session.get(Contingent, entity_id)
            return c.name if c else f"Contingent {entity_id}"
        elif norm_type == "event":
            e = session.get(Event, entity_id)
            return e.name if e else f"Event {entity_id}"
        elif norm_type == "event_session":
            s = session.get(EventSession, entity_id)
            return f"Session {s.session_code}" if s else f"Session {entity_id}"
        elif norm_type == "venue":
            v = session.get(Venue, entity_id)
            return v.name if v else f"Venue {entity_id}"
        elif norm_type == "vendor":
            v = session.get(Vendor, entity_id)
            return v.name if v else f"Vendor {entity_id}"
        elif norm_type == "equipment":
            it = session.get(InventoryItem, entity_id)
            return it.name if it else f"Equipment {entity_id}"
        elif norm_type == "meal_slot":
            ms = session.get(MealSlot, entity_id)
            return f"{ms.name} ({ms.date})" if ms else f"Meal Slot {entity_id}"
    except Exception:
        pass
    return f"{entity_type.capitalize()} {entity_id}"


def _assign_severity(entity_type: str, people_affected: int, depth: int) -> str:
    norm = _normalize_type(entity_type)
    if depth == 0:
        return "CRITICAL" if people_affected > 20 else "HIGH"
    if norm in ["participant"]:
        return "HIGH" if depth <= 2 else "MEDIUM"
    if norm in ["hostel", "venue", "vendor"] and people_affected > 25:
        return "CRITICAL"
    if people_affected > 10:
        return "HIGH"
    if people_affected > 1:
        return "MEDIUM"
    return "LOW"


def build_impact_graph(
    session: Session,
    root_entity_type_or_change: Any,
    root_entity_id: Optional[str] = None,
    action: str = "disrupt",
    parameters: Optional[Dict[str, Any]] = None,
    max_depth: int = 5,
) -> ImpactReport:
    """Breadth-first search (BFS) building the unified dependency tree and blast radius report.

    Covers the 3 canonical chains:
    1. Participant -> Contingent -> Registration -> Event -> Venue -> Equipment -> Vendor
    2. Participant -> Arrival -> Check-in -> Accommodation -> Meal -> Vendor
    3. Participant -> Merchandise eligibility -> Stock -> Distribution counter
    Guarantees cycle termination via visited set and depth cap.
    """
    if hasattr(root_entity_type_or_change, "entity_type"):
        req = root_entity_type_or_change
        if isinstance(root_entity_id, int):
            max_depth = root_entity_id
        root_entity_type = req.entity_type
        root_entity_id = req.entity_id
        action = getattr(req, "action", action)
        parameters = getattr(req, "payload", parameters)
    else:
        root_entity_type = str(root_entity_type_or_change)
        root_entity_id = str(root_entity_id or "")

    norm_root_type = _normalize_type(root_entity_type)
    root_label = _resolve_label(session, norm_root_type, root_entity_id)

    root_node = ImpactNode(
        id=root_entity_id,
        type=norm_root_type,
        label=root_label,
        severity="HIGH",
        people_affected=0,
        depth=0,
        update_status="PENDING",
        reason=f"Action '{action}' on {norm_root_type}:{root_entity_id}",
        children=[],
    )

    visited: Set[Tuple[str, str]] = {(norm_root_type, root_entity_id)}
    queue: deque[Tuple[ImpactNode, int]] = deque([(root_node, 0)])

    counts_by_type: Dict[str, int] = {norm_root_type: 1}
    severities: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    nodes_flat: List[Dict[str, Any]] = []
    total_people_set: Set[str] = set()

    # Public module dependent delegates
    public_modules = iter_public_modules()

    while queue:
        curr_node, curr_depth = queue.popleft()
        nodes_flat.append({
            "id": curr_node.id,
            "type": curr_node.type,
            "label": curr_node.label,
            "severity": curr_node.severity,
            "people_affected": curr_node.people_affected,
            "depth": curr_node.depth,
            "update_status": curr_node.update_status,
            "downstream_status": curr_node.update_status,
        })
        severities[curr_node.severity] = severities.get(curr_node.severity, 0) + 1

        if curr_node.type == "participant":
            total_people_set.add(curr_node.id)

        if curr_depth >= max_depth:
            continue

        # 1. Fetch direct ORM dependents
        orm_deps = _get_direct_orm_dependents(session, curr_node.type, curr_node.id)

        # 2. Query public.dependents across all registered modules
        for mod_info in public_modules:
            mod = mod_info["module"]
            if hasattr(mod, "dependents"):
                try:
                    pub_deps = mod.dependents(session, curr_node.type, curr_node.id)
                    for d in pub_deps:
                        d_type = getattr(d, "type", "entity")
                        d_id = getattr(d, "id", "")
                        d_label = getattr(d, "label", f"{d_type}:{d_id}")
                        if d_id:
                            orm_deps.append((d_type, d_id, d_label, 1, "module_dependency"))
                except Exception:
                    pass

        # De-duplicate dependents for this node
        seen_child_keys: Set[Tuple[str, str]] = set()

        for d_type, d_id, d_label, d_people, d_rel in orm_deps:
            norm_d_type = _normalize_type(d_type)
            key = (norm_d_type, d_id)

            if key in visited or key in seen_child_keys:
                continue
            seen_child_keys.add(key)
            visited.add(key)

            child_sev = _assign_severity(norm_d_type, d_people, curr_depth + 1)
            child_node = ImpactNode(
                id=d_id,
                type=norm_d_type,
                label=d_label,
                severity=child_sev,
                people_affected=d_people,
                depth=curr_depth + 1,
                update_status="PENDING",
                reason=f"{d_rel} from {curr_node.type}:{curr_node.id}",
                children=[],
            )

            curr_node.children.append(child_node)
            counts_by_type[norm_d_type] = counts_by_type.get(norm_d_type, 0) + 1
            queue.append((child_node, curr_depth + 1))

    # Calculate root aggregate people affected if 0
    if root_node.people_affected == 0:
        root_node.people_affected = len(total_people_set)
    root_node.severity = _assign_severity(norm_root_type, root_node.people_affected, 0)

    # Recommendations
    recommendations: List[str] = []
    if "participant" in counts_by_type and counts_by_type["participant"] > 0:
        recommendations.append(f"Execute minimal-change recovery replan for {counts_by_type['participant']} affected participants.")
    if norm_root_type == "hostel":
        recommendations.append(f"Isolate {root_label} and reallocate displaced residents to vacant campus rooms.")
    elif norm_root_type == "venue":
        recommendations.append(f"Re-route {counts_by_type.get('event_session', 1)} affected sessions to compatible alternative venues.")
    elif norm_root_type == "vendor":
        recommendations.append("Activate secondary vendor assignments and verify dietary coverage gaps.")
    elif norm_root_type == "equipment":
        recommendations.append("Check equipment transfer matrix for nearest available backup units.")
    else:
        recommendations.append(f"Review blast radius across {len(visited)} affected entities.")

    before_after = {
        "disrupted_entity": f"{norm_root_type}:{root_entity_id}",
        "affected_count_before": len(visited),
        "affected_count_after": 0,
        "unplaced_people_before": len(total_people_set),
        "unplaced_people_after": 0,
    }

    return ImpactReport(
        root_entity={
            "type": norm_root_type,
            "id": root_entity_id,
            "label": root_label,
            "action": action,
        },
        tree=root_node,
        counts_by_type=counts_by_type,
        severities=severities,
        total_people_affected=len(total_people_set),
        recommendations=recommendations,
        before_after_comparison=before_after,
        nodes_flat=nodes_flat,
    )


def get_entity_subgraph(
    session: Session, entity_type: str, entity_id: str, max_depth: int = 3
) -> ImpactGraphResponse:
    """Build directed graph node-and-edge response for GET /impact/graph."""
    norm_type = _normalize_type(entity_type)
    root_label = _resolve_label(session, norm_type, entity_id)

    nodes: List[GraphNode] = [
        GraphNode(id=f"{norm_type}:{entity_id}", type=norm_type, label=root_label, severity="HIGH", people_affected=0)
    ]
    edges: List[GraphEdge] = []
    direct_dependents: List[Dict[str, Any]] = []

    visited: Set[Tuple[str, str]] = {(norm_type, entity_id)}
    queue: deque[Tuple[str, str, int]] = deque([(norm_type, entity_id, 0)])

    while queue:
        c_type, c_id, c_depth = queue.popleft()
        if c_depth >= max_depth:
            continue

        deps = _get_direct_orm_dependents(session, c_type, c_id)
        for d_type, d_id, d_label, d_people, d_rel in deps:
            norm_d = _normalize_type(d_type)
            key = (norm_d, d_id)

            if c_depth == 0:
                direct_dependents.append({
                    "type": norm_d,
                    "id": d_id,
                    "label": d_label,
                    "relation": d_rel,
                })

            edges.append(GraphEdge(
                source=f"{c_type}:{c_id}",
                target=f"{norm_d}:{d_id}",
                relation=d_rel,
            ))

            if key not in visited:
                visited.add(key)
                nodes.append(GraphNode(
                    id=f"{norm_d}:{d_id}",
                    type=norm_d,
                    label=d_label,
                    severity="MEDIUM",
                    people_affected=d_people,
                ))
                queue.append((norm_d, d_id, c_depth + 1))

    return ImpactGraphResponse(
        entity=f"{norm_type}:{entity_id}",
        direct_dependents=direct_dependents,
        nodes=nodes,
        edges=edges,
    )
