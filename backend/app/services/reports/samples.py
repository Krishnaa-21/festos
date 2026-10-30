# OWNER: P1
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from sqlmodel import Session

from app.core.db import get_engine, init_db
from app.schemas.common import Actor, Role
from app.services.reports.generators import (
    gen_accommodation_plan_a,
    gen_accommodation_plan_b,
    gen_accommodation_plan_c,
    gen_inventory_plan,
    gen_schedule_plan,
)

logger = logging.getLogger("festos.reports.samples")


def generate_all_sample_plans(output_dir: Path | None = None) -> Dict[str, Path]:
    """Generates the deliverable 02 sample plans into data/golden/:
    - accommodation_plan_A.csv
    - accommodation_plan_B.csv
    - accommodation_plan_C.csv
    - schedule_plan.csv
    - inventory_plan.csv
    """
    init_db()

    if output_dir is None:
        # Determine project root data/golden directory
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        output_dir = project_root / "data" / "golden"

    output_dir.mkdir(parents=True, exist_ok=True)

    actor = Actor(
        id="usr_golden_generator",
        name="Deliverable Generator",
        role=Role.FESTIVAL_DIRECTOR.value,
    )

    generated_files: Dict[str, Path] = {}

    with Session(get_engine()) as session:
        plans = {
            "accommodation_plan_A.csv": gen_accommodation_plan_a(session, actor, mask=False)[0],
            "accommodation_plan_B.csv": gen_accommodation_plan_b(session, actor, mask=False)[0],
            "accommodation_plan_C.csv": gen_accommodation_plan_c(session, actor, mask=False)[0],
            "schedule_plan.csv": gen_schedule_plan(session, actor, mask=False)[0],
            "inventory_plan.csv": gen_inventory_plan(session, actor, mask=False)[0],
        }

        for filename, content in plans.items():
            file_path = output_dir / filename
            file_path.write_text(content, encoding="utf-8")
            generated_files[filename] = file_path
            logger.info(f"Generated golden sample plan: {file_path}")

    return generated_files


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Generating Deliverable 02 sample plans into data/golden/...")
    files = generate_all_sample_plans()
    for name, p in files.items():
        print(f"  [OK] {name} -> {p}")
    print("Done. All deliverable 02 sample plans generated successfully.")
