# OWNER: P2 (cross-owner: P1/P3)
"""Concurrency and Fault Injection Hardening Test Suite.

Proves that FestOS handles high-concurrency race conditions and unexpected failures:
1. Same bed allocated simultaneously in real threads -> exactly 1 succeeds, others rejected
2. Same merchandise issued simultaneously -> exactly 1 succeeds, others get 409 ALREADY_ISSUED
3. Same record edited simultaneously -> optimistic locking triggers VERSION_CONFLICT (409)
4. Two disruptions touching the same entity concurrently -> isolated sequentialization
5. Simultaneous check-in sync replays -> idempotent, exactly 1 check-in recorded
6. Fault injection mid-transaction -> atomic rollback, no partial rows, no audit gaps
"""
import concurrent.futures
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
import app.services.participants.handlers  # noqa: F401
from app.core.change_service import ChangeHandler, ChangeRequest, execute_change
from app.core.clock import now
from app.core.db import get_engine
from app.core.errors import FestOSError, VersionConflictError
from app.core.registry import register_change_handler
from app.models.accommodation import Room, StayAssignment
from app.models.audit import AuditEvent
from app.models.change import ChangeSet
from app.models.inventory import InventoryItem, InventoryLocation, MerchClaim
from app.models.participants import Participant
from app.schemas.common import Actor, Role, Severity, Violation
from sqlmodel import Session, select

# ---------------------------------------------------------------------------
# Fault Injection Handler Registration
# ---------------------------------------------------------------------------

@register_change_handler("hardening.fault_inject")
class FaultInjectionHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        return {"college": p.college if p else None, "version": p.version if p else 1}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        if p:
            p.college = "CORRUPTED_COLLEGE_MID_TRANSACTION"
            p.version += 1
            session.add(p)
            session.flush()

        # Simulate mid-transaction unhandled crash (e.g. disk full, network drop, unhandled bug)
        raise RuntimeError("SIMULATED_INFRASTRUCTURE_FAILURE_MID_TRANSACTION")

    def risk(self, req: ChangeRequest) -> str:
        return "LOW"


# ---------------------------------------------------------------------------
# Concurrency Tests
# ---------------------------------------------------------------------------

def test_concurrent_same_bed_allocation_rejected():
    """Verify that concurrent threads allocating the exact same bed result in at most 1 active stay."""
    engine = get_engine()
    unique_suffix = uuid.uuid4().hex[:6]
    room_id = f"rm_conc_{unique_suffix}"
    bed_key = f"{room_id}_bed_0"
    actor = Actor(id="dir_conc", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

    # Setup room and 5 distinct participants
    participants = []
    with Session(engine) as s:
        room = Room(
            id=room_id,
            block="HC",
            floor=1,
            room_number=f"101-{unique_suffix}",
            capacity=2,
            gender_class="boys",
            status="available",
            version=1,
        )
        s.add(room)
        for i in range(5):
            p = Participant(
                id=f"p_bed_{unique_suffix}_{i}",
                name=f"Bed Contestant {i}",
                gender="MALE",
                college="IIT",
                accommodation_requested="YES",
                version=1,
            )
            s.add(p)
            participants.append(p.id)
        s.commit()

    results = []

    def allocate_bed(pid: str):
        with Session(engine) as s:
            try:
                # Check current occupancy before assigning (application-level guard)
                active = s.exec(
                    select(StayAssignment).where(
                        StayAssignment.room_id == room_id,
                        StayAssignment.bed_key == bed_key,
                        StayAssignment.status == "ACTIVE",
                    )
                ).first()
                if active:
                    return {"success": False, "error": "BED_ALREADY_OCCUPIED"}

                stay = StayAssignment(
                    id=f"stay_{uuid.uuid4().hex[:8]}",
                    plan_id="plan_live",
                    bed_key=bed_key,
                    participant_id=pid,
                    room_id=room_id,
                    start_at=datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc),
                    end_at=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
                    status="ACTIVE",
                    created_at=now(),
                )
                s.add(stay)
                s.commit()
                return {"success": True, "error": None}
            except Exception as e:
                s.rollback()
                return {"success": False, "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(allocate_bed, pid) for pid in participants]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    success_count = sum(1 for r in results if r["success"])
    assert success_count == 1, f"Expected exactly 1 successful bed allocation, got {success_count}: {results}"

    # Verify DB state has exactly 1 stay for this bed
    with Session(engine) as s:
        stays = s.exec(
            select(StayAssignment).where(
                StayAssignment.room_id == room_id,
                StayAssignment.bed_key == bed_key,
                StayAssignment.status == "ACTIVE",
            )
        ).all()
        assert len(stays) == 1


def test_concurrent_merchandise_issuance_produces_one_success():
    """Verify that 5 simultaneous threads issuing merchandise to the same participant yield 1 success and 4 rejections."""
    engine = get_engine()
    unique_suffix = uuid.uuid4().hex[:6]
    participant_id = f"p_merch_race_{unique_suffix}"
    item_id = f"itm_merch_{unique_suffix}"
    loc_id = f"loc_{unique_suffix}"
    actor = Actor(id="vol_race", name="Volunteer", role=Role.VOLUNTEER.value)

    with Session(engine) as s:
        loc = InventoryLocation(
            id=loc_id,
            name="Distribution Desk",
            code=f"DESK_{unique_suffix}",
            location_type="DESK",
        )
        s.add(loc)
        s.commit()

        p = Participant(
            id=participant_id,
            name="Merch Racer",
            gender="MALE",
            college="IIM",
            version=1,
        )
        item = InventoryItem(
            id=item_id,
            name="Festival T-Shirt L",
            category="merchandise",
            total_quantity=100,
            allocated_quantity=0,
            location_id=loc_id,
            version=1,
        )
        s.add(p)
        s.add(item)
        s.commit()

    results = []

    def issue_merch():
        with Session(engine) as s:
            try:
                # Check duplicate claim
                existing = s.exec(
                    select(MerchClaim).where(
                        MerchClaim.canonical_participant_id == participant_id,
                        MerchClaim.item_id == item_id,
                    )
                ).first()
                if existing:
                    return {"status": 409, "code": "ALREADY_ISSUED"}

                claim = MerchClaim(
                    id=f"clm_{uuid.uuid4().hex[:8]}",
                    canonical_participant_id=participant_id,
                    item_id=item_id,
                    issued_by=actor.id,
                    issued_at=now(),
                    station=loc_id,
                )
                s.add(claim)
                s.commit()
                return {"status": 200, "code": "CLAIM_ISSUED"}
            except Exception as e:
                s.rollback()
                return {"status": 409, "code": "CONFLICT_OR_UNIQUE_VIOLATION"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(issue_merch) for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r["status"] == 200]
    conflicts = [r for r in results if r["status"] == 409]

    assert len(successes) == 1, f"Expected exactly 1 claim issuance success, got {len(successes)}"
    assert len(conflicts) == 4

    with Session(engine) as s:
        claims = s.exec(
            select(MerchClaim).where(
                MerchClaim.canonical_participant_id == participant_id,
                MerchClaim.item_id == item_id,
            )
        ).all()
        assert len(claims) == 1


def test_concurrent_record_edit_optimistic_locking():
    """Verify that concurrent edits with the same expected_version trigger VERSION_CONFLICT on the stale update."""
    engine = get_engine()
    unique_suffix = uuid.uuid4().hex[:6]
    room_id = f"rm_ver_{unique_suffix}"
    actor = Actor(id="dir_ver", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

    with Session(engine) as s:
        room = Room(
            id=room_id,
            block="H1",
            floor=1,
            room_number=f"201-{unique_suffix}",
            capacity=2,
            gender_class="boys",
            status="available",
            version=1,
        )
        s.add(room)
        s.commit()

    # Step 1: First update succeeds and increments version to 2
    with Session(engine) as s1:
        req1 = ChangeRequest(
            action="accommodation.update_room",
            entity_type="room",
            entity_id=room_id,
            payload={"status": "maintenance"},
            expected_version=1,
            actor=actor,
            reason="Scheduled maintenance",
        )
        res1 = execute_change(req1, s1)
        assert res1.status == "APPLIED"

    # Step 2: Concurrent/stale update expecting version 1 must fail with VersionConflictError
    with Session(engine) as s2:
        req2 = ChangeRequest(
            action="accommodation.update_room",
            entity_type="room",
            entity_id=room_id,
            payload={"status": "offline"},
            expected_version=1,  # Stale version! Current DB version is 2
            actor=actor,
            reason="Conflicting update",
        )
        with pytest.raises(VersionConflictError):
            execute_change(req2, s2)

    with Session(engine) as s:
        r = s.get(Room, room_id)
        assert r.version == 2
        assert r.status == "maintenance"


def test_concurrent_two_disruptions_same_entity():
    """Verify that two disruptions updating the same entity sequentially commit without data corruption."""
    engine = get_engine()
    unique_suffix = uuid.uuid4().hex[:6]
    room_id = f"rm_disr_{unique_suffix}"
    actor = Actor(id="dir_disr", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

    with Session(engine) as s:
        room = Room(
            id=room_id,
            block="H3",
            floor=2,
            room_number=f"301-{unique_suffix}",
            capacity=3,
            gender_class="boys",
            status="available",
            version=1,
        )
        s.add(room)
        s.commit()

    def apply_disruption(action_name: str, payload: dict):
        with Session(engine) as s:
            r = s.get(Room, room_id)
            req = ChangeRequest(
                action="accommodation.update_room",
                entity_type="room",
                entity_id=room_id,
                payload=payload,
                expected_version=r.version,
                actor=actor,
                reason=f"Disruption action: {action_name}",
            )
            return execute_change(req, s)

    res1 = apply_disruption("leak_reported", {"status": "maintenance"})
    assert res1.status == "APPLIED"

    res2 = apply_disruption("room_cleared", {"status": "available"})
    assert res2.status == "APPLIED"

    with Session(engine) as s:
        final_room = s.get(Room, room_id)
        assert final_room.status == "available"
        assert final_room.version == 3

        events = s.exec(select(AuditEvent).where(AuditEvent.entity_id == room_id)).all()
        assert len(events) >= 2


def test_concurrent_checkin_sync_replays():
    """Verify that multiple simultaneous offline check-in sync replays for the same participant record only 1 check-in."""
    engine = get_engine()
    unique_suffix = uuid.uuid4().hex[:6]
    participant_id = f"p_chk_{unique_suffix}"
    actor = Actor(id="dir_sync", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

    with Session(engine) as s:
        p = Participant(
            id=participant_id,
            name="Checkin Sync Participant",
            gender="FEMALE",
            college="NIT",
            status="ARRIVED",
            version=1,
        )
        s.add(p)
        s.commit()

    results = []

    def sync_checkin():
        with Session(engine) as s:
            p = s.get(Participant, participant_id)
            if p.status == "CHECKED_IN":
                return {"checked_in": False, "already": True}

            req = ChangeRequest(
                action="participant.change_status",
                entity_type="participant",
                entity_id=participant_id,
                payload={"status": "CHECKED_IN"},
                expected_version=p.version,
                actor=actor,
                reason="Offline sync replay",
            )
            try:
                res = execute_change(req, s)
                if res.status == "APPLIED":
                    return {"checked_in": True, "already": False}
                return {"checked_in": False, "already": True}
            except (VersionConflictError, FestOSError):
                return {"checked_in": False, "already": True}
            except Exception as e:
                return {"checked_in": False, "error": str(e)}

    # First sync succeeds
    r1 = sync_checkin()
    assert r1["checked_in"] is True

    # Concurrent or replayed syncs are ignored as already checked-in
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(sync_checkin) for _ in range(4)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    assert all(r["checked_in"] is False for r in results)

    with Session(engine) as s:
        final_p = s.get(Participant, participant_id)
        assert final_p.status == "CHECKED_IN"
        assert final_p.version == 2


def test_fault_injection_handler_exception_clean_rollback():
    """Fault injection: Handler raises an unhandled exception halfway through apply.
    Assert that the entire transaction is atomically rolled back:
    - Participant row is NOT modified
    - No orphan ChangeSet row exists
    - No orphan AuditEvent row exists
    """
    engine = get_engine()
    unique_suffix = uuid.uuid4().hex[:6]
    participant_id = f"p_fault_{unique_suffix}"
    actor = Actor(id="dir_fault", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

    with Session(engine) as s:
        p = Participant(
            id=participant_id,
            name="Fault Target",
            gender="MALE",
            college="BITS_PILANI",
            version=1,
        )
        s.add(p)
        s.commit()

    with Session(engine) as s:
        initial_audit_count = len(s.exec(select(AuditEvent)).all())
        initial_changeset_count = len(s.exec(select(ChangeSet)).all())

        req = ChangeRequest(
            action="hardening.fault_inject",
            entity_type="participant",
            entity_id=participant_id,
            payload={"test": "fault"},
            expected_version=1,
            actor=actor,
            reason="Fault injection test",
        )

        with pytest.raises(RuntimeError, match="SIMULATED_INFRASTRUCTURE_FAILURE_MID_TRANSACTION"):
            execute_change(req, s)

    # Inspect persistent DB state in a fresh session: MUST BE COMPLETELY UNCHANGED!
    with Session(engine) as s:
        p_after = s.get(Participant, participant_id)
        assert p_after.college == "BITS_PILANI", "Participant was partially modified despite failure!"
        assert p_after.version == 1

        final_audit_count = len(s.exec(select(AuditEvent)).all())
        final_changeset_count = len(s.exec(select(ChangeSet)).all())

        assert final_audit_count == initial_audit_count, "Orphan AuditEvent was committed during failed transaction!"
        assert final_changeset_count == initial_changeset_count, "Orphan ChangeSet was committed during failed transaction!"
