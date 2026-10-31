# OWNER: P2
from datetime import datetime, timezone
import pytest
from sqlmodel import Session, select

from app.core.change_service import ChangeRequest, execute_change
from app.engines.unknowns.voi_engine import calculate_voi_ranking
from app.models.accommodation import Room
from app.models.participants import Contingent, FieldVerification, Participant
from app.schemas.common import Actor
from app.services.unknowns.service import (
    generate_batch_confirmation_request,
    get_voi_ranking,
    get_why_not_counterfactuals,
    verify_and_reconcile,
)


def test_voi_ranking_structure_and_order(session: Session):
    """VOI ranking reports ranked groups, empirical distributions & bounding ranges."""
    # Seed sample participants
    c = Contingent(id="c_voi_01", name="IIT Bombay", code="IITB")
    session.add(c)
    session.commit()

    p1 = Participant(
        id="p_v_01",
        name="Aarav Sharma",
        gender="UNKNOWN",
        accommodation_requested="UNKNOWN",
        contingent_id=c.id,
        diet="UNKNOWN",
        status="EXPECTED",
    )
    p2 = Participant(
        id="p_v_02",
        name="Neha Verma",
        gender="Female",
        accommodation_requested="YES",
        contingent_id=c.id,
        diet="Vegetarian",
        age=16,
        status="EXPECTED",
    )
    session.add_all([p1, p2])
    session.commit()

    ranking = get_voi_ranking(session)
    assert "ranked_groups" in ranking
    assert len(ranking["ranked_groups"]) == 6
    assert ranking["ranked_groups"][0]["rank"] == 1

    # Check methodology labeling
    housing_group = next(g for g in ranking["ranked_groups"] if g["group_id"] == "housing_gender")
    assert housing_group["method"] == "DATA_DISTRIBUTION"
    assert housing_group["simulated_outcomes"]["beds_eligible_range"][1] >= housing_group["simulated_outcomes"]["beds_eligible_range"][0]

    access_group = next(g for g in ranking["ranked_groups"] if g["group_id"] == "accessibility")
    assert access_group["method"] == "BOUNDING_RANGE"


def test_voi_ranking_recomputes_on_changed_data(session: Session, volunteer_actor: Actor):
    """VOI ranking scores and affected counts update dynamically when participants are verified."""
    p = Participant(
        id="p_recomp_01",
        name="Vikram Rao",
        gender="UNKNOWN",
        diet="UNKNOWN",
        status="EXPECTED",
    )
    session.add(p)
    session.commit()

    ranking1 = get_voi_ranking(session)
    diet_g1 = next(g for g in ranking1["ranked_groups"] if g["group_id"] == "dietary")
    initial_diet_affected = diet_g1["affected_participants"]
    assert initial_diet_affected >= 1

    # Verify participant diet via ChangeService
    req = ChangeRequest(
        action="unknowns.verify_field",
        entity_type="participant",
        entity_id="p_recomp_01",
        payload={
            "field": "diet",
            "value": "VEGAN",
            "source": "DESK_VERIFICATION",
            "verifier": volunteer_actor.id,
        },
        reason="Verified verbally",
        actor=volunteer_actor,
    )
    res = execute_change(req, session)
    assert res.status in ["APPLIED", "COMMITTED"]
    session.commit()

    # Re-run ranking
    ranking2 = get_voi_ranking(session)
    diet_g2 = next(g for g in ranking2["ranked_groups"] if g["group_id"] == "dietary")
    assert diet_g2["affected_participants"] == initial_diet_affected - 1


def test_before_after_totals_reconcile_with_plain_engine_rerun(session: Session, volunteer_actor: Actor):
    """Verification reconciliation matches plain manual engine count re-evaluation."""
    p = Participant(
        id="p_recon_01",
        name="Divya Iyer",
        gender="UNKNOWN",
        accommodation_requested="UNKNOWN",
        status="EXPECTED",
    )
    session.add(p)
    session.commit()

    unresolved_before = len(session.exec(select(Participant).where(Participant.gender == "UNKNOWN")).all())

    # Call verify_and_reconcile
    recon = verify_and_reconcile(
        session=session,
        entity_type="participant",
        entity_id="p_recon_01",
        field="gender",
        value="FEMALE",
        source="DESK_VERIFICATION",
        verifier=volunteer_actor.id,
        actor=volunteer_actor,
    )

    unresolved_after = len(session.exec(select(Participant).where(Participant.gender == "UNKNOWN")).all())

    assert recon["reconciliation"]["unresolved_count_before"] == unresolved_before
    assert recon["reconciliation"]["unresolved_count_after"] == unresolved_after
    assert recon["reconciliation"]["delta"] == 1
    assert unresolved_after == unresolved_before - 1


def test_batch_confirmation_request_generation(session: Session):
    """Minimal confirmation request batches by contingent leader and targets only missing fields."""
    c = Contingent(id="c_batch_01", name="IIM Bangalore", code="IIMB", leader="Ananya Roy")
    session.add(c)
    session.commit()

    p = Participant(
        id="p_b_01",
        name="Rohit Shenoy",
        contingent_id=c.id,
        gender="UNKNOWN",
        accommodation_requested="YES",
        status="EXPECTED",
    )
    session.add(p)
    session.commit()

    batch_req = generate_batch_confirmation_request(
        session=session,
        target_type="CONTINGENT_LEADER",
        contingent_id=c.id,
        group_id="housing_gender",
    )

    assert batch_req["contingent_id"] == c.id
    assert batch_req["leader_name"] == "Ananya Roy"
    assert "gender" in batch_req["fields_requested"]
    assert len(batch_req["participants"]) == 1
    assert batch_req["participants"][0]["id"] == "p_b_01"
    assert "gender" in batch_req["participants"][0]["missing_fields"]


def test_why_not_counterfactuals(session: Session):
    """Why-not counterfactuals simulate 'what confirming X would change' for an unplaced participant."""
    r1 = Room(id="r_g_01", block="G1", capacity=2, gender_class="GIRLS", status="READY")
    r2 = Room(id="r_b_01", block="B1", capacity=2, gender_class="BOYS", status="READY")
    session.add_all([r1, r2])
    session.commit()

    p = Participant(
        id="p_wn_01",
        name="Kavya Joshi",
        gender="UNKNOWN",
        accommodation_requested="UNKNOWN",
        diet="UNKNOWN",
        status="EXPECTED",
    )
    session.add(p)
    session.commit()

    wn = get_why_not_counterfactuals(session, "p_wn_01")
    assert wn["participant_id"] == "p_wn_01"
    assert "GENDER_UNKNOWN" in wn["blocking_reasons"]
    assert "HOUSING_PREFERENCE_UNKNOWN" in wn["blocking_reasons"]

    gender_cf = [c for c in wn["counterfactuals"] if c["field"] == "gender"]
    assert len(gender_cf) == 2  # FEMALE & MALE
    female_run = next(c for c in gender_cf if c["if_confirmed_as"] == "FEMALE")
    assert "Girls hostel" in female_run["outcome"]

    housing_cf = [c for c in wn["counterfactuals"] if c["field"] == "accommodation_requested"]
    no_housing = next(c for c in housing_cf if c["if_confirmed_as"] == "NO")
    assert "0 beds required" in no_housing["outcome"]
