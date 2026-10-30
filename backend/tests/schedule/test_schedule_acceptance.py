# OWNER: P1
import pytest
from app.core.db import init_db
from app.main import app
from app.seed.registry import run_seeders
from starlette.testclient import TestClient

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_schedule_db():
    init_db()
    run_seeders(reset=True)


def test_acceptance_workflow_schedule_generation_and_restoration():
    """ACCEPTANCE:

    1. Generate a schedule from the pack (labelled ASSUMED)
    2. See conflicts by type
    3. Apply a ranked resolution
    4. Restore a previous schedule version
    """
    headers = {
        "X-Actor-Role": "EVENT_LEAD",
        "X-Actor-Id": "usr_test_scheduler",
        "Idempotency-Key": "test_idemp_gen_01",
    }

    # 1. Generate schedule from the pack
    gen_res = client.post(
        "/api/v1/schedule/generate",
        json={
            "plan_name": "Acceptance Plan Alpha",
            "solver": "greedy",
            "include_late_wave": True,
            "wildcard_finals": False,
        },
        headers=headers,
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()["data"]
    version_id = gen_data["version_id"]
    assert gen_data["status"] == "ASSUMED"
    assert gen_data["total_sessions"] > 150
    assert gen_data["unscheduled_registrations"] > 900
    assert "prototype_benchmark" in gen_data

    # 2. See conflicts by type
    conf_res = client.get("/api/v1/schedule/conflicts", headers=headers)
    assert conf_res.status_code == 200
    conf_data = conf_res.json()["data"]
    assert "items" in conf_data

    # Check unscheduled report
    unsched_res = client.get("/api/v1/schedule/unscheduled", headers=headers)
    assert unsched_res.status_code == 200
    unsched_data = unsched_res.json()["data"]
    assert unsched_data["unscheduled_count"] > 0
    assert "reasons_breakdown" in unsched_data

    # Check Gantt timeline data
    timeline_res = client.get("/api/v1/schedule/timeline", headers=headers)
    assert timeline_res.status_code == 200
    timeline_data = timeline_res.json()["data"]
    assert len(timeline_data["venues"]) == 9

    # Check provisional teams (1,810 team registrations reconciliation)
    team_res = client.get("/api/v1/events/teams/provisional", headers=headers)
    assert team_res.status_code == 200
    team_data = team_res.json()["data"]
    assert team_data["total_team_registrations"] == 1810
    assert team_data["label"] == "ASSUMED"

    # Check judge registry gaps
    judge_res = client.get("/api/v1/events/judges", headers=headers)
    assert judge_res.status_code == 200
    judge_data = judge_res.json()["data"]
    assert judge_data["unassigned_slots_count"] > 0

    # 3. Create a conflict to test ranked resolution recommendation
    # Intentionally move session ses_0002 to overlap with ses_0001
    sessions_res = client.get("/api/v1/schedule/sessions", headers=headers)
    sessions = sessions_res.json()["data"]["items"]
    assert len(sessions) >= 2

    s1 = sessions[0]
    s2 = sessions[1]

    # Move s2 to s1's start_at and same venue to create a venue double booking conflict
    move_res = client.post(
        f"/api/v1/schedule/sessions/{s2['id']}/move",
        json={"new_start_at": s1["start_at"]},
        headers=headers,
    )
    assert move_res.status_code == 200

    # Refresh conflicts list
    conf_refresh = client.get("/api/v1/schedule/conflicts", headers=headers)
    assert conf_refresh.status_code == 200
    active_confs = conf_refresh.json()["data"]["items"]
    assert len(active_confs) > 0

    target_conflict = active_confs[0]
    cfl_id = target_conflict["id"]

    # Request ranked resolutions
    res_rec = client.get(f"/api/v1/schedule/conflicts/{cfl_id}/resolutions", headers=headers)
    assert res_rec.status_code == 200
    rec_data = res_rec.json()["data"]
    assert len(rec_data["recommendations"]) > 0
    top_rec = rec_data["recommendations"][0]
    assert top_rec["rank"] == 1

    # Apply the top ranked resolution
    apply_res = client.post(
        f"/api/v1/schedule/conflicts/{cfl_id}/apply-resolution",
        json={
            "action": top_rec["action"],
            "payload": top_rec["payload"],
            "reason": "Applied ranked resolution #1",
        },
        headers=headers,
    )
    assert apply_res.status_code == 200

    # 4. Restore the original schedule version (requires FESTIVAL_DIRECTOR due to HIGH risk)
    dir_headers = {
        "X-Actor-Role": "FESTIVAL_DIRECTOR",
        "X-Actor-Id": "usr_director_01",
        "Idempotency-Key": "test_idemp_restore_01",
    }
    restore_res = client.post(
        f"/api/v1/schedule/versions/{version_id}/restore",
        json={"reason": "Restored baseline plan by festival director"},
        headers=dir_headers,
    )
    assert restore_res.status_code == 200
    restore_data = restore_res.json()["data"]
    assert restore_data["status"] == "APPLIED"
    assert restore_data["data"]["restored_version_id"] == version_id
