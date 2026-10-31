#!/usr/bin/env python3
"""Generate Deliverable 02 Sample Plans and Verification Reports into submission/sample_plans/.

Usage:
    PYTHONPATH=backend python3 scripts/generate_sample_plans.py [--output-dir submission/sample_plans]
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.db import get_engine, init_db  # noqa: E402
from app.schemas.common import Actor, Role  # noqa: E402
from app.services.reports.generators import (  # noqa: E402
    gen_accommodation_plan_a,
    gen_accommodation_plan_b,
    gen_accommodation_plan_c,
    gen_data_quality_report,
    gen_inventory_plan,
    gen_reconciliation_report,
    gen_schedule_plan,
)
from sqlmodel import Session  # noqa: E402

logger = logging.getLogger("festos.generate_sample_plans")


def get_git_commit_hash() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def generate_all(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    init_db()

    actor = Actor(
        id="usr_sample_generator",
        name="Submission Deliverables Generator",
        role=Role.FESTIVAL_DIRECTOR.value,
    )

    commit_hash = get_git_commit_hash()
    timestamp = datetime.now(timezone.utc).isoformat()

    print(f"Generating Deliverable 02 plans into {output_dir}...")
    print(f"Commit: {commit_hash} | Timestamp: {timestamp}")

    with Session(get_engine()) as session:
        reports = {
            "accommodation_plan_A.csv": gen_accommodation_plan_a(session, actor, mask=False)[0],
            "accommodation_plan_B.csv": gen_accommodation_plan_b(session, actor, mask=False)[0],
            "accommodation_plan_C.csv": gen_accommodation_plan_c(session, actor, mask=False)[0],
            "schedule_plan.csv": gen_schedule_plan(session, actor, mask=False)[0],
            "inventory_plan.csv": gen_inventory_plan(session, actor, mask=False)[0],
            "reconciliation_report.csv": gen_reconciliation_report(session, actor, mask=False)[0],
            "data_quality_report.csv": gen_data_quality_report(session, actor, mask=False)[0],
        }

        for filename, content in reports.items():
            dest = output_dir / filename
            dest.write_text(content, encoding="utf-8")
            size_kb = len(content.encode("utf-8")) / 1024
            print(f"  [OK] {filename:28} ({size_kb:.1f} KB)")

    print(f"\n[SUCCESS] All 7 submission sample plans and reports successfully generated in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate sample plans and reports for FestOS submission")
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "submission" / "sample_plans"), help="Target directory")
    args = parser.parse_args()
    generate_all(Path(args.output_dir))


if __name__ == "__main__":
    main()
