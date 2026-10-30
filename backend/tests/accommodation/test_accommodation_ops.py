# OWNER: P2
import concurrent.futures
from datetime import datetime, timezone

import pytest
from app.core.approvals import approve_request
from app.core.bus import publish
from app.core.errors import FestOSError, VersionConflictError
from app.models.accommodation import (
    AccommodationPlan,
    BedReallocationSuggestion,
    Room,
    StayAssignment,
)
from app.models.audit import AuditEvent
from app.models.decisions import DecisionCard
from app.models.participants import Participant
from app.schemas.accommodation import ManualAssignRequest, RepairPlanRequest
from app.schemas.checkin import (
    CheckinRequest,
    CheckoutRequest,
    OfflineOperation,
    SyncBatchRequest,
)
from app.schemas.common import Actor, Role
from app.seed.accommodation import seed_accommodation_resources
from app.services.accommodation.service import (
    close_block_rooms,
    commit_plan_to_live,
    complete_room_cleaning,
    generate_plans,
    get_live_plan,
    manual_assign,
    repair_accommodation,
)
from app.services.checkin.handlers import register_checkin_handlers
from app.services.checkin.service import (
    checkin_participant,
    checkout_participant,
    sync_offline_operations,
)
from sqlmodel import Session, select


@pytest.fixture
def ops_session():
    register_checkin_handlers()
    import app.models  # noqa: F401
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, create_engine

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_accommodation_resources(session)

        # Seed sample participants
        participants = [
            Participant(
                id="P_MALE_01",
                name="Aarav Sharma",
                contingent_id="C01",
                college="IIT Bombay",
                gender="MALE",
                age=21,
                accessibility_needs="",
                housing_preference="standard",
                arrival_at=datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
                accommodation_requested="YES",
                status="EXPECTED",
            ),
            Participant(
                id="P_MALE_02",
                name="Rohan Verma",
                contingent_id="C01",
                college="IIT Bombay",
                gender="MALE",
                age=21,
                accessibility_needs="",
                housing_preference="standard",
                arrival_at=datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
                accommodation_requested="YES",
                status="EXPECTED",
            ),
            Participant(
                id="P_FEMALE_01",
                name="Pooja Patel",
                contingent_id="C02",
                college="IIM Ahmedabad",
                gender="FEMALE",
                age=22,
                accessibility_needs="",
                housing_preference="standard",
                arrival_at=datetime(2026, 10, 29, 11, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
                accommodation_requested="YES",
                status="EXPECTED",
            ),
            Participant(
                id="P_ACC_01",
                name="Vikram Rao",
                contingent_id="C03",
                college="BITS Pilani",
                gender="MALE",
                age=20,
                accessibility_needs="wheelchair",
                housing_preference="accessible",
                arrival_at=datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
                accommodation_requested="YES",
                status="EXPECTED",
            ),
            Participant(
                id="P_UNPLACED_01",
                name="Aditya Nair",
                contingent_id="C01",
                college="IIT Bombay",
                gender="MALE",
                age=20,
                accessibility_needs="",
                housing_preference="standard",
                arrival_at=datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc),
                departure_at=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
                accommodation_requested="YES",
                status="EXPECTED",
            ),
        ]
        session.add_all(participants)
        session.commit()
        yield session


# -----------------------------------------------------------------------------
# TEST 1: Concurrency (two organisers allocating same bed -> exactly one 409)
# -----------------------------------------------------------------------------
def test_concurrent_bed_allocation(ops_session: Session):
    """Two organisers allocating the same bed concurrently: exactly one success and one clear 409."""
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Lead 1")
    target_bed = "B1-0-01-bed1"

    req1 = ManualAssignRequest(
        participant_id="P_MALE_01",
        target_bed_key=target_bed,
        target_room_id="B1-0-01",
        reason="Allocating bed to Aarav",
    )
    req2 = ManualAssignRequest(
        participant_id="P_MALE_02",
        target_bed_key=target_bed,
        target_room_id="B1-0-01",
        reason="Allocating bed to Rohan",
    )

    results = []
    errors = []

    def run_assign(req):
        try:
            with Session(ops_session.bind) as sess:
                res = manual_assign(sess, req, lead_actor)
                results.append(res)
        except (FestOSError, VersionConflictError) as ex:
            errors.append(ex)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_assign, req1)
        f2 = executor.submit(run_assign, req2)
        concurrent.futures.wait([f1, f2])

    assert len(results) == 1, "Exactly one thread must succeed"
    assert len(errors) == 1, "Exactly one thread must fail"
    err = errors[0]
    assert err.status_code == 409, f"Expected 409 conflict, got {err.status_code}"
    assert err.code == "VERSION_CONFLICT"



# -----------------------------------------------------------------------------
# TEST 2: Checkout then immediate re-allocation blocked until cleaning complete
# -----------------------------------------------------------------------------
def test_checkout_blocks_immediate_allocation_until_cleaning_completes(ops_session: Session):
    """Checkout starts cleaning buffer timer; immediate check-in is blocked until cleaning completes."""
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Lead 1")

    # 1. Assign P_MALE_01 to B1-0-01
    manual_assign(
        ops_session,
        ManualAssignRequest(
            participant_id="P_MALE_01",
            target_bed_key="B1-0-01-bed1",
            target_room_id="B1-0-01",
            reason="Checkin preparation",
        ),
        lead_actor,
    )

    # 2. P_MALE_01 checks in
    checkin_participant(
        ops_session,
        CheckinRequest(participant_id="P_MALE_01", client_op_id="op_in_01"),
        lead_actor,
    )

    # 3. P_MALE_01 checks out
    checkout_res = checkout_participant(
        ops_session,
        CheckoutRequest(participant_id="P_MALE_01", client_op_id="op_out_01"),
        lead_actor,
    )
    assert checkout_res["room_status"] == "CLEANING"
    assert checkout_res["cleaning_buffer_minutes"] == 180

    # Room is in CLEANING
    room = ops_session.get(Room, "B1-0-01")
    assert room.cleaning_status == "CLEANING"

    # 4. P_MALE_02 attempts check-in to B1-0-01: must be blocked!
    # Assign P_MALE_02 to B1-0-01
    manual_assign(
        ops_session,
        ManualAssignRequest(
            participant_id="P_MALE_02",
            target_bed_key="B1-0-01-bed2",
            target_room_id="B1-0-01",
            reason="Assigning bed in same room",
        ),
        lead_actor,
    )

    with pytest.raises(FestOSError) as exc_info:
        checkin_participant(
            ops_session,
            CheckinRequest(participant_id="P_MALE_02", client_op_id="op_in_02"),
            lead_actor,
        )
    assert exc_info.value.code == "CONSTRAINT_VIOLATION"
    assert "not READY" in exc_info.value.message
    assert "alternative_rooms" in exc_info.value.details

    # 5. Housekeeping completes cleaning
    complete_room_cleaning(ops_session, room_id="B1-0-01", actor=lead_actor, notes="Sanitized")
    room_after = ops_session.get(Room, "B1-0-01")
    assert room_after.status == "READY"
    assert room_after.cleaning_status == "READY"

    # 6. Now P_MALE_02 checks in successfully!
    success_in = checkin_participant(
        ops_session,
        CheckinRequest(participant_id="P_MALE_02", client_op_id="op_in_02"),
        lead_actor,
    )
    assert success_in["status"] == "CHECKED_IN"


# -----------------------------------------------------------------------------
# TEST 3: Cancellation frees bed and creates a suggestion, NOT a change
# -----------------------------------------------------------------------------
def test_cancellation_frees_bed_and_creates_suggestion(ops_session: Session):
    """Cancellation frees the bed and creates an advisory suggestion, never auto-applying."""
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Lead 1")

    # Assign P_MALE_01 to B1-0-01
    manual_assign(
        ops_session,
        ManualAssignRequest(
            participant_id="P_MALE_01",
            target_bed_key="B1-0-01-bed1",
            target_room_id="B1-0-01",
            reason="Initial assignment",
        ),
        lead_actor,
    )

    # Participant cancels
    publish(
        "participant.status_changed",
        {
            "participant_id": "P_MALE_01",
            "previous_status": "EXPECTED",
            "new_status": "CANCELLED",
            "_session": ops_session,
        },
    )

    # Verify bed was freed
    ops_session.expire_all()
    stay = ops_session.exec(
        select(StayAssignment).where(StayAssignment.participant_id == "P_MALE_01")
    ).first()
    assert stay.status == "CANCELLED"

    # Verify unplaced participant was NOT auto-placed
    unplaced_stay = ops_session.exec(
        select(StayAssignment).where(
            StayAssignment.participant_id == "P_UNPLACED_01",
            StayAssignment.status == "ACTIVE",
        )
    ).first()
    assert unplaced_stay is None, "Unplaced participant must NEVER be auto-placed"

    # Verify reallocation suggestion was generated
    suggestions = ops_session.exec(
        select(BedReallocationSuggestion).where(
            BedReallocationSuggestion.freed_bed_key == "B1-0-01-bed1"
        )
    ).all()
    assert len(suggestions) >= 1
    sug = suggestions[0]
    assert sug.status == "PENDING"
    assert sug.freed_by_participant_id == "P_MALE_01"
    assert sug.suggested_participant_id in ["P_UNPLACED_01", "P_MALE_02"]
    assert "C01" in sug.cohesion_benefit



# -----------------------------------------------------------------------------
# TEST 4: Hard override without Director role or reason is rejected
# -----------------------------------------------------------------------------
def test_hard_override_without_director_or_reason_is_rejected(ops_session: Session):
    """Overriding hard accessibility or gender rules requires Director role and reason."""
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Accommodation Lead")
    director_actor = Actor(id="dir_1", role=Role.FESTIVAL_DIRECTOR.value, name="Director")

    # 1. Male assigned to Girls room G1-0-01 without Director override -> Rejected
    with pytest.raises(FestOSError) as exc_info:
        manual_assign(
            ops_session,
            ManualAssignRequest(
                participant_id="P_MALE_01",
                target_bed_key="G1-0-01-bed1",
                target_room_id="G1-0-01",
                reason="Cross-block placement",
                override_hard_constraint=False,
            ),
            lead_actor,
        )
    assert "GENDER_MISMATCH" in exc_info.value.message or "cannot be assigned" in exc_info.value.message

    # 2. Attempting override with Accommodation Lead (non-Director) -> Rejected
    with pytest.raises(FestOSError) as exc_info:
        manual_assign(
            ops_session,
            ManualAssignRequest(
                participant_id="P_MALE_01",
                target_bed_key="G1-0-01-bed1",
                target_room_id="G1-0-01",
                reason="Cross-block placement",
                override_hard_constraint=True,
            ),
            lead_actor,
        )
    assert "Festival Director" in exc_info.value.message

    # 3. Director attempting override with empty reason -> Rejected
    with pytest.raises(FestOSError) as exc_info:
        manual_assign(
            ops_session,
            ManualAssignRequest(
                participant_id="P_MALE_01",
                target_bed_key="G1-0-01-bed1",
                target_room_id="G1-0-01",
                reason="",
                override_hard_constraint=True,
            ),
            director_actor,
        )
    assert "reason" in exc_info.value.message.lower()

    # 4. Director with mandatory reason -> Succeeded and writes to override register
    result = manual_assign(
        ops_session,
        ManualAssignRequest(
            participant_id="P_MALE_01",
            target_bed_key="G1-0-01-bed1",
            target_room_id="G1-0-01",
            reason="Emergency isolated quarantine single room placement",
            override_hard_constraint=True,
        ),
        director_actor,
    )
    assert result["override_id"] is not None
    assert result["decision_card_id"] is not None


# -----------------------------------------------------------------------------
# TEST 5: Minimal-change repair after closing a block
# -----------------------------------------------------------------------------
def test_repair_after_closing_block(ops_session: Session):
    """Repair after closing a block never violates hard constraints and reports a correct diff."""
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Lead 1")

    # Generate candidate plans first
    generate_plans(ops_session, ["C"])

    # Commit Plan C to LIVE
    plan_c = ops_session.exec(
        select(AccommodationPlan).where(AccommodationPlan.kind == "C")
    ).first()
    plan_c.status = "LIVE"
    ops_session.add(plan_c)
    ops_session.commit()

    # Close block B1
    close_block_rooms(ops_session, block="B1", actor=lead_actor, reason="Water leakage repair")

    # Run minimal-change repair
    diff = repair_accommodation(
        ops_session,
        RepairPlanRequest(plan_id=plan_c.plan_id, closed_block="B1"),
    )

    assert diff["people_moved"] > 0
    assert diff["candidate_plan_id"] is not None
    assert "moves" in diff

    # Verify relocated participants do not violate hard constraints
    repair_plan_id = diff["candidate_plan_id"]
    new_stays = ops_session.exec(
        select(StayAssignment).where(StayAssignment.plan_id == repair_plan_id)
    ).all()

    for s in new_stays:
        p = ops_session.get(Participant, s.participant_id)
        if s.room_id:
            rm = ops_session.get(Room, s.room_id)
            assert rm.block != "B1", "No participant may be in closed block B1"
            if p and p.gender.upper() == "MALE":
                assert rm.gender_class.lower() in ["boys", "male", "neutral"]
            if p and p.gender.upper() == "FEMALE":
                assert rm.gender_class.lower() in ["girls", "female", "neutral"]


# -----------------------------------------------------------------------------
# TEST 6: Offline sync is idempotent when replayed
# -----------------------------------------------------------------------------
def test_offline_sync_idempotent_replay(ops_session: Session):
    """Offline operation batch is idempotent when replayed."""
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Lead 1")

    # Assign P_MALE_01 and P_MALE_02
    manual_assign(
        ops_session,
        ManualAssignRequest(
            participant_id="P_MALE_01",
            target_bed_key="B2-0-01-bed1",
            target_room_id="B2-0-01",
            reason="Prep",
        ),
        lead_actor,
    )
    manual_assign(
        ops_session,
        ManualAssignRequest(
            participant_id="P_MALE_02",
            target_bed_key="B2-0-01-bed2",
            target_room_id="B2-0-01",
            reason="Prep",
        ),
        lead_actor,
    )

    batch_req = SyncBatchRequest(
        device_id="desk_tablet_01",
        sync_batch_id="batch_100",
        operations=[
            OfflineOperation(
                client_op_id="client_op_1",
                op_type="CHECKIN",
                participant_id="P_MALE_01",
            ),
            OfflineOperation(
                client_op_id="client_op_2",
                op_type="CHECKIN",
                participant_id="P_MALE_02",
            ),
        ],
    )

    # Run 1: operations applied
    res1 = sync_offline_operations(ops_session, batch_req, lead_actor)
    assert res1.applied_count == 2
    assert res1.duplicate_count == 0

    # Run 2: exact same batch replayed -> DUPLICATE_IGNORED
    res2 = sync_offline_operations(ops_session, batch_req, lead_actor)
    assert res2.applied_count == 0
    assert res2.duplicate_count == 2
    for r in res2.results:
        assert r.status == "DUPLICATE_IGNORED"


# -----------------------------------------------------------------------------
# ACCEPTANCE FLOW:
# Commit Plan C to LIVE with approval -> close a block -> receive minimal-change
# repair proposal -> approve it -> see live assignments change with audit entries.
# -----------------------------------------------------------------------------
def test_acceptance_flow(ops_session: Session):
    """Full acceptance workflow:

    1. Propose committing plan C to LIVE.
    2. Director approves commitment.
    3. Close block B2.
    4. Generate minimal-change repair proposal.
    5. Approve repair proposal.
    6. Verify live assignments changed with audit entries.
    """
    lead_actor = Actor(id="lead_1", role=Role.ACCOMMODATION_LEAD.value, name="Accommodation Lead")
    director_actor = Actor(id="dir_1", role=Role.FESTIVAL_DIRECTOR.value, name="Festival Director")

    # Step 1: Generate Candidate Plan C
    generate_plans(ops_session, ["C"])
    plan_c = ops_session.exec(
        select(AccommodationPlan).where(AccommodationPlan.kind == "C")
    ).first()
    assert plan_c is not None

    # Step 2: Propose committing Plan C to LIVE as Accommodation Lead
    commit_res = commit_plan_to_live(
        ops_session,
        plan_id=plan_c.plan_id,
        actor=lead_actor,
        reason="Initial festival plan proposal",
    )
    # Under budget-unset mode, requires Director approval
    assert commit_res["status"] == "PENDING_APPROVAL"
    assert commit_res["requires_director_approval"] is True
    cs_id = commit_res["change_set_id"]

    # Step 3: Director approves the commit
    from app.models.audit import Approval
    approval = ops_session.exec(select(Approval).where(Approval.change_set_id == cs_id)).first()
    assert approval is not None

    appr_res = approve_request(
        ops_session,
        approval_id=approval.id,
        actor=director_actor,
        reason="Director approval for Plan C operational rollout",
    )
    assert appr_res["status"] == "APPROVED"

    # Plan C is now LIVE
    live_plan = get_live_plan(ops_session)
    assert live_plan is not None
    assert live_plan.plan_id == plan_c.plan_id
    assert live_plan.status == "LIVE"

    initial_live_stays = ops_session.exec(
        select(StayAssignment).where(
            StayAssignment.plan_id == live_plan.plan_id,
            StayAssignment.status == "ACTIVE",
        )
    ).all()
    initial_stays_count = len(initial_live_stays)
    assert initial_stays_count > 0

    # Step 4: Close Block where occupants reside
    first_room_stay = next(s for s in initial_live_stays if s.room_id is not None)
    first_room = ops_session.get(Room, first_room_stay.room_id)
    block_to_close = first_room.block

    close_block_rooms(ops_session, block=block_to_close, actor=lead_actor, reason=f"Plumbing maintenance on {block_to_close}")

    # Step 5: Receive minimal-change repair proposal
    diff = repair_accommodation(
        ops_session,
        RepairPlanRequest(plan_id=live_plan.plan_id, closed_block=block_to_close),
    )
    assert diff["people_moved"] > 0
    candidate_repair_plan_id = diff["candidate_plan_id"]

    # Step 6: Approve the repair proposal via ChangeService
    from app.core.change_service import ChangeRequest, execute_change
    repair_req = ChangeRequest(
        action="accommodation.apply_repair",
        entity_type="accommodation_plan",
        entity_id=candidate_repair_plan_id,
        payload={},
        reason=f"Approved minimal-change repair following block {block_to_close} plumbing maintenance",
        actor=director_actor,
    )
    repair_change_res = execute_change(repair_req, ops_session)
    assert repair_change_res.status == "APPLIED"

    # Step 7: Verify live assignments changed and audit entries exist
    new_live_plan = get_live_plan(ops_session)
    assert new_live_plan.plan_id == candidate_repair_plan_id
    assert new_live_plan.status == "LIVE"

    # Check that closed block has 0 active stays in new live plan
    closed_block_stays = ops_session.exec(
        select(StayAssignment).where(
            StayAssignment.plan_id == new_live_plan.plan_id,
            StayAssignment.status == "ACTIVE",
        )
    ).all()
    for s in closed_block_stays:
        if s.room_id:
            rm = ops_session.get(Room, s.room_id)
            assert rm.block != block_to_close, f"No active stays should be in closed block {block_to_close}"


    # Audit events verify
    audit_events = ops_session.exec(
        select(AuditEvent).where(AuditEvent.action == "accommodation.apply_repair")
    ).all()
    assert len(audit_events) >= 1

    dec_cards = ops_session.exec(
        select(DecisionCard).where(DecisionCard.decision_type == "APPLY_REPAIR_PLAN")
    ).all()
    assert len(dec_cards) >= 1
    assert "Repaired accommodation operations" in dec_cards[0].summary
