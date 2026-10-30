# OWNER: P2
import pytest
from app.core.db import get_session
from app.main import app
from app.models.ops import NotificationDeliveryLog, NotificationDraft
from app.schemas.common import Role
from app.services.notifications.public import dependents, risks, summary
from app.services.notifications.service import generate_drafts
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture
def test_engine():
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
    return engine


@pytest.fixture
def test_session(test_engine):
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine):
    def get_test_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_generate_drafts_across_all_audiences(test_session: Session):
    """Requirement 6.14: notification_draft generation per audience from structured change data."""
    context = {
        "vendor_name": "QuickBite",
        "replacement_name": "Campus Caterers",
        "location": "Quadrangle Food Court",
        "affected_slots": ["LUNCH", "DINNER"],
        "lost_capacity": 300,
        "reason": "Health inspection order",
    }
    drafts = generate_drafts(
        event_type="VENDOR_SHUTDOWN",
        context=context,
        session=test_session,
    )
    test_session.commit()

    assert len(drafts) == 5
    audiences = {d.audience for d in drafts}
    expected_audiences = {
        "contingent_leaders",
        "volunteers",
        "vendors",
        "accommodation_coordinators",
        "event_organisers",
    }
    assert audiences == expected_audiences
    for d in drafts:
        assert d.status == "PENDING_APPROVAL"
        assert d.requires_approval is True
        assert d.id is not None
        assert len(d.body) > 0


def test_cannot_send_notification_without_approval(client: TestClient, test_session: Session):
    """Requirement: notifications cannot be sent without approval."""
    # 1. Create a draft in PENDING_APPROVAL status
    draft = NotificationDraft(
        id="ndr_unapproved_test",
        audience="volunteers",
        channel="WHATSAPP",
        subject="URGENT: Dining Hall Change",
        body="Please direct all contingents to Dining Hall B.",
        status="PENDING_APPROVAL",
        requires_approval=True,
    )
    test_session.add(draft)
    test_session.commit()

    # 2. Attempt to mock send without approval
    resp = client.post(
        f"/api/v1/notifications/drafts/{draft.id}/send",
        headers={"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value},
    )
    # Must fail with 422 CONSTRAINT_VIOLATION
    assert resp.status_code == 422
    err_body = resp.json()["error"]
    assert err_body["code"] == "CONSTRAINT_VIOLATION"
    assert "approval" in err_body["message"].lower()

    # Verify no delivery log was created
    logs = test_session.exec(select(NotificationDeliveryLog)).all()
    assert len(logs) == 0


def test_approve_and_send_notification_lifecycle(client: TestClient, test_session: Session):
    """Approve a draft as Director/Lead, then send successfully and verify delivery log."""
    draft = NotificationDraft(
        id="ndr_approval_flow_test",
        audience="contingent_leaders",
        channel="SMS",
        subject="Catering Update",
        body="Lunch vouchers valid at Arena Counters.",
        status="PENDING_APPROVAL",
        requires_approval=True,
    )
    test_session.add(draft)
    test_session.commit()

    # 1. Approve draft
    resp_approve = client.post(
        f"/api/v1/notifications/drafts/{draft.id}/approve",
        headers={"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value},
    )
    assert resp_approve.status_code == 200
    approved_data = resp_approve.json()["data"]
    assert approved_data["status"] == "APPROVED"
    assert approved_data["approved_by"] is not None

    # 2. Send draft
    resp_send = client.post(
        f"/api/v1/notifications/drafts/{draft.id}/send",
        headers={"X-Actor-Role": Role.FESTIVAL_DIRECTOR.value},
    )
    assert resp_send.status_code == 200
    send_data = resp_send.json()["data"]
    assert send_data["status"] == "DELIVERED"
    assert send_data["id"] is not None

    # 3. Verify Delivery Log in database
    log = test_session.get(NotificationDeliveryLog, send_data["id"])
    assert log is not None
    assert log.draft_id == draft.id
    assert log.audience == "contingent_leaders"
    assert log.status == "DELIVERED"


def test_edit_draft_content(client: TestClient, test_session: Session):
    """Verify templates/drafts can be edited before approval and dispatch."""
    draft = NotificationDraft(
        id="ndr_edit_test",
        audience="vendors",
        channel="EMAIL",
        subject="Draft Notice",
        body="Initial body text.",
        status="PENDING_APPROVAL",
        requires_approval=True,
    )
    test_session.add(draft)
    test_session.commit()

    patch_payload = {
        "subject": "Updated Notice for Counter Managers",
        "body": "Revised instructions for evening dinner service.",
    }
    resp = client.patch(
        f"/api/v1/notifications/drafts/{draft.id}",
        json=patch_payload,
        headers={"X-Actor-Role": Role.FOOD_OPS_MANAGER.value},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["subject"] == patch_payload["subject"]
    assert data["body"] == patch_payload["body"]


def test_notifications_public_interface(test_session: Session):
    """Verify public summary, risks, and dependents in notifications.public."""
    draft = NotificationDraft(
        id="ndr_pub_test",
        audience="event_organisers",
        channel="APP",
        subject="URGENT Schedule Change",
        body="Alert body",
        status="PENDING_APPROVAL",
        requires_approval=True,
    )
    test_session.add(draft)
    test_session.commit()

    s = summary(test_session)
    assert s["total_drafts"] >= 1
    assert s["pending_approval"] >= 1

    r = risks(test_session)
    assert len(r) >= 1
    assert any(item.kind == "UNAPPROVED_CRITICAL_NOTIFICATION" for item in r)

    d = dependents(test_session, "notification_draft", draft.id)
    assert len(d) > 0
