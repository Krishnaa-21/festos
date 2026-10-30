# OWNER: P1
"""Seeder for contingents, events, participants, registrations, and duplicate candidates.

Order: 15 (after assumptions: 10, before users: 20).
"""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from app.core.clock import now
from app.core.config import settings
from app.core.registry import register_seeder
from app.engines.dedupe import find_duplicate_candidates
from app.models.events import Event
from app.models.participants import (
    Contingent,
    DuplicateCandidate,
    FieldVerification,
    Participant,
    RawRecord,
    Registration,
)

logger = logging.getLogger("festos.seed.participants")


def _find_data_file(filename: str) -> Optional[Path]:
    """Resolves data file path from settings.DATA_DIR or common repo locations."""
    candidates = [
        Path(settings.DATA_DIR) / filename,
        Path("data/raw") / filename,
        Path("../data/raw") / filename,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _parse_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val or val.strip() in ("", "None", "nan"):
        return None
    val = val.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(val, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return None


def _parse_accessibility(val: Optional[str]) -> Dict[str, Any]:
    if not val or val.strip().lower() in ("", "none", "nan"):
        return {}
    v = val.strip()
    v_lower = v.lower()
    return {
        "raw": v,
        "has_need": True,
        "requires_wheelchair": "wheelchair" in v_lower,
        "requires_ground_floor": "ground floor" in v_lower or "wheelchair" in v_lower,
        "visual_assistance": "visual" in v_lower,
        "near_washroom": "washroom" in v_lower,
    }


@register_seeder("participants", order=15)
def seed_participants_pack(session: Session) -> None:
    logger.info("Starting participants, contingents, and registrations ingestion...")

    # 1. Seed Contingents
    ctg_path = _find_data_file("contingents.csv")
    if not ctg_path:
        logger.warning("contingents.csv not found; skipping contingent seed.")
        return

    contingent_rows: List[Contingent] = []
    with open(ctg_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row["contingent_id"].strip()
            # Check if exists
            existing = session.get(Contingent, cid)
            if existing:
                continue

            college = row.get("college", "").strip()
            strength = 0
            try:
                strength = int(row.get("strength_declared", 0))
            except (ValueError, TypeError):
                strength = 0

            contingent = Contingent(
                id=cid,
                code=cid,
                name=f"{college} Contingent",
                college=college,
                leader=row.get("leader", "").strip() or None,
                escort=row.get("escort", "").strip() or None,
                strength_declared=strength,
                preferences=row.get("preferences", "").strip() or None,
                status="ACTIVE",
                created_at=now(),
                updated_at=now(),
            )
            contingent_rows.append(contingent)
            session.add(contingent)

    session.flush()
    logger.info(f"Seeded {len(contingent_rows)} contingents.")

    # 2. Seed Events (so registrations FKs are satisfied)
    evt_path = _find_data_file("events.csv")
    if evt_path:
        with open(evt_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = row["event_id"].strip()
                if not session.get(Event, eid):
                    evt = Event(
                        id=eid,
                        code=eid,
                        name=row.get("event_name", eid).strip(),
                        solo_team="TEAM" if row.get("type", "").strip().lower() == "team" else "SOLO",
                        event_type=row.get("type", "solo").strip().lower(),
                        rounds_text=row.get("rounds", "").strip() or None,
                        duration_min=int(row.get("duration_minutes", 60) or 60),
                        venue_requirements=row.get("venue_requirements", "").strip() or None,
                        equipment_needs=row.get("equipment_needs", "").strip() or None,
                        volunteers_needed=int(row.get("volunteers_needed", 0) or 0),
                        status="ACTIVE",
                        created_at=now(),
                        updated_at=now(),
                    )
                    session.add(evt)
        session.flush()

    # 3. Seed Participants
    par_path = _find_data_file("participants.csv")
    if not par_path:
        logger.warning("participants.csv not found; skipping participant seed.")
        return

    participants_for_dedupe: List[Dict[str, Any]] = []
    participant_count = 0

    with open(par_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["participant_id"].strip()
            existing = session.get(Participant, pid)
            if existing:
                continue

            name = row.get("name", "").strip()
            college = row.get("college", "").strip() or None
            cid = row.get("contingent_id", "").strip() or None
            raw_gender = row.get("gender_as_given", "").strip()
            gender = raw_gender if raw_gender else "UNKNOWN"

            raw_diet = row.get("dietary_needs", "").strip()
            diet = raw_diet if raw_diet else "UNKNOWN"

            raw_age = row.get("age", "").strip()
            age: Optional[int] = None
            if raw_age:
                try:
                    age = int(raw_age)
                except ValueError:
                    age = None

            phone = row.get("contact", "").strip() or None
            access_dict = _parse_accessibility(row.get("accessibility_needs"))

            raw_accom = row.get("accommodation_requested", "").strip().lower()
            if raw_accom in ("yes", "y", "true"):
                accom_req = "YES"
            elif raw_accom in ("no", "n", "false"):
                accom_req = "NO"
            else:
                accom_req = "UNKNOWN"

            raw_tshirt = row.get("tshirt_size", "").strip().upper()
            tshirt = raw_tshirt if raw_tshirt else "UNKNOWN"

            arr_at = _parse_datetime(row.get("arrival_datetime"))
            dep_at = _parse_datetime(row.get("departure_datetime"))

            # Determine operational status:
            # 3 records have departure_datetime < arrival_datetime -> INVALID
            if arr_at and dep_at and dep_at < arr_at:
                status = "INVALID"
            else:
                status = "EXPECTED"

            participant = Participant(
                id=pid,
                canonical_participant_id=pid,
                source_row_id=pid,
                contingent_id=cid,
                name=name if name else "UNKNOWN",
                college=college,
                phone=phone,
                gender=gender,
                diet=diet,
                housing_preference="UNKNOWN",
                accessibility_needs=access_dict,
                accommodation_requested=accom_req,
                tshirt_size=tshirt,
                arrival_at=arr_at,
                departure_at=dep_at,
                age=age,
                role="PARTICIPANT",
                status=status,
                version=1,
                created_at=now(),
                updated_at=now(),
            )
            session.add(participant)
            participant_count += 1

            # Save RawRecord
            raw_rec = RawRecord(
                batch_id="initial_raw_import",
                source_row_id=pid,
                source_sheet="participants.csv",
                raw_payload=row,
                created_at=now(),
            )
            session.add(raw_rec)

            # Record UNKNOWNs in FieldVerification
            if gender == "UNKNOWN":
                session.add(FieldVerification(
                    entity_type="participant",
                    entity_id=pid,
                    field="gender",
                    status="UNKNOWN",
                    owner="ACCOMMODATION_LEAD",
                    created_at=now(),
                ))
            if diet == "UNKNOWN":
                session.add(FieldVerification(
                    entity_type="participant",
                    entity_id=pid,
                    field="diet",
                    status="UNKNOWN",
                    owner="FOOD_OPS_MANAGER",
                    created_at=now(),
                ))
            if accom_req == "UNKNOWN":
                session.add(FieldVerification(
                    entity_type="participant",
                    entity_id=pid,
                    field="accommodation_requested",
                    status="UNKNOWN",
                    owner="ACCOMMODATION_LEAD",
                    created_at=now(),
                ))
            if tshirt == "UNKNOWN":
                session.add(FieldVerification(
                    entity_type="participant",
                    entity_id=pid,
                    field="tshirt_size",
                    status="UNKNOWN",
                    owner="MERCHANDISE_MANAGER",
                    created_at=now(),
                ))

            participants_for_dedupe.append(row)

    session.flush()
    logger.info(f"Seeded {participant_count} participants and raw records.")

    # 4. Seed Registrations
    reg_path = _find_data_file("registrations.csv")
    registrations_for_dedupe: List[Dict[str, Any]] = []
    if reg_path:
        reg_count = 0
        with open(reg_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["participant_id"].strip()
                eid = row["event_id"].strip()
                tid = row.get("team_id", "").strip() or None

                reg = Registration(
                    participant_id=pid,
                    event_id=eid,
                    team_id=tid,
                    status="REGISTERED",
                    registered_at=now(),
                    created_at=now(),
                    updated_at=now(),
                )
                session.add(reg)
                reg_count += 1
                registrations_for_dedupe.append(row)

        session.flush()
        logger.info(f"Seeded {reg_count} event registrations.")

    # 5. Run Pure Deduplication Engine & Persist DuplicateCandidate rows
    if participants_for_dedupe:
        logger.info("Running pure deduplication engine to find candidates...")
        candidates = find_duplicate_candidates(participants_for_dedupe, registrations_for_dedupe)
        dup_count = 0
        for c in candidates:
            cand = DuplicateCandidate(
                participant_a_id=c["participant_a_id"],
                participant_b_id=c["participant_b_id"],
                score=c["score"],
                classification=c["classification"],
                reasons=c["reasons"],
                status="PENDING",
                created_at=now(),
            )
            session.add(cand)
            dup_count += 1

        session.flush()
        logger.info(f"Persisted {dup_count} duplicate candidates.")
