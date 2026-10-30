# OWNER: P1
"""Tests for Participants module, status transitions, bus events, and role-based masking."""

from typing import Any, Dict

from app.core.bus import subscribe
from app.core.change_service import ChangeRequest, execute_change
from app.core.registry import register_participant_section
from app.models.participants import Contingent, Participant, Registration
from app.schemas.common import Actor
from app.services.participants.service import (
    get_participant,
    get_participant_360,
)
from sqlmodel import Session


def test_participant_crud_via_change_service(session: Session, director_actor: Actor):
    """Profile CRUD executed strictly through ChangeService."""
    req_create = ChangeRequest(
        action="participant.create",
        entity_type="participant",
        entity_id="par_test01",
        payload={
            "id": "par_test01",
            "name": "Ananya Sharma",
            "college": "IIT Bombay",
            "contingent_id": "C05",
            "phone": "+91-9876543210",
            "email": "ananya@iitb.ac.in",
            "gender": "Female",
            "diet": "VEG",
            "accommodation_requested": "YES",
            "tshirt_size": "M",
            "age": 21,
            "status": "EXPECTED",
        },
        actor=director_actor,
    )
    res_create = execute_change(req_create, session)
    assert res_create.status == "APPLIED"

    p = session.get(Participant, "par_test01")
    assert p is not None
    assert p.name == "Ananya Sharma"
    assert p.version == 1

    # Update through ChangeService
    req_update = ChangeRequest(
        action="participant.update",
        entity_type="participant",
        entity_id="par_test01",
        payload={"diet": "JAIN", "tshirt_size": "L"},
        expected_version=1,
        actor=director_actor,
    )
    res_update = execute_change(req_update, session)
    assert res_update.status == "APPLIED"

    session.refresh(p)
    assert p.diet == "JAIN"
    assert p.tshirt_size == "L"
    assert p.version == 2


def test_status_machine_publishes_bus_event_once(session: Session, director_actor: Actor):
    """Participant status transitions publish participant.status_changed event on core.bus exactly once."""
    events_received: list[Dict[str, Any]] = []

    @subscribe("participant.status_changed")
    def on_status_changed(payload: Dict[str, Any]):
        events_received.append(payload)

    p = Participant(
        id="par_state01",
        canonical_participant_id="par_state01",
        name="Rohan Verma",
        college="IIM Indore",
        contingent_id="C01",
        status="EXPECTED",
        version=1,
    )
    session.add(p)
    session.commit()

    # Transition EXPECTED -> ARRIVED
    req_arrived = ChangeRequest(
        action="participant.change_status",
        entity_type="participant",
        entity_id="par_state01",
        payload={"status": "ARRIVED"},
        reason="Arrived at main entrance gate",
        actor=director_actor,
    )
    res_arrived = execute_change(req_arrived, session)
    assert res_arrived.status == "APPLIED"

    assert len(events_received) == 1
    ev = events_received[0]
    assert ev["participant_id"] == "par_state01"
    assert ev["previous_status"] == "EXPECTED"
    assert ev["new_status"] == "ARRIVED"
    assert ev["reason"] == "Arrived at main entrance gate"

    # Transition ARRIVED -> CHECKED_IN
    req_checkin = ChangeRequest(
        action="participant.change_status",
        entity_type="participant",
        entity_id="par_state01",
        payload={"status": "CHECKED_IN"},
        reason="Badge printed and kit issued",
        actor=director_actor,
    )
    res_checkin = execute_change(req_checkin, session)
    assert res_checkin.status == "APPLIED"
    assert len(events_received) == 2
    assert events_received[1]["new_status"] == "CHECKED_IN"


def test_disallowed_status_transition_rejected(session: Session, volunteer_actor: Actor):
    """Invalid status transition is rejected with constraint violation."""
    p = Participant(
        id="par_state02",
        canonical_participant_id="par_state02",
        name="Vikram Rao",
        status="EXPECTED",
        version=1,
    )
    session.add(p)
    session.commit()

    # Attempt illegal transition EXPECTED -> CHECKED_OUT directly
    req_illegal = ChangeRequest(
        action="participant.change_status",
        entity_type="participant",
        entity_id="par_state02",
        payload={"status": "CHECKED_OUT"},
        actor=volunteer_actor,
    )
    res = execute_change(req_illegal, session)
    assert res.status == "REJECTED"
    assert any(v.code == "INVALID_STATE_TRANSITION" for v in res.violations)


def test_masked_fields_hidden_for_volunteer_role(session: Session):
    """Masked sensitive fields (phone, email, contact, medical/accessibility) are obscured for Volunteer role."""
    p = Participant(
        id="par_mask01",
        canonical_participant_id="par_mask01",
        name="Tanvi Patel",
        phone="+91-9876543210",
        email="tanvi.patel@iitb.ac.in",
        gender="Female",
        accessibility_needs={"raw": "Wheelchair access", "has_need": True},
        status="EXPECTED",
    )
    session.add(p)
    session.commit()

    # Query as VOLUNTEER
    res_volunteer = get_participant(session, "par_mask01", actor_role="VOLUNTEER")
    assert res_volunteer is not None
    assert "+91-9876543210" not in res_volunteer["phone"]
    assert "****" in res_volunteer["phone"]
    assert "tanvi.patel@iitb.ac.in" not in res_volunteer["email"]
    assert "***@" in res_volunteer["email"]
    assert res_volunteer["accessibility_needs"] == {"status": "MASKED_RESTRICTED"}

    # Query as FESTIVAL_DIRECTOR
    res_director = get_participant(session, "par_mask01", actor_role="FESTIVAL_DIRECTOR")
    assert res_director is not None
    assert res_director["phone"] == "+91-9876543210"
    assert res_director["email"] == "tanvi.patel@iitb.ac.in"
    assert res_director["accessibility_needs"]["raw"] == "Wheelchair access"


def test_participant_360_aggregates_all_sections(session: Session, director_actor: Actor):
    """GET /participants/{id}/360 aggregates contingent, registrations, diet, accessibility, merch, and dynamic sections."""
    c = Contingent(
        id="C05",
        code="C05",
        name="IIT Bombay Contingent",
        college="IIT Bombay",
        leader="Rohan Deshmukh",
        escort="Dr. Raman",
        strength_declared=80,
    )
    session.add(c)

    p = Participant(
        id="par_360_01",
        canonical_participant_id="par_360_01",
        name="Aarav Gupta",
        college="IIT Bombay",
        contingent_id="C05",
        phone="+91-9988776655",
        diet="UNKNOWN",
        gender="UNKNOWN",
        accommodation_requested="UNKNOWN",
        tshirt_size="L",
        status="EXPECTED",
    )
    session.add(p)

    r = Registration(
        id="reg_360_01",
        participant_id="par_360_01",
        event_id="E01",
        team_id="T01",
        status="REGISTERED",
    )
    session.add(r)
    session.commit()

    # Register a dynamic participant section (e.g. accommodation mock hook)
    @register_participant_section("test_accommodation_section")
    def provide_housing(pid: str, s: Session) -> Dict[str, Any]:
        return {"assigned_bed": "B1-102", "plan": "Plan A"}

    view_360 = get_participant_360(session, "par_360_01", actor_role="FESTIVAL_DIRECTOR")
    assert view_360 is not None

    # Verify participant & UNKNOWN values are preserved
    assert view_360["participant"]["name"] == "Aarav Gupta"
    assert view_360["participant"]["diet"] == "UNKNOWN"
    assert view_360["participant"]["gender"] == "UNKNOWN"

    # Verify contingent link
    assert view_360["contingent"]["id"] == "C05"
    assert view_360["contingent"]["name"] == "IIT Bombay Contingent"

    # Verify event registrations
    assert len(view_360["registrations"]) == 1
    assert view_360["registrations"][0]["event_id"] == "E01"

    # Verify dynamic section hook
    assert "test_accommodation_section" in view_360["sections"]
    assert view_360["sections"]["test_accommodation_section"]["assigned_bed"] == "B1-102"

    # Verify warnings generated for UNKNOWN fields
    assert any("Dietary preference is UNKNOWN" in w for w in view_360["warnings"])
