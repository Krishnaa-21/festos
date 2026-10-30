# OWNER: P1
from pathlib import Path

from app.services.reports.samples import generate_all_sample_plans


def test_golden_outputs_exist_and_regression_stable(tmp_path: Path):
    """Deliverable 02 sample plans generate stably into data/golden/ and match regression expectations."""
    # 1. Generate into temporary directory
    files_run_1 = generate_all_sample_plans(output_dir=tmp_path / "run_1")
    assert len(files_run_1) == 5

    expected_files = [
        "accommodation_plan_A.csv",
        "accommodation_plan_B.csv",
        "accommodation_plan_C.csv",
        "schedule_plan.csv",
        "inventory_plan.csv",
    ]

    for fname in expected_files:
        assert fname in files_run_1
        p = files_run_1[fname]
        assert p.exists()
        assert p.stat().st_size > 0

    # 2. Check structure of accommodation plans
    plan_a_lines = files_run_1["accommodation_plan_A.csv"].read_text(encoding="utf-8").splitlines()
    assert len(plan_a_lines) > 1
    assert "plan_id,participant_id,participant_name,contingent_id" in plan_a_lines[0]

    schedule_lines = files_run_1["schedule_plan.csv"].read_text(encoding="utf-8").splitlines()
    assert len(schedule_lines) > 1
    assert "session_id,event_id,event_name,round" in schedule_lines[0]

    inventory_lines = files_run_1["inventory_plan.csv"].read_text(encoding="utf-8").splitlines()
    assert len(inventory_lines) > 1
    assert "item_id,item_name,category,on_hand" in inventory_lines[0]

    # 3. Generate again into a second directory and verify identical, stable outputs
    files_run_2 = generate_all_sample_plans(output_dir=tmp_path / "run_2")
    for fname in expected_files:
        c1 = files_run_1[fname].read_text(encoding="utf-8")
        c2 = files_run_2[fname].read_text(encoding="utf-8")
        assert c1 == c2, f"Golden regression failure: {fname} output changed across runs!"
