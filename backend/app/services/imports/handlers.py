# OWNER: P2
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now

from app.core.registry import register_change_handler
from app.models.accommodation import ExternalProperty, Room
from app.models.events import Event
from app.models.inventory import InventoryItem
from app.models.ops import ImportBatchMetadata, StagedRecord, Venue
from app.models.participants import (
    Contingent,
    ImportBatch,
    Participant,
    QuarantineRow,
    Registration,
)
from app.models.staff import Staff
from app.models.vendors import Vendor
from app.schemas.common import Severity, Violation

logger = logging.getLogger("festos.imports.handlers")


@register_change_handler("imports.promote")
class ImportPromoteHandler:
    """ChangeService handler for promoting staged import records into canonical tables."""

    def validate(self, req: Any, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        payload = req.payload or {}
        batch_id = payload.get("batch_id") or req.entity_id

        if not batch_id:
            violations.append(
                Violation(
                    code="MISSING_BATCH_ID",
                    severity=Severity.CRITICAL,
                    hard=True,
                    message="Import batch ID is required for promotion",
                )
            )
            return violations

        # Verify batch exists
        batch = session.exec(select(ImportBatch).where(ImportBatch.id == batch_id)).first()
        if not batch:
            violations.append(
                Violation(
                    code="BATCH_NOT_FOUND",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Import batch '{batch_id}' was not found",
                )
            )
            return violations

        # Check pending staged records
        pending_count = len(
            session.exec(
                select(StagedRecord)
                .where(StagedRecord.batch_id == batch_id)
                .where(StagedRecord.status == "PENDING")
            ).all()
        )

        if pending_count == 0 and batch.status == "PROMOTED":
            violations.append(
                Violation(
                    code="BATCH_ALREADY_PROMOTED",
                    severity=Severity.MEDIUM,
                    hard=False,
                    message=f"Batch '{batch_id}' has already been promoted to canonical tables",
                )
            )

        return violations

    def snapshot(self, req: Any, session: Session) -> Dict[str, Any]:
        batch_id = req.payload.get("batch_id") or req.entity_id
        batch = session.exec(select(ImportBatch).where(ImportBatch.id == batch_id)).first()
        pending_count = len(
            session.exec(
                select(StagedRecord)
                .where(StagedRecord.batch_id == batch_id)
                .where(StagedRecord.status == "PENDING")
            ).all()
        )
        return {
            "batch_id": batch_id,
            "status": batch.status if batch else "UNKNOWN",
            "pending_staged_records": pending_count,
        }

    def apply(self, req: Any, session: Session) -> Dict[str, Any]:
        batch_id = req.payload.get("batch_id") or req.entity_id
        batch = session.exec(select(ImportBatch).where(ImportBatch.id == batch_id)).first()
        meta = session.exec(select(ImportBatchMetadata).where(ImportBatchMetadata.batch_id == batch_id)).first()

        staged_rows = session.exec(
            select(StagedRecord)
            .where(StagedRecord.batch_id == batch_id)
            .where(StagedRecord.status == "PENDING")
        ).all()

        promoted_count = 0

        for stg in staged_rows:
            target = stg.target_table
            data = stg.payload or {}

            if target == "participant":
                existing = session.exec(select(Participant).where(Participant.id == stg.source_row_id)).first()
                arr = data.get("arrival_at")
                if isinstance(arr, str) and arr:
                    try:
                        arr = datetime.fromisoformat(arr)
                    except Exception:
                        arr = None
                dep = data.get("departure_at")
                if isinstance(dep, str) and dep:
                    try:
                        dep = datetime.fromisoformat(dep)
                    except Exception:
                        dep = None

                if not existing:
                    part = Participant(
                        id=data.get("id", stg.source_row_id),
                        canonical_participant_id=data.get("id", stg.source_row_id),
                        source_row_id=data.get("source_row_id", stg.source_row_id),
                        contingent_id=data.get("contingent_id"),
                        name=data.get("name", "UNKNOWN"),
                        college=data.get("college"),
                        phone=data.get("phone"),
                        gender=data.get("gender", "UNKNOWN"),
                        diet=data.get("diet", "UNKNOWN"),
                        housing_preference=data.get("housing_preference", "UNKNOWN"),
                        accessibility_needs=data.get("accessibility_needs", {}),
                        accommodation_requested=data.get("accommodation_requested", "UNKNOWN"),
                        tshirt_size=data.get("tshirt_size"),
                        arrival_at=arr,
                        departure_at=dep,
                        age=data.get("age"),
                        role="PARTICIPANT",
                        status="EXPECTED",
                    )
                    session.add(part)
                    promoted_count += 1

                else:
                    # Idempotent update
                    for k in ("name", "college", "gender", "diet", "accommodation_requested", "age", "phone"):
                        if k in data and data[k] is not None:
                            setattr(existing, k, data[k])
                    session.add(existing)

            elif target == "contingent":
                cid = data.get("id", stg.source_row_id)
                existing_c = session.exec(select(Contingent).where(Contingent.id == cid)).first()
                if not existing_c:
                    ctg = Contingent(
                        id=cid,
                        code=cid,
                        name=data.get("name") or data.get("college") or cid,
                        college=data.get("college") or data.get("name"),
                        leader=data.get("leader"),
                        escort=data.get("escort"),
                        strength_declared=data.get("strength_declared", 0) or 0,
                        preferences=data.get("preferences"),
                        status="ACTIVE",
                    )
                    session.add(ctg)
                    promoted_count += 1

            elif target == "registration":
                pid = data.get("participant_id")
                eid = data.get("event_id")
                p_exists = session.exec(select(Participant.id).where(Participant.id == pid)).first()
                e_exists = session.exec(select(Event.id).where(Event.id == eid)).first()
                if not p_exists or not e_exists:
                    missing = []
                    if not p_exists:
                        missing.append(f"participant '{pid}'")
                    if not e_exists:
                        missing.append(f"event '{eid}'")
                    qr = QuarantineRow(
                        batch_id=batch_id,
                        reason=f"Registration references unpromoted or unknown entity: {', '.join(missing)}",
                        raw_payload=data,
                        created_at=now(),
                    )
                    session.add(qr)
                    stg.status = "QUARANTINED"
                    session.add(stg)
                    continue

                reg_id = f"reg_{pid}_{eid}"
                existing_r = session.exec(select(Registration).where(Registration.id == reg_id)).first()
                if not existing_r:
                    reg = Registration(
                        id=reg_id,
                        participant_id=pid,
                        event_id=eid,
                        team_id=data.get("team_id") or None,
                        status="REGISTERED",
                        registered_at=now(),
                    )
                    session.add(reg)
                    promoted_count += 1

            elif target == "event":
                eid = data.get("id", stg.source_row_id)
                existing_e = session.exec(select(Event).where(Event.id == eid)).first()
                if not existing_e:
                    ev = Event(
                        id=eid,
                        code=eid,
                        name=data.get("name", eid),
                        solo_team=(data.get("solo_team") or "SOLO").upper(),
                        event_type=data.get("solo_team", "solo").lower(),
                        rounds_text=data.get("rounds_text"),
                        duration_min=data.get("duration_min", 60) or 60,
                        venue_requirements=data.get("venue_requirements"),
                        equipment_needs=data.get("equipment_needs"),
                        volunteers_needed=data.get("volunteers_needed", 0) or 0,
                        status="ACTIVE",
                    )
                    session.add(ev)
                    promoted_count += 1

            elif target == "venue":
                vid = data.get("id", stg.source_row_id)
                existing_v = session.exec(select(Venue).where(Venue.id == vid)).first()
                if not existing_v:
                    ven = Venue(
                        id=vid,
                        code=vid,
                        name=data.get("name", vid),
                        capacity=data.get("capacity", 100) or 100,
                        availability_windows=data.get("availability_windows"),
                        indoor_outdoor=data.get("indoor_outdoor", "indoor"),
                        status="AVAILABLE",
                    )
                    session.add(ven)
                    promoted_count += 1

            elif target == "staff":
                sid = data.get("id", stg.source_row_id)
                existing_s = session.exec(select(Staff).where(Staff.id == sid)).first()
                if not existing_s:
                    stf = Staff(
                        id=sid,
                        name=data.get("name", sid),
                        role=data.get("role", "VOLUNTEER"),
                        shift=data.get("shift"),
                        phone=data.get("phone"),
                        status="ACTIVE",
                    )
                    session.add(stf)
                    promoted_count += 1

            elif target == "room":
                rid = data.get("id", stg.source_row_id)
                existing_rm = session.exec(select(Room).where(Room.id == rid)).first()
                if not existing_rm:
                    rm = Room(
                        id=rid,
                        block=data.get("block", "UNKNOWN"),
                        floor=data.get("floor", 0) or 0,
                        capacity=data.get("capacity", 2) or 2,
                        bed_count=data.get("capacity", 2) or 2,
                        accessible=(data.get("accessibility") == "YES"),
                        accessibility=data.get("accessibility", "no"),
                        gender_class=data.get("gender_class", "UNKNOWN"),
                        status=data.get("status", "AVAILABLE"),
                    )
                    session.add(rm)
                    promoted_count += 1

            elif target == "external_property":
                pid = data.get("id", stg.source_row_id)
                existing_ep = session.exec(select(ExternalProperty).where(ExternalProperty.id == pid)).first()
                if not existing_ep:
                    ep = ExternalProperty(
                        id=pid,
                        name=data.get("name", pid),
                        beds=data.get("beds", 0) or 0,
                        cost_per_bed_night=data.get("cost_per_bed_night", 0.0) or 0.0,
                        distance_km=data.get("distance_km", 0.0) or 0.0,
                        transport_availability=data.get("transport_availability", "yes"),
                        transport_limited=(data.get("transport_availability") == "limited"),
                        status="ACTIVE",
                    )
                    session.add(ep)
                    promoted_count += 1

            elif target == "inventory_item":
                iid = data.get("id", stg.source_row_id)
                existing_it = session.exec(select(InventoryItem).where(InventoryItem.id == iid)).first()
                if not existing_it:
                    it = InventoryItem(
                        id=iid,
                        name=data.get("name", iid),
                        code=iid,
                        kind="merch" if "size" in data else "equipment",
                        size=data.get("size"),
                        condition=data.get("condition", "GOOD"),
                        quantity=data.get("quantity", 1) or 1,
                        reserved_quantity=data.get("reserved_quantity", 0) or 0,
                        available_quantity=data.get("quantity", 1) or 1,
                        location=data.get("location"),
                        status="AVAILABLE",
                    )
                    session.add(it)
                    promoted_count += 1

            elif target == "vendor":
                vnd_id = data.get("id", stg.source_row_id)
                existing_vnd = session.exec(select(Vendor).where(Vendor.id == vnd_id)).first()
                if not existing_vnd:
                    vnd = Vendor(
                        id=vnd_id,
                        name=data.get("name", vnd_id),
                        menu_description=data.get("menu_description"),
                        dietary_options=data.get("dietary_options"),
                        hygiene_certificate_expiry=data.get("hygiene_certificate_expiry"),
                        hours=data.get("hours"),
                        capacity=data.get("capacity"),
                        payment_terms=data.get("payment_terms"),
                        status="ACTIVE",
                    )
                    session.add(vnd)
                    promoted_count += 1

            # Mark staged record as PROMOTED
            stg.status = "PROMOTED"
            session.add(stg)

        if batch:
            batch.status = "PROMOTED"
            session.add(batch)
        if meta:
            meta.status = "PROMOTED"
            session.add(meta)

        session.flush()

        return {
            "batch_id": batch_id,
            "promoted_count": promoted_count,
            "target_table": staged_rows[0].target_table if staged_rows else "unknown",
            "status": "PROMOTED",
        }

    def risk(self, req: Any) -> str:
        return "LOW"

    def revert(self, change_set: Any, session: Session) -> None:
        batch_id = change_set.payload.get("batch_id") or change_set.entity_id
        staged_rows = session.exec(
            select(StagedRecord).where(StagedRecord.batch_id == batch_id)
        ).all()
        for stg in staged_rows:
            stg.status = "PENDING"
            session.add(stg)
        batch = session.exec(select(ImportBatch).where(ImportBatch.id == batch_id)).first()
        if batch:
            batch.status = "STAGED"
            session.add(batch)
        session.flush()
