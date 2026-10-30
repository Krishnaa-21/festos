# OWNER: P1
"""Tests for Deduplication, Merge, Byte-Identical Undo, and Reconciliation Waterfall."""

from datetime import datetime, timezone

from app.core.change_service import ChangeRequest, execute_change
from app.engines.dedupe import compute_pair_similarity
from app.models.inventory import MerchClaim
from app.models.participants import (
    Contingent,
    DuplicateCandidate,
    MergeRecord,
    Participant,
    Registration,
)
from app.schemas.common import Actor
from app.services.reconciliation.service import (
    get_waterfall,
)
from sqlmodel import Session, select


def test_same_name_different_contact_never_auto_merges():
    """Names repeat heavily in this pack and contacts may be unique, so name similarity alone must NEVER reach LIKELY."""
    # Two participants with exact same name, but different contingents and different contacts
    p1 = {
        "id": "P101",
        "name": "Rahul Sharma",
        "college": "IIT Delhi",
        "contingent_id": "C09",
        "contact": "+91-9876500001",
        "age": 21,
    }
    p2 = {
        "id": "P202",
        "name": "Rahul Sharma",
        "college": "BITS Pilani",
        "contingent_id": "C14",
        "contact": "+91-9876500002",
        "age": 22,
    }

    res = compute_pair_similarity(p1, p2)

    # Name similarity is 1.0, but score MUST be capped and NEVER reach LIKELY
    assert res["reasons"]["name_similarity"] == 1.0
    assert res["score"] < 0.60
    assert res["classification"] != "LIKELY"
    assert res["classification"] != "EXACT"
    assert res["can_auto_merge"] is False
    assert res["reasons"]["phones_differ"] is True


def test_merge_and_byte_identical_undo_merge(session: Session, director_actor: Actor):
    """Test that undo merge restores byte-identical rows and repoints registrations/claims."""
    # Seed Contingent
    c = Contingent(id="C08", code="C08", name="IIT Bombay Contingent", college="IIT Bombay", strength_declared=45)
    session.add(c)

    # Participant A (Canonical)
    pa = Participant(
        id="P0412",
        canonical_participant_id="P0412",
        source_row_id="412",
        contingent_id="C08",
        name="Aditya Verma",
        college="IIT Bombay",
        email="aditya@iitb.ac.in",
        phone="+91-9876511111",
        gender="Male",
        diet="UNKNOWN",
        housing_preference="UNKNOWN",
        accessibility_needs={},
        accommodation_requested="YES",
        tshirt_size="L",
        arrival_at=datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc),
        departure_at=datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc),
        age=20,
        role="PARTICIPANT",
        status="EXPECTED",
        version=1,
        created_at=datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc),
    )
    session.add(pa)

    # Participant B (Duplicate to merge)
    pb = Participant(
        id="P1845",
        canonical_participant_id="P1845",
        source_row_id="1845",
        contingent_id="C08",
        name="Aditya Verma",
        college="IIT Bombay",
        email=None,
        phone="+91-9876511111",
        gender="Male",
        diet="VEG",
        housing_preference="UNKNOWN",
        accessibility_needs={},
        accommodation_requested="YES",
        tshirt_size="L",
        arrival_at=datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc),
        departure_at=datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc),
        age=20,
        role="PARTICIPANT",
        status="EXPECTED",
        version=1,
        created_at=datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc),
    )
    session.add(pb)

    # Linked registration on B
    rb = Registration(
        id="reg_b_01",
        participant_id="P1845",
        event_id="EV04",
        status="REGISTERED",
    )
    session.add(rb)

    # Candidate record
    cand = DuplicateCandidate(
        id="dup_test_01",
        participant_a_id="P0412",
        participant_b_id="P1845",
        score=0.95,
        classification="LIKELY",
        status="PENDING",
    )
    session.add(cand)
    session.commit()

    # Save exact snapshots before merge for byte-identical verification
    session.refresh(pa)
    session.refresh(pb)
    pa_before = pa.model_dump()
    pb_before = pb.model_dump()

    # 1. Execute Merge
    req_merge = ChangeRequest(
        action="participant.merge",
        entity_type="participant",
        entity_id="P0412",
        payload={
            "canonical_id": "P0412",
            "merged_id": "P1845",
            "candidate_id": "dup_test_01",
        },
        reason="Verified duplicate with identical contact, age, and college",
        actor=director_actor,
    )
    res_merge = execute_change(req_merge, session)
    assert res_merge.status == "APPLIED"

    session.refresh(pa)
    session.refresh(pb)
    session.refresh(rb)
    session.refresh(cand)

    assert pb.status == "MERGED"
    assert pb.canonical_participant_id == "P0412"
    assert rb.participant_id == "P0412"  # Repointed
    assert pa.diet == "VEG"  # Filled missing value from loser
    assert cand.status == "RESOLVED"

    # Find the MergeRecord
    merge_rec = session.exec(
        select(MergeRecord).where(MergeRecord.canonical_participant_id == "P0412")
    ).first()
    assert merge_rec is not None
    assert merge_rec.is_reverted is False

    # 2. Execute Undo Merge
    req_undo = ChangeRequest(
        action="participant.undo_merge",
        entity_type="merge_record",
        entity_id=merge_rec.id,
        payload={"merge_id": merge_rec.id},
        reason="Mistaken merge reverted upon detailed ID check",
        actor=director_actor,
    )
    res_undo = execute_change(req_undo, session)
    assert res_undo.status == "APPLIED"

    session.refresh(pa)
    session.refresh(pb)
    session.refresh(rb)
    session.refresh(cand)
    session.refresh(merge_rec)

    # 3. Assert Byte-Identical Row Restoration
    pb_after = pb.model_dump()
    pa_after = pa.model_dump()

    # Compare all fields of merged participant B
    assert pb_after == pb_before, f"Merged participant not byte-identical! Diff: {set(pb_after.items()) ^ set(pb_before.items())}"

    # Compare canonical participant A
    assert pa_after == pa_before, f"Canonical participant not byte-identical! Diff: {set(pa_after.items()) ^ set(pa_before.items())}"

    # Assert registration repointed back to B
    assert rb.participant_id == "P1845"
    assert merge_rec.is_reverted is True
    assert cand.status == "PENDING"


def test_conflicting_merch_claims_block_merge(session: Session, director_actor: Actor):
    """Merge is blocked for review if both records already hold conflicting merchandise claims."""
    pa = Participant(id="P0001", canonical_participant_id="P0001", name="Aditi Patel", status="EXPECTED")
    pb = Participant(id="P0002", canonical_participant_id="P0002", name="Aditi Patel", status="EXPECTED")
    session.add(pa)
    session.add(pb)

    # Both participants hold claims for item 'ITM_TSHIRT'
    ca = MerchClaim(id="clm_01", canonical_participant_id="P0001", item_id="ITM_TSHIRT")
    cb = MerchClaim(id="clm_02", canonical_participant_id="P0002", item_id="ITM_TSHIRT")
    session.add(ca)
    session.add(cb)
    session.commit()

    req_merge = ChangeRequest(
        action="participant.merge",
        entity_type="participant",
        entity_id="P0001",
        payload={"canonical_id": "P0001", "merged_id": "P0002"},
        actor=director_actor,
    )
    res = execute_change(req_merge, session)
    assert res.status == "REJECTED"
    assert any(v.code == "CONFLICTING_MERCH_CLAIMS" for v in res.violations)


def test_reconciliation_numbers_add_up(session: Session):
    """Reconciliation numbers add up: declared - deficit + surplus == raw."""
    # Seed 3 contingents
    # C01 declared: 10, actual: 10 (diff 0)
    # C02 declared: 20, actual: 15 (deficit -5)
    # C03 declared: 30, actual: 32 (surplus +2)
    # Total declared = 60. Raw total = 10 + 15 + 32 = 57. Gap = -3.
    c1 = Contingent(id="C01", code="C01", name="C01", strength_declared=10)
    c2 = Contingent(id="C02", code="C02", name="C02", strength_declared=20)
    c3 = Contingent(id="C03", code="C03", name="C03", strength_declared=30)
    session.add_all([c1, c2, c3])

    for i in range(10):
        session.add(Participant(id=f"p1_{i}", canonical_participant_id=f"p1_{i}", contingent_id="C01", status="EXPECTED"))
    for i in range(15):
        session.add(Participant(id=f"p2_{i}", canonical_participant_id=f"p2_{i}", contingent_id="C02", status="EXPECTED"))
    for i in range(32):
        session.add(Participant(id=f"p3_{i}", canonical_participant_id=f"p3_{i}", contingent_id="C03", status="EXPECTED"))

    session.commit()

    waterfall_res = get_waterfall(session)
    counts = waterfall_res["counts"]

    assert counts["declared"] == 60
    assert counts["raw"] == 57
    assert counts["declared_vs_raw_gap"] == -3

    # Check waterfall arithmetic
    steps = {s["step"]: s for s in waterfall_res["waterfall"]}
    declared_step = steps["DECLARED_TOTAL"]["count"]
    deficit_delta = steps["CONTINGENT_DEFICIT"]["delta"]
    surplus_delta = steps["CONTINGENT_SURPLUS"]["delta"]
    raw_step = steps["RAW_ROSTER_TOTAL"]["count"]

    assert deficit_delta == -5
    assert surplus_delta == 2
    assert declared_step + deficit_delta + surplus_delta == raw_step
