# OWNER: P2
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List

from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_seeder
from app.models.accommodation import ExternalProperty, Room

logger = logging.getLogger("festos.seed.accommodation")


@register_seeder(name="seed_accommodation_resources", order=30)
def seed_accommodation_resources(session: Session) -> None:
    """Seed on-campus rooms and external properties into database (order 30)."""
    raw_dir = Path(__file__).resolve().parents[3] / "data" / "raw"

    # 1. Seed on-campus rooms from hostels.csv (200 rooms / 710 beds)
    hostels_file = raw_dir / "hostels.csv"
    if hostels_file.exists():
        with open(hostels_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rooms_to_insert: List[Room] = []
            for row in reader:
                room_id = row["room_id"].strip()
                existing = session.exec(select(Room).where(Room.id == room_id)).first()
                if existing:
                    continue

                accessibility_str = row.get("accessibility", "no").strip().lower()
                is_accessible = accessibility_str == "yes"

                r = Room(
                    id=room_id,
                    block=row["block"].strip(),
                    floor=int(row["floor"].strip()),
                    capacity=int(row["capacity"].strip()),
                    bed_count=int(row["capacity"].strip()),
                    accessible=is_accessible,
                    accessibility=accessibility_str,
                    gender_class=row.get("gender", "UNKNOWN").strip().lower(),
                    status=row.get("status", "available").strip().lower(),
                    cleaning_status="READY",
                    version=1,
                    created_at=now(),
                    updated_at=now(),
                )
                rooms_to_insert.append(r)

            if rooms_to_insert:
                session.add_all(rooms_to_insert)
                session.commit()
                logger.info(f"Seeded {len(rooms_to_insert)} on-campus rooms into room table.")

    # 2. Seed external properties from external_stays.csv (6 properties / 740 beds)
    external_file = raw_dir / "external_stays.csv"
    if external_file.exists():
        with open(external_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            props_to_insert: List[ExternalProperty] = []
            for row in reader:
                prop_id = row["property_id"].strip()
                existing = session.exec(select(ExternalProperty).where(ExternalProperty.id == prop_id)).first()
                if existing:
                    continue

                trans_avail = row.get("transport_availability", "yes").strip().lower()
                is_limited = trans_avail == "limited"

                p = ExternalProperty(
                    id=prop_id,
                    name=row["property_name"].strip(),
                    beds=int(row["beds"].strip()),
                    cost_per_bed_night=float(row["cost_per_bed_per_night"].strip()),
                    distance_km=float(row["distance_km"].strip()),
                    transport_availability=trans_avail,
                    transport_limited=is_limited,
                    accessibility_verified=False,
                    gender_suitability_verified=False,
                    status="ACTIVE",
                    version=1,
                    created_at=now(),
                    updated_at=now(),
                )
                props_to_insert.append(p)

            if props_to_insert:
                session.add_all(props_to_insert)
                session.commit()
                logger.info(f"Seeded {len(props_to_insert)} external properties into external_property table.")
