# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now
from app.core.errors import FestOSError, NotFoundError
from app.models.ops import NotificationDeliveryLog, NotificationDraft
from app.schemas.common import Actor
from app.schemas.notifications import EditDraftRequest

logger = logging.getLogger("festos.services.notifications")

TEMPLATES = [
    {
        "key": "VENDOR_SHUTDOWN_LEADERS",
        "audience": "contingent_leaders",
        "channel": "SMS",
        "title": "Vendor Interruption Notice",
        "body_template": "Attention Leaders: Vendor {vendor_name} is offline. Meals for {affected_slots} are transferred to {replacement_name} ({location}).",
    },
    {
        "audience": "volunteers",
        "channel": "APP",
        "key": "VENDOR_SHUTDOWN_VOLUNTEERS",
        "title": "Volunteer Dining Redirection Alert",
        "body_template": "Duty Alert: Direct participants from {vendor_name} to {replacement_name} counters at {location} for {affected_slots}.",
    },
    {
        "audience": "vendors",
        "channel": "WHATSAPP",
        "key": "VENDOR_SHUTDOWN_VENDORS",
        "title": "Emergency Capacity Expansion",
        "body_template": "Notice to {replacement_name}: Prepare for +{lost_capacity} additional meal capacity at {location} for {affected_slots}.",
    },
    {
        "audience": "accommodation_coordinators",
        "channel": "EMAIL",
        "key": "VENDOR_SHUTDOWN_HOUSING",
        "title": "Hostel Dining Transfer",
        "body_template": "Coordinators: Catering at {location} transferred from {vendor_name} to {replacement_name}. Please advise resident contingents.",
    },
    {
        "audience": "event_organisers",
        "channel": "APP",
        "key": "VENDOR_SHUTDOWN_ORGANISERS",
        "title": "Event Schedule & Dining Sync",
        "body_template": "Event Organisers: Catering counters at {location} re-routed to {replacement_name}. Ensure session breaks match new capacity.",
    },
]


def list_templates() -> List[Dict[str, Any]]:
    return TEMPLATES


def generate_drafts(
    event_type: str,
    context: Dict[str, Any],
    change_set_id: Optional[str] = None,
    incident_id: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[NotificationDraft]:
    """Generate structured notification drafts across all 5 audiences (Spec 6.14).

    Exposed for Prompt 11, Prompt 14 (incidents), and other modules.
    """
    drafts: List[NotificationDraft] = []
    created_at_dt = now()

    vendor_name = context.get("vendor_name", "Vendor")
    replacement_name = context.get("replacement_name", "Alternative Counter")
    location = context.get("location", "Campus Dining Hall")
    affected_slots = ", ".join(context.get("affected_slots", ["LUNCH"]))
    lost_capacity = context.get("lost_capacity", 200)

    # 1. Contingent Leaders
    drafts.append(
        NotificationDraft(
            audience="contingent_leaders",
            channel="SMS",
            recipient="All Contingent Leaders",
            subject=f"Dining Update: {location}",
            body=(
                f"Attention Leaders: {vendor_name} is offline. Meals for {affected_slots} "
                f"will be served at {replacement_name} ({location}). Please inform contingent members."
            ),
            status="PENDING_APPROVAL",
            requires_approval=True,
            template_key="VENDOR_SHUTDOWN_LEADERS",
            related_change_set_id=change_set_id,
            related_incident_id=incident_id,
            created_at=created_at_dt,
            updated_at=created_at_dt,
        )
    )

    # 2. Volunteers
    drafts.append(
        NotificationDraft(
            audience="volunteers",
            channel="APP",
            recipient="Food Operations & Venue Volunteers",
            subject=f"OPERATIONAL: Direct participants to {replacement_name}",
            body=(
                f"Duty Alert: {vendor_name} has shut down at {location}. "
                f"Direct participants to {replacement_name} counters during {affected_slots}."
            ),
            status="PENDING_APPROVAL",
            requires_approval=True,
            template_key="VENDOR_SHUTDOWN_VOLUNTEERS",
            related_change_set_id=change_set_id,
            related_incident_id=incident_id,
            created_at=created_at_dt,
            updated_at=created_at_dt,
        )
    )

    # 3. Vendors
    drafts.append(
        NotificationDraft(
            audience="vendors",
            channel="WHATSAPP",
            recipient=f"Management: {replacement_name}",
            subject=f"EMERGENCY CAPACITY EXPANSION: {replacement_name}",
            body=(
                f"Notice to {replacement_name}: Prepare for +{lost_capacity} additional meal capacity "
                f"at {location} for {affected_slots} due to emergency vendor reassignment."
            ),
            status="PENDING_APPROVAL",
            requires_approval=True,
            template_key="VENDOR_SHUTDOWN_VENDORS",
            related_change_set_id=change_set_id,
            related_incident_id=incident_id,
            created_at=created_at_dt,
            updated_at=created_at_dt,
        )
    )

    # 4. Accommodation Coordinators
    drafts.append(
        NotificationDraft(
            audience="accommodation_coordinators",
            channel="EMAIL",
            recipient="Hostel Accommodation Desk",
            subject=f"Catering Change Alert: {location}",
            body=(
                f"Coordinators: Dining operations at {location} transferred from {vendor_name} "
                f"to {replacement_name}. Advise participants before departure from hostels."
            ),
            status="PENDING_APPROVAL",
            requires_approval=True,
            template_key="VENDOR_SHUTDOWN_HOUSING",
            related_change_set_id=change_set_id,
            related_incident_id=incident_id,
            created_at=created_at_dt,
            updated_at=created_at_dt,
        )
    )

    # 5. Event Organisers
    drafts.append(
        NotificationDraft(
            audience="event_organisers",
            channel="APP",
            recipient="All Event Session Leads",
            subject=f"Event Schedule & Dining Sync: {location}",
            body=(
                f"Event Organisers: Dining counters at {location} re-routed to {replacement_name}. "
                f"Ensure session intervals sync with new counter capacity."
            ),
            status="PENDING_APPROVAL",
            requires_approval=True,
            template_key="VENDOR_SHUTDOWN_ORGANISERS",
            related_change_set_id=change_set_id,
            related_incident_id=incident_id,
            created_at=created_at_dt,
            updated_at=created_at_dt,
        )
    )

    if session:
        for d in drafts:
            session.add(d)
        session.flush()

    return drafts


def list_drafts(
    session: Session,
    audience: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
) -> List[NotificationDraft]:
    query = select(NotificationDraft)
    if audience:
        query = query.where(NotificationDraft.audience == audience)
    if status:
        query = query.where(NotificationDraft.status == status)
    if channel:
        query = query.where(NotificationDraft.channel == channel)
    query = query.order_by(NotificationDraft.created_at.desc())
    return session.exec(query).all()


def get_draft(session: Session, draft_id: str) -> NotificationDraft:
    draft = session.get(NotificationDraft, draft_id)
    if not draft:
        raise NotFoundError(f"Notification draft '{draft_id}' not found.")
    return draft


def update_draft(session: Session, draft_id: str, req: EditDraftRequest, actor: Actor) -> NotificationDraft:
    draft = get_draft(session, draft_id)
    if draft.status == "SENT":
        raise FestOSError("Cannot edit a notification draft that has already been sent.", code="CONSTRAINT_VIOLATION", status_code=422)

    if req.subject is not None:
        draft.subject = req.subject
    if req.body is not None:
        draft.body = req.body
    if req.channel is not None:
        draft.channel = req.channel
    if req.recipient is not None:
        draft.recipient = req.recipient

    draft.updated_at = now()
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft


def approve_draft(session: Session, draft_id: str, actor: Actor) -> NotificationDraft:
    draft = get_draft(session, draft_id)
    draft.status = "APPROVED"
    draft.approved_by = actor.name or actor.id
    draft.approved_at = now()
    draft.updated_at = now()
    session.add(draft)
    session.commit()
    session.refresh(draft)
    logger.info(f"Approved notification draft '{draft_id}' by {actor.id}")
    return draft


def send_draft(session: Session, draft_id: str, actor: Actor) -> NotificationDeliveryLog:
    """Mock-send a notification draft. Strictly requires prior approval."""
    draft = get_draft(session, draft_id)

    # STRICT APPROVAL GUARD
    if draft.status != "APPROVED":
        raise FestOSError(
            message=f"Notification draft '{draft_id}' cannot be sent without prior approval (current status: {draft.status}).",
            code="CONSTRAINT_VIOLATION",
            status_code=422,
        )

    # Record delivery log
    log_entry = NotificationDeliveryLog(
        draft_id=draft.id,
        audience=draft.audience,
        recipient=draft.recipient,
        channel=draft.channel,
        subject=draft.subject,
        body=draft.body,
        sent_at=now(),
        status="DELIVERED",
        provider="MOCK_DISPATCHER",
    )
    session.add(log_entry)

    draft.status = "SENT"
    draft.updated_at = now()
    session.add(draft)

    session.commit()
    session.refresh(log_entry)
    logger.info(f"Dispatched notification draft '{draft_id}' to '{draft.recipient}' via {draft.channel}")
    return log_entry


def get_delivery_logs(session: Session) -> List[NotificationDeliveryLog]:
    return session.exec(select(NotificationDeliveryLog).order_by(NotificationDeliveryLog.sent_at.desc())).all()
