# OWNER: P3
from datetime import timedelta

import pytest
from app.core.approvals import approve_request
from app.core.audit import record, verify_chain
from app.core.clock import now
from app.core.db import get_engine, init_db
from app.core.masking import mask_fields
from app.core.overrides import record as record_override
from app.core.rbac import has_permission
from app.main import app
from app.models.audit import Approval, AuditEvent, BreakGlassGrant, User
from app.schemas.common import Actor, Role
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture
def db_session():
    engine = get_engine()
    init_db(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client():
    return TestClient(app)


# -------------------------------------------------------------
# 1. PARAMETRIZED RBAC ALLOW / DENY MATRIX
# -------------------------------------------------------------
@pytest.mark.parametrize(
    "role,permission,expected_allowed",
    [
        # Festival Director has universal permissions
        (Role.FESTIVAL_DIRECTOR.value, "audit:read", True),
        (Role.FESTIVAL_DIRECTOR.value, "accommodation:write", True),
        (Role.FESTIVAL_DIRECTOR.value, "finance:write", True),
        (Role.FESTIVAL_DIRECTOR.value, "checkin:write", True),
        # Accommodation Lead
        (Role.ACCOMMODATION_LEAD.value, "accommodation:read", True),
        (Role.ACCOMMODATION_LEAD.value, "accommodation:write", True),
        (Role.ACCOMMODATION_LEAD.value, "accommodation:approve", True),
        (Role.ACCOMMODATION_LEAD.value, "finance:write", False),
        (Role.ACCOMMODATION_LEAD.value, "events:write", False),
        # Event Lead
        (Role.EVENT_LEAD.value, "events:write", True),
        (Role.EVENT_LEAD.value, "schedule:write", True),
        (Role.EVENT_LEAD.value, "accommodation:write", False),
        (Role.EVENT_LEAD.value, "finance:write", False),
        # Logistics Manager
        (Role.LOGISTICS_MANAGER.value, "logistics:write", True),
        (Role.LOGISTICS_MANAGER.value, "inventory:write", True),
        (Role.LOGISTICS_MANAGER.value, "events:write", False),
        (Role.LOGISTICS_MANAGER.value, "accommodation:write", False),
        # Merchandise Manager
        (Role.MERCHANDISE_MANAGER.value, "merchandise:write", True),
        (Role.MERCHANDISE_MANAGER.value, "food:write", False),
        (Role.MERCHANDISE_MANAGER.value, "accommodation:write", False),
        # Food Ops Manager
        (Role.FOOD_OPS_MANAGER.value, "food:write", True),
        (Role.FOOD_OPS_MANAGER.value, "vendors:write", True),
        (Role.FOOD_OPS_MANAGER.value, "schedule:write", False),
        # Finance Manager
        (Role.FINANCE_MANAGER.value, "finance:write", True),
        (Role.FINANCE_MANAGER.value, "finance:approve", True),
        (Role.FINANCE_MANAGER.value, "accommodation:write", False),
        (Role.FINANCE_MANAGER.value, "events:write", False),
        # Volunteer (limited check-in and scan)
        (Role.VOLUNTEER.value, "checkin:write", True),
        (Role.VOLUNTEER.value, "merchandise:write", True),
        (Role.VOLUNTEER.value, "audit:read", False),
        (Role.VOLUNTEER.value, "accommodation:write", False),
        (Role.VOLUNTEER.value, "finance:write", False),
        # Auditor (read-only)
        (Role.AUDITOR.value, "audit:read", True),
        (Role.AUDITOR.value, "audit:export", True),
        (Role.AUDITOR.value, "accommodation:read", True),
        (Role.AUDITOR.value, "audit:write", False),
        (Role.AUDITOR.value, "accommodation:write", False),
        (Role.AUDITOR.value, "checkin:write", False),
    ]
)
def test_rbac_allow_deny_matrix(role, permission, expected_allowed):
    actor = Actor(id="test_user", name="Test User", role=role)
    assert has_permission(actor, permission) == expected_allowed


# -------------------------------------------------------------
# 2. FIELD-LEVEL MASKING PER ROLE & BREAK-GLASS ELEVATION
# -------------------------------------------------------------
def test_masking_per_role(db_session: Session):
    sample_participant = {
        "id": "P10099",
        "name": "Jane Doe",
        "phone": "+91-98765-43210",
        "email": "jane.doe@college.edu",
        "medical_notes": "Severe peanut allergy",
        "accessibility_details": "Requires ground floor room",
        "room_number": "H2-104",
        "guardian_phone": "+91-98765-11111"
    }

    # Festival Director: Full access
    director = Actor(id="usr_dir", name="Director", role=Role.FESTIVAL_DIRECTOR.value)
    unmasked = mask_fields(sample_participant, director, "participant:P10099", db_session)
    assert unmasked["phone"] == "+91-98765-43210"
    assert unmasked["email"] == "jane.doe@college.edu"
    assert unmasked["medical_notes"] == "Severe peanut allergy"
    assert unmasked["room_number"] == "H2-104"

    # Volunteer: Strictly masked
    volunteer = Actor(id="usr_vol", name="Volunteer", role=Role.VOLUNTEER.value)
    vol_masked = mask_fields(sample_participant, volunteer, "participant:P10099", db_session)
    assert vol_masked["phone"] == "+91-XXXXX-3210"
    assert vol_masked["email"] == "j***@college.edu"
    assert vol_masked["medical_notes"] == "[PROTECTED MEDICAL DATA]"
    assert vol_masked["room_number"] == "[PROTECTED ROOM DATA]"
    assert vol_masked["guardian_phone"] == "[PROTECTED GUARDIAN DATA]"

    # Accommodation Lead: Room & accessibility visible, contact & medical masked
    accom_lead = Actor(id="usr_acc", name="Accom Lead", role=Role.ACCOMMODATION_LEAD.value)
    acc_masked = mask_fields(sample_participant, accom_lead, "participant:P10099", db_session)
    assert acc_masked["room_number"] == "H2-104"
    assert acc_masked["accessibility_details"] == "Requires ground floor room"
    assert acc_masked["medical_notes"] == "[PROTECTED MEDICAL DATA]"
    assert acc_masked["phone"] == "+91-XXXXX-3210"


def test_break_glass_unmasking_and_expiry(db_session: Session):
    entity_key = "participant:P10099"
    volunteer = Actor(id="usr_vol_test", name="Volunteer", role=Role.VOLUNTEER.value)
    data = {"medical_notes": "Severe asthma"}

    # Initially masked
    res_masked = mask_fields(data, volunteer, entity_key, db_session)
    assert res_masked["medical_notes"] == "[PROTECTED MEDICAL DATA]"

    # Ensure User exists for foreign key constraint
    test_user = db_session.get(User, volunteer.id)
    if not test_user:
        test_user = User(
            id=volunteer.id,
            email="vol.test@festos.internal",
            hashed_password="mock-hashed-pass",
            full_name="Volunteer Test",
            role=Role.VOLUNTEER.value
        )
        db_session.add(test_user)
        db_session.commit()

    import uuid

    # Active break glass grant
    grant_id = f"bgg_{uuid.uuid4().hex[:8]}"
    grant = BreakGlassGrant(
        id=grant_id,
        user_id=volunteer.id,
        entity=entity_key,
        field="medical_notes",
        reason="Emergency medic dispatch",
        expires_at=now() + timedelta(minutes=10),
        is_revoked=False
    )
    db_session.add(grant)
    db_session.commit()

    # Now unmasked via break-glass
    res_unmasked = mask_fields(data, volunteer, entity_key, db_session)
    assert res_unmasked["medical_notes"] == "Severe asthma"

    # Once expired, masked again
    grant.expires_at = now() - timedelta(minutes=1)
    db_session.add(grant)
    db_session.commit()

    res_expired = mask_fields(data, volunteer, entity_key, db_session)
    assert res_expired["medical_notes"] == "[PROTECTED MEDICAL DATA]"


# -------------------------------------------------------------
# 3. AUDIT IMMUTABILITY (UPDATE / DELETE REJECTED)
# -------------------------------------------------------------
def test_audit_immutability(db_session: Session):
    actor = Actor(id="usr_test", name="Tester", role=Role.FESTIVAL_DIRECTOR.value)
    event_id = record(
        session=db_session,
        actor=actor,
        action="test.action",
        entity_type="test_entity",
        entity_id="te_01",
        before={"val": 1},
        after={"val": 2},
        reason="Test run"
    )
    db_session.commit()

    event = db_session.get(AuditEvent, event_id)
    assert event is not None

    # Application-level / DB trigger UPDATE rejection
    event.reason = "Tampered reason"
    with pytest.raises(Exception):
        db_session.add(event)
        db_session.commit()
    db_session.rollback()

    # Application-level / DB trigger DELETE rejection
    event_to_delete = db_session.get(AuditEvent, event_id)
    with pytest.raises(Exception):
        db_session.delete(event_to_delete)
        db_session.commit()
    db_session.rollback()


# -------------------------------------------------------------
# 4. HASH CHAIN CRYPTOGRAPHIC VERIFICATION
# -------------------------------------------------------------
def test_audit_hash_chain_verification(db_session: Session):
    actor = Actor(id="usr_test_chain", name="Chain Tester", role=Role.FESTIVAL_DIRECTOR.value)

    # Record 3 sequential events
    record(db_session, actor, "chain.step1", "item", "it_1", {"v": 1}, {"v": 2})
    db_session.commit()
    record(db_session, actor, "chain.step2", "item", "it_1", {"v": 2}, {"v": 3})
    db_session.commit()
    record(db_session, actor, "chain.step3", "item", "it_1", {"v": 3}, {"v": 4})
    db_session.commit()

    # Verification must pass
    result = verify_chain(db_session)
    assert result["valid"] is True
    assert result["verified_count"] >= 3
    assert result["broken_event_id"] is None


# -------------------------------------------------------------
# 5. APPROVAL FRAMEWORK & EXECUTION OF STORED CHANGE
# -------------------------------------------------------------
def test_approval_executes_stored_change(db_session: Session):
    from app.core.change_service import ChangeRequest, execute_change

    # Create high-risk change request by non-director actor
    actor_acc = Actor(id="usr_acc_test", name="Accom Lead", role=Role.ACCOMMODATION_LEAD.value)
    req = ChangeRequest(
        action="example.create_item",
        entity_type="example_item",
        entity_id="ex_appr_99",
        payload={"name": "High Risk Item", "is_high_risk": True},
        reason="Testing approval execution",
        actor=actor_acc
    )

    change_res = execute_change(req, db_session)
    assert change_res.status == "PENDING_APPROVAL"
    assert change_res.change_set_id is not None

    # Retrieve created approval
    approval = db_session.exec(
        select(Approval).where(Approval.change_set_id == change_res.change_set_id)
    ).first()
    assert approval is not None
    assert approval.status == "PENDING"

    # Approving without reason fails
    director = Actor(id="usr_dir_test", name="Festival Director", role=Role.FESTIVAL_DIRECTOR.value)
    with pytest.raises(Exception):
        approve_request(db_session, approval.id, director, reason="")

    # Approve with mandatory reason executes change
    approve_res = approve_request(
        session=db_session,
        approval_id=approval.id,
        actor=director,
        reason="Approved after safety committee review"
    )
    assert approve_res["status"] == "APPROVED"
    assert approve_res["execution_result"]["status"] == "CREATED"


# -------------------------------------------------------------
# 6. OVERRIDE MANDATORY REASON ENFORCEMENT
# -------------------------------------------------------------
def test_override_requires_mandatory_reason(db_session: Session):
    director = Actor(id="usr_dir_test", name="Festival Director", role=Role.FESTIVAL_DIRECTOR.value)

    # Blank reason fails
    with pytest.raises(Exception):
        record_override(
            session=db_session,
            entity_type="room",
            entity_id="R101",
            constraint_code="OVERCAPACITY",
            reason="   ",
            actor=director
        )

    # Valid reason succeeds
    ovr = record_override(
        session=db_session,
        entity_type="room",
        entity_id="R101",
        constraint_code="OVERCAPACITY",
        reason="Contingent leader overflow accommodation authorized",
        actor=director
    )
    assert ovr.id.startswith("ovr_")
    assert ovr.status == "ACTIVE"
