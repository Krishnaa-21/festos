# OWNER: P1
"""Tests for transactional merchandise issuance, concurrency, duplicate prevention, and voiding."""
import threading
import uuid
from typing import List

import pytest
from app.core.db import get_engine, init_db
from app.main import app
from app.models.participants import Participant
from app.seed.registry import run_seeders
from sqlmodel import Session
from starlette.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_merch_db():
    init_db()
    run_seeders(reset=False)


def test_concurrent_issuance_produces_exactly_one_success():
    """Two volunteers issuing the same item to the same participant simultaneously produce exactly one success."""
    pid = f"p_concur_{uuid.uuid4().hex[:8]}"
    with Session(get_engine()) as session:
        p = Participant(
            id=pid,
            name="Concurrent Entrant",
            status="CHECKED_IN",
            tshirt_size="L",
        )
        session.add(p)
        session.commit()

    headers_vol1 = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_alpha",
        "Idempotency-Key": f"idemp_concurrency_01_{uuid.uuid4().hex[:6]}",
    }
    headers_vol2 = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_beta",
        "Idempotency-Key": f"idemp_concurrency_02_{uuid.uuid4().hex[:6]}",
    }

    results: List[int] = []

    def issue_worker(headers, counter):
        res = client.post(
            "/api/v1/merchandise/issue",
            json={
                "participant_id": pid,
                "item_id": "mch_t_shirt_l",
                "counter_id": counter,
            },
            headers=headers,
        )
        results.append(res.status_code)

    t1 = threading.Thread(target=issue_worker, args=(headers_vol1, "DESK_1"))
    t2 = threading.Thread(target=issue_worker, args=(headers_vol2, "DESK_2"))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one request must succeed with 200, the other must fail with 409 (ALREADY_ISSUED)
    assert 200 in results
    assert 409 in results
    assert results.count(200) == 1
    assert results.count(409) == 1


def test_duplicate_qr_scan_yields_already_issued_with_original_details():
    """Duplicate QR scan/issue returns 409 ALREADY_ISSUED containing original claim timestamp, counter, and staff member."""
    pid = f"p_dup_qr_{uuid.uuid4().hex[:8]}"
    with Session(get_engine()) as session:
        p = Participant(
            id=pid,
            name="QR Duplicate Test",
            status="CHECKED_IN",
            tshirt_size="M",
        )
        session.add(p)
        session.commit()

    headers = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_desk_north",
        "Idempotency-Key": f"idemp_qr_first_scan_{uuid.uuid4().hex[:6]}",
    }

    # First issue
    res1 = client.post(
        "/api/v1/merchandise/issue",
        json={
            "participant_id": pid,
            "item_id": "mch_t_shirt_m",
            "counter_id": "DESK_NORTH",
        },
        headers=headers,
    )
    assert res1.status_code == 200

    # Second issue attempt
    headers2 = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_desk_south",
        "Idempotency-Key": f"idemp_qr_second_scan_{uuid.uuid4().hex[:6]}",
    }
    res2 = client.post(
        "/api/v1/merchandise/issue",
        json={
            "participant_id": pid,
            "item_id": "mch_t_shirt_m",
            "counter_id": "DESK_SOUTH",
        },
        headers=headers2,
    )
    assert res2.status_code == 409
    err = res2.json()["error"]
    assert err["code"] == "ALREADY_ISSUED"
    assert "usr_vol_desk_north" in err["message"]


def test_merged_duplicate_participants_cannot_both_claim():
    """If participant A is merged into canonical participant B, claiming under A and then B is rejected."""
    p_can_id = f"p_canon_{uuid.uuid4().hex[:8]}"
    p_dup_id = f"p_merged_{uuid.uuid4().hex[:8]}"
    with Session(get_engine()) as session:
        # Canonical participant B
        p_canonical = Participant(
            id=p_can_id,
            name="Canonical Attendee",
            status="CHECKED_IN",
            tshirt_size="XL",
        )
        # Duplicate participant A pointing to B
        p_duplicate = Participant(
            id=p_dup_id,
            name="Duplicate Attendee",
            status="MERGED",
            canonical_participant_id=p_can_id,
            tshirt_size="XL",
        )
        session.add(p_canonical)
        session.add(p_duplicate)
        session.commit()

    headers = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_desk",
        "Idempotency-Key": f"idemp_merge_test_01_{uuid.uuid4().hex[:6]}",
    }

    # Claim using the duplicate record ID
    res1 = client.post(
        "/api/v1/merchandise/issue",
        json={
            "participant_id": p_dup_id,
            "item_id": "mch_id_card_na",
            "counter_id": "DESK_MAIN",
        },
        headers=headers,
    )
    assert res1.status_code == 200
    claim_data = res1.json()["data"]
    # Verified: resolved to canonical!
    assert claim_data["canonical_participant_id"] == p_can_id

    # Now attempt to claim using the canonical record ID directly
    headers2 = {
        "X-Actor-Role": "VOLUNTEER",
        "X-Actor-Id": "usr_vol_desk",
        "Idempotency-Key": f"idemp_merge_test_02_{uuid.uuid4().hex[:6]}",
    }
    res2 = client.post(
        "/api/v1/merchandise/issue",
        json={
            "participant_id": p_can_id,
            "item_id": "mch_id_card_na",
            "counter_id": "DESK_MAIN",
        },
        headers=headers2,
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "ALREADY_ISSUED"
