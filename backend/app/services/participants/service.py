# OWNER: P1
"""Service layer for Participants and Participant 360 view."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, func, select

from app.core.masking import mask_sensitive_fields
from app.core.registry import get_participant_sections
from app.models.audit import AuditEvent
from app.models.events import Event
from app.models.inventory import MerchClaim
from app.models.participants import Contingent, FieldVerification, Participant, Registration
from app.services.participants.handlers import ALLOWED_TRANSITIONS


def list_participants(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    sort: str = "name",
    q: Optional[str] = None,
    contingent_id: Optional[str] = None,
    status: Optional[str] = None,
    event_id: Optional[str] = None,
    diet: Optional[str] = None,
    accessibility: Optional[str] = None,
    unknown_field: Optional[str] = None,
    role: Optional[str] = None,
    arrival_window_start: Optional[datetime] = None,
    arrival_window_end: Optional[datetime] = None,
    actor_role: str = "VOLUNTEER",
) -> Dict[str, Any]:
    """Lists participants with comprehensive filtering, fuzzy search, and pagination."""
    query = select(Participant)

    if q:
        q_term = f"%{q.strip().lower()}%"
        query = query.where(func.lower(Participant.name).like(q_term) | func.lower(Participant.college).like(q_term))

    if contingent_id:
        query = query.where(Participant.contingent_id == contingent_id)

    if status:
        query = query.where(Participant.status == status)

    if diet:
        query = query.where(Participant.diet == diet)

    if role:
        query = query.where(Participant.role == role)

    if arrival_window_start:
        query = query.where(Participant.arrival_at >= arrival_window_start)

    if arrival_window_end:
        query = query.where(Participant.arrival_at <= arrival_window_end)

    if unknown_field:
        if hasattr(Participant, unknown_field):
            query = query.where(getattr(Participant, unknown_field) == "UNKNOWN")

    if event_id:
        # Join with registration
        query = query.join(Registration, Registration.participant_id == Participant.id).where(Registration.event_id == event_id)

    # Sorting
    descending = sort.startswith("-")
    sort_field = sort[1:] if descending else sort
    if hasattr(Participant, sort_field):
        col = getattr(Participant, sort_field)
        query = query.order_by(col.desc() if descending else col.asc())
    else:
        query = query.order_by(Participant.name.asc())

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    participants = session.exec(query).all()

    items = []
    for p in participants:
        p_dict = p.model_dump()
        items.append(mask_sensitive_fields(p_dict, actor_role))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_participant(session: Session, participant_id: str, actor_role: str = "VOLUNTEER") -> Optional[Dict[str, Any]]:
    """Retrieve a single participant record by ID with role-based field masking."""
    p = session.get(Participant, participant_id)
    if not p:
        return None
    return mask_sensitive_fields(p.model_dump(), actor_role)


def get_participant_360(session: Session, participant_id: str, actor_role: str = "VOLUNTEER") -> Optional[Dict[str, Any]]:
    """Aggregates all participant facets into a 360-degree operational view.

    Includes contingent details, events/registrations, diet, accessibility, merch status,
    operational lifecycle, and pluggable section hooks registered via register_participant_section.
    """
    p = session.get(Participant, participant_id)
    if not p:
        return None

    # 1. Contingent details
    contingent_info: Dict[str, Any] = {}
    if p.contingent_id:
        c = session.get(Contingent, p.contingent_id)
        if c:
            # Check if leader/escort found
            leader_match = session.exec(
                select(Participant).where(Participant.contingent_id == c.id, Participant.name == c.leader)
            ).first()
            escort_match = session.exec(
                select(Participant).where(Participant.contingent_id == c.id, Participant.name == c.escort)
            ).first()

            contingent_info = {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "college": c.college,
                "leader_name": c.leader,
                "leader_found": leader_match is not None,
                "escort_name": c.escort,
                "escort_found": escort_match is not None,
                "contact_phone": c.contact_phone,
            }

    # 2. Registrations and Events
    regs = session.exec(select(Registration).where(Registration.participant_id == p.id)).all()
    registrations_list = []
    for r in regs:
        event = session.get(Event, r.event_id)
        registrations_list.append({
            "registration_id": r.id,
            "event_id": r.event_id,
            "event_name": event.name if event else r.event_id,
            "team_id": r.team_id,
            "status": r.status,
            "registered_at": r.registered_at.isoformat() if r.registered_at else None,
        })

    # 3. Dietary info & verifications
    diet_verifications = session.exec(
        select(FieldVerification).where(
            FieldVerification.entity_type == "participant",
            FieldVerification.entity_id == p.id,
            FieldVerification.field == "diet",
        )
    ).all()
    diet_info = {
        "preference": p.diet,
        "status": "VERIFIED" if any(v.status == "VERIFIED" for v in diet_verifications) else ("UNKNOWN" if p.diet == "UNKNOWN" else "CLAIMED"),
        "verification_history": [
            {
                "status": v.status,
                "value": v.value,
                "source": v.source,
                "verified_by": v.verified_by,
                "verified_at": v.verified_at.isoformat() if v.verified_at else None,
            }
            for v in diet_verifications
        ],
    }

    # 4. Accessibility
    access_needs = p.accessibility_needs or {}
    accessibility_info = {
        "needs": access_needs,
        "has_need": bool(access_needs.get("has_need")),
        "requires_ground_floor": bool(access_needs.get("requires_ground_floor")),
        "requires_wheelchair": bool(access_needs.get("requires_wheelchair")),
        "visual_assistance": bool(access_needs.get("visual_assistance")),
    }

    # 5. Merchandise claims
    claims = session.exec(
        select(MerchClaim).where(MerchClaim.canonical_participant_id == p.id)
    ).all()
    merchandise_info = {
        "tshirt_size": p.tshirt_size,
        "entitlement": "FULFILLED" if claims else "PENDING",
        "claims": [
            {
                "claim_id": c.id,
                "item_id": c.item_id,
                "claimed_at": c.claimed_at.isoformat() if hasattr(c, "claimed_at") and c.claimed_at else None,
            }
            for c in claims
        ],
    }

    # 6. Operational Status
    allowed = list(ALLOWED_TRANSITIONS.get(p.status, []))
    operational_info = {
        "current_status": p.status,
        "can_transition_to": allowed,
        "last_updated": p.updated_at.isoformat() if p.updated_at else None,
    }

    # 7. Dynamic sections registered through register_participant_section
    dynamic_sections: Dict[str, Any] = {}
    for section_name, provider_fn in get_participant_sections().items():
        try:
            sec_data = provider_fn(p.id, session)
            dynamic_sections[section_name] = sec_data
        except Exception as e:
            dynamic_sections[section_name] = {"error": f"Failed loading section {section_name}: {str(e)}"}

    # Mask sensitive fields on participant profile
    masked_participant = mask_sensitive_fields(p.model_dump(), actor_role)

    # Warnings for UNKNOWN fields
    warnings: List[str] = []
    if p.diet == "UNKNOWN":
        warnings.append("Dietary preference is UNKNOWN - flag for desk verification on arrival.")
    if p.gender == "UNKNOWN":
        warnings.append("Gender is UNKNOWN - housing assignment requires confirmation.")
    if p.accommodation_requested == "UNKNOWN":
        warnings.append("Accommodation need is UNKNOWN - beds cannot be confirmed.")

    return {
        "participant": masked_participant,
        "contingent": contingent_info,
        "registrations": registrations_list,
        "diet": diet_info,
        "accessibility": accessibility_info,
        "merchandise": merchandise_info,
        "operational_status": operational_info,
        "sections": dynamic_sections,
        "warnings": warnings,
    }


def get_timeline(session: Session, participant_id: str) -> List[Dict[str, Any]]:
    """Retrieve chronological audit events and state transitions for a participant."""
    events = session.exec(
        select(AuditEvent).where(
            AuditEvent.entity_type == "participant",
            AuditEvent.entity_id == participant_id,
        ).order_by(AuditEvent.timestamp.desc())
    ).all()

    timeline = []
    for ev in events:
        timeline.append({
            "id": ev.id,
            "action": ev.action,
            "actor_id": ev.actor_id,
            "actor_role": ev.actor_role,
            "reason": ev.reason,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "before": ev.before_state,
            "after": ev.after_state,
        })
    return timeline
