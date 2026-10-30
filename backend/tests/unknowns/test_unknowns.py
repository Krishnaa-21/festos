# OWNER: P2 (P1 testing field verification)
"""Tests for Unknowns field verification queue, ranking, and confirmation tokens."""

from app.core.change_service import ChangeRequest, execute_change
from app.models.participants import FieldVerification, Participant
from app.schemas.common import Actor
from app.services.unknowns.service import (
    confirm_token_submission,
    generate_confirmation_token,
    get_unknown_queue,
    verify_confirmation_token,
)
from sqlmodel import Session, select


def test_unknown_queue_ranked_by_count_times_criticality(session: Session):
    """Unknown fields queue ranks items deterministically by (count x criticality)."""
    # Criticalities:
    # accommodation_requested: 4
    # gender: 4
    # diet: 3
    # tshirt_size: 2

    # Add 10 unknown diet -> score = 10 * 3 = 30
    # Add 5 unknown accommodation_requested -> score = 5 * 4 = 20
    # Add 2 unknown tshirt_size -> score = 2 * 2 = 4
    for i in range(10):
        session.add(Participant(
            id=f"p_diet_{i}",
            name=f"Diet UNK {i}",
            diet="UNKNOWN",
            gender="Male",
            accommodation_requested="YES",
            tshirt_size="M",
            status="EXPECTED",
        ))
    for i in range(5):
        session.add(Participant(
            id=f"p_accom_{i}",
            name=f"Accom UNK {i}",
            diet="VEG",
            gender="Male",
            accommodation_requested="UNKNOWN",
            tshirt_size="M",
            status="EXPECTED",
        ))
    for i in range(2):
        session.add(Participant(
            id=f"p_tshirt_{i}",
            name=f"Tshirt UNK {i}",
            diet="VEG",
            gender="Male",
            accommodation_requested="YES",
            tshirt_size="UNKNOWN",
            status="EXPECTED",
        ))
    session.commit()

    res = get_unknown_queue(session)
    queue = res["queue"]
    assert len(queue) == 3

    # Ranking:
    # 1st: diet (score 30)
    # 2nd: accommodation_requested (score 20)
    # 3rd: tshirt_size (score 4)
    assert queue[0]["field"] == "diet"
    assert queue[0]["score"] == 30
    assert queue[0]["criticality"] == 3
    assert queue[0]["owner"] == "FOOD_OPS_MANAGER"

    assert queue[1]["field"] == "accommodation_requested"
    assert queue[1]["score"] == 20
    assert queue[1]["criticality"] == 4
    assert queue[1]["owner"] == "ACCOMMODATION_LEAD"

    assert queue[2]["field"] == "tshirt_size"
    assert queue[2]["score"] == 4
    assert queue[2]["criticality"] == 2


def test_field_verification_through_change_service(session: Session, volunteer_actor: Actor):
    """Recording verified field updates participant attribute and creates FieldVerification record."""
    p = Participant(id="p_ver_01", name="Siddharth Roy", diet="UNKNOWN", status="EXPECTED")
    session.add(p)
    session.commit()

    req = ChangeRequest(
        action="unknowns.verify_field",
        entity_type="participant",
        entity_id="p_ver_01",
        payload={
            "field": "diet",
            "value": "VEGAN",
            "source": "DESK_VERIFICATION",
            "verifier": volunteer_actor.id,
        },
        reason="Verified verbally at registration counter",
        actor=volunteer_actor,
    )
    result = execute_change(req, session)
    assert result.status == "APPLIED"

    session.refresh(p)
    assert p.diet == "VEGAN"
    assert p.version == 2

    # Check FieldVerification row
    ver = session.exec(
        select(FieldVerification).where(FieldVerification.entity_id == "p_ver_01", FieldVerification.field == "diet")
    ).first()
    assert ver is not None
    assert ver.status == "VERIFIED"
    assert ver.value == "VEGAN"
    assert ver.source == "DESK_VERIFICATION"
    assert ver.verified_by == volunteer_actor.id


def test_signed_confirmation_token_workflow(session: Session):
    """Signed, expiring confirmation token allows remote confirmation and commits via ChangeService."""
    p = Participant(id="p_tok_01", name="Kunal Verma", diet="UNKNOWN", status="EXPECTED")
    session.add(p)
    session.commit()

    # Generate token
    token_data = generate_confirmation_token(
        entity_type="participant",
        entity_id="p_tok_01",
        field="diet",
        expires_in_minutes=60,
        role="LEADER",
    )
    token = token_data["token"]
    assert token is not None

    # Verify token claims
    claims = verify_confirmation_token(token)
    assert claims["entity_id"] == "p_tok_01"
    assert claims["field"] == "diet"
    assert claims["role"] == "LEADER"

    # Submit verification
    res = confirm_token_submission(
        session=session,
        token=token,
        value="NON_VEG",
        source="LEADER_PORTAL",
        comment="Contingent leader verified diet from college roster",
    )
    assert res["status"] == "VERIFIED"
    assert res["value"] == "NON_VEG"

    session.refresh(p)
    assert p.diet == "NON_VEG"
