# OWNER: P1
"""Tests for Contingents module, operational status, leadership detection, and strength reconciliation."""

from app.models.participants import Contingent, Participant
from app.services.contingents.service import (
    get_contingent_status,
    list_contingents,
)
from sqlmodel import Session


def test_contingent_strength_and_leadership_status(session: Session):
    """Contingent listing and status view accurately reports declared vs actual strength and leader/escort presence."""
    # Seed Contingent with declared strength 5
    c = Contingent(
        id="C05",
        code="C05",
        name="IIT Bombay Contingent",
        college="IIT Bombay",
        leader="Rohan Deshmukh",
        escort="Dr. Raman",
        strength_declared=5,
        status="ACTIVE",
    )
    session.add(c)

    # 3 participants:
    # 1 is the leader Rohan Deshmukh (FOUND)
    # Escort Dr. Raman is NOT in participant roster (MISSING)
    # Total actual = 3 -> gap = 3 - 5 = -2
    p1 = Participant(id="p1", contingent_id="C05", name="Rohan Deshmukh", status="EXPECTED", diet="VEG")
    p2 = Participant(id="p2", contingent_id="C05", name="Priya Sen", status="ARRIVED", diet="NON_VEG")
    p3 = Participant(id="p3", contingent_id="C05", name="Aarav Verma", status="EXPECTED", diet="JAIN")
    session.add_all([p1, p2, p3])
    session.commit()

    # 1. Test listing
    res_list = list_contingents(session)
    items = res_list["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "C05"
    assert item["strength_declared"] == 5
    assert item["strength_actual"] == 3
    assert item["gap"] == -2
    assert item["leader_status"] == "FOUND"
    assert item["escort_status"] == "MISSING"

    # 2. Test operational status view
    status_view = get_contingent_status(session, "C05")
    assert status_view is not None
    assert status_view["strength"]["gap"] == -2
    assert status_view["strength"]["status"] == "DISCREPANCY_UNDER"
    assert status_view["leadership"]["leader"]["status"] == "FOUND"
    assert status_view["leadership"]["leader"]["participant_id"] == "p1"
    assert status_view["leadership"]["escort"]["status"] == "MISSING"
    assert status_view["attendance"]["EXPECTED"] == 2
    assert status_view["attendance"]["ARRIVED"] == 1
    assert status_view["dietary_summary"]["VEG"] == 1
    assert status_view["dietary_summary"]["NON_VEG"] == 1
    assert status_view["dietary_summary"]["JAIN"] == 1

    # Alerts generated
    assert any("Declared strength 5 differs from actual rosters 3" in a["message"] for a in status_view["alerts"])
    assert any("Escort Dr. Raman not found" in a["message"] for a in status_view["alerts"])

    # Graceful degradation for housing when accommodation.public not present
    assert status_view["housing_fragmentation"]["status"] == "UNAVAILABLE"
    assert "Accommodation plan not yet live" in status_view["housing_fragmentation"]["warning"]
