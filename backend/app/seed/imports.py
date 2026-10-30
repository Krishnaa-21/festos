# OWNER: P2
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from sqlmodel import Session

from app.core.registry import register_seeder
from app.schemas.common import Actor, Role
from app.services.assumptions.service import seed_all_assumptions
from app.services.imports.service import import_file, promote_import_batch

logger = logging.getLogger("festos.seed.imports")

# Topological sequence of raw data files ensuring foreign keys resolve
IMPORT_SEQUENCE: List[str] = [
    "contingents.csv",
    "venues.csv",
    "events.csv",
    "core_team.csv",
    "hostels.csv",
    "external_stays.csv",
    "inventory_logistics.csv",
    "inventory_merch.csv",
    "vendors.csv",
    "participants.csv",
    "registrations.csv",
]


@register_seeder(name="seed_imports", order=10)
def seed_imports(session: Session) -> None:
    """Seed all raw data pack CSVs into canonical tables via the import pipeline."""
    # 1. Ensure all 25 FestOS assumptions are seeded first
    seed_all_assumptions(session)
    session.commit()

    raw_dir = Path(__file__).resolve().parents[3] / "data" / "raw"

    if not raw_dir.exists():
        logger.warning(f"Raw data directory not found at {raw_dir}")
        return

    actor = Actor(id="usr_system_seeder", name="System Seeder", role=Role.FESTIVAL_DIRECTOR.value)


    for filename in IMPORT_SEQUENCE:
        file_path = raw_dir / filename
        if not file_path.exists():
            logger.warning(f"File {filename} not found at {file_path}, skipping...")
            continue

        sheet_name = filename.replace(".csv", "")
        content = file_path.read_bytes()

        logger.info(f"Importing {filename} ({len(content)} bytes)...")
        batch_resp = import_file(
            session=session,
            file_content=content,
            filename=filename,
            sheet_name=sheet_name,
            dry_run=False,
            actor=actor,
        )

        logger.info(
            f"Staged batch {batch_resp.batch_id} for {filename}: "
            f"total={batch_resp.total_rows}, imported={batch_resp.imported_rows}, "
            f"quarantined={batch_resp.quarantined_rows}. Promoting to canonical..."
        )

        # Promote staged records into canonical tables through ChangeService
        result = promote_import_batch(
            session=session,
            batch_id=batch_resp.batch_id,
            actor=actor,
            reason=f"Seeding canonical tables from {filename}",
            dry_run=False,
        )

        if not result.success:
            logger.error(f"Failed to promote batch {batch_resp.batch_id}: {result.error}")
        else:
            logger.info(f"Promoted batch {batch_resp.batch_id} ({filename}) successfully.")
