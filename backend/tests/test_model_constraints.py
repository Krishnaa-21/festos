# OWNER: P1
from datetime import datetime, timezone

import pytest
from app.models.accommodation import StayAssignment
from app.models.inventory import InventoryItem, MerchClaim
from app.models.participants import Participant
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session


def test_duplicate_merch_claim_rejected(session: Session):
    """Guarantees unique(canonical_participant_id, item_id) on merch_claim."""
    # Create inventory item
    item = InventoryItem(name="Official Fest T-Shirt", code="TSHIRT_M", kind="merch", size="M")
    session.add(item)
    session.commit()

    # First claim succeeds
    claim1 = MerchClaim(
        canonical_participant_id="CAN_PAR_001",
        item_id=item.id,
        size="M",
        issued_by="STAFF_01"
    )
    session.add(claim1)
    session.commit()

    # Second claim with identical canonical participant and item must fail
    claim2 = MerchClaim(
        canonical_participant_id="CAN_PAR_001",
        item_id=item.id,
        size="M",
        issued_by="STAFF_02"
    )
    session.add(claim2)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()

def test_overlapping_stay_bed_assignment_rejected(session: Session):
    """Guarantees unique(plan_id, bed_key, start_at) on stay_assignment."""
    participant = Participant(name="Aarav Sharma")
    session.add(participant)
    session.commit()

    start_time = datetime(2026, 10, 30, 14, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)

    # First stay assignment succeeds
    stay1 = StayAssignment(
        plan_id="PLAN_A",
        bed_key="BLOCK_B_RM_201_BED_1",
        participant_id=participant.id,
        start_at=start_time,
        end_at=end_time
    )
    session.add(stay1)
    session.commit()

    # Conflicting assignment for the same plan, bed_key, and start_at fails
    stay2 = StayAssignment(
        plan_id="PLAN_A",
        bed_key="BLOCK_B_RM_201_BED_1",
        participant_id=participant.id,
        start_at=start_time,
        end_at=end_time
    )
    session.add(stay2)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
