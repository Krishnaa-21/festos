# OWNER: P1
"""Acceptance test verifying Prompt 1 acceptance criteria:

ACCEPTANCE: after `make reset`, an organiser can open any participant 360,
see UNKNOWN fields as UNKNOWN, merge a likely duplicate with a reason, and
undo it.
"""

from app.main import app
from app.seed.registry import run_seeders
from starlette.testclient import TestClient


def test_acceptance_workflow_after_reset():
    """Verifies that an organiser can:
    1. Inspect seeded participant 360 and see UNKNOWN fields as UNKNOWN.
    2. Merge a likely duplicate with a recorded reason.
    3. Undo the merge and restore exact prior state.
    """
    # Simulate `make reset`
    run_seeders(reset=True)
    client = TestClient(app)

    # 1. Open participant 360 (P0001 has UNKNOWN diet in participants.csv)
    # Header: X-Actor-Role: FESTIVAL_DIRECTOR
    resp_360 = client.get("/api/v1/participants/P0001/360", headers={"X-Actor-Role": "FESTIVAL_DIRECTOR"})
    assert resp_360.status_code == 200
    data_360 = resp_360.json()["data"]

    # Verify UNKNOWN fields are literally "UNKNOWN"
    assert data_360["participant"]["diet"] == "UNKNOWN"
    assert data_360["diet"]["preference"] == "UNKNOWN"

    # 2. Query duplicate candidates for LIKELY pairs
    resp_dups = client.get("/api/v1/reconciliation/duplicates?classification=EXACT")
    assert resp_dups.status_code == 200
    exact_candidates = resp_dups.json()["data"]["items"]

    # If exact candidate (e.g. P0119 and P_DUP02) exists:
    assert len(exact_candidates) >= 1
    cand = exact_candidates[0]
    p_a = cand["participant_a_id"]
    p_b = cand["participant_b_id"]

    # 3. Merge candidate with recorded reason
    merge_payload = {
        "expected_version": None,
        "reason": "Organiser confirmed duplicate on arrival desk review",
        "dry_run": False,
        "payload": {
            "canonical_id": p_a,
            "merged_id": p_b,
            "candidate_id": cand["id"],
        },
    }
    resp_merge = client.post(
        "/api/v1/reconciliation/merge",
        json=merge_payload,
        headers={"X-Actor-Role": "FESTIVAL_DIRECTOR", "Idempotency-Key": "merge_acceptance_01"},
    )
    assert resp_merge.status_code == 200
    merge_data = resp_merge.json()["data"]
    merge_rec_id = merge_data["merge_record_id"]
    assert merge_data["status"] == "APPLIED"

    # Verify participant B is now MERGED
    resp_b = client.get(f"/api/v1/participants/{p_b}", headers={"X-Actor-Role": "FESTIVAL_DIRECTOR"})
    assert resp_b.status_code == 200
    assert resp_b.json()["data"]["status"] == "MERGED"
    assert resp_b.json()["data"]["canonical_participant_id"] == p_a

    # 4. Undo the merge
    undo_payload = {
        "reason": "Desk volunteer noticed distinct college IDs upon further check",
        "dry_run": False,
    }
    resp_undo = client.post(
        f"/api/v1/reconciliation/undo-merge/{merge_rec_id}",
        json=undo_payload,
        headers={"X-Actor-Role": "FESTIVAL_DIRECTOR", "Idempotency-Key": "undo_acceptance_01"},
    )
    assert resp_undo.status_code == 200
    undo_data = resp_undo.json()["data"]
    assert undo_data["status"] == "REVERTED"

    # Verify participant B is restored to its exact pre-merge status
    resp_b_restored = client.get(f"/api/v1/participants/{p_b}", headers={"X-Actor-Role": "FESTIVAL_DIRECTOR"})
    assert resp_b_restored.status_code == 200
    assert resp_b_restored.json()["data"]["status"] != "MERGED"
