# OWNER: P1
from datetime import datetime, timezone

from app.engines.conflicts import DefaultEquipmentAdapter, PureConflictDetector


def _base_venues():
    return [
        {
            "id": "V01",
            "name": "Main Stage",
            "capacity": 50,
            "availability_windows": "2026-10-31 08:00-22:00",
            "setup_time_min": 15,
            "teardown_time_min": 15,
        },
        {
            "id": "V02",
            "name": "LT-1",
            "capacity": 100,
            "availability_windows": "2026-10-31 08:00-22:00",
            "setup_time_min": 15,
            "teardown_time_min": 15,
        },
    ]


def test_conflict_participant_clash():
    detector = PureConflictDetector(_base_venues())
    sessions = [
        {
            "id": "s1",
            "event_name": "Debate",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "assigned_participant_ids": ["P001", "P002"],
        },
        {
            "id": "s2",
            "event_name": "Quiz",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 30, tzinfo=timezone.utc),
            "assigned_participant_ids": ["P001", "P003"],
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "PARTICIPANT_CLASH" in types


def test_conflict_team_clash():
    detector = PureConflictDetector(_base_venues())
    sessions = [
        {
            "id": "s1",
            "event_name": "Futsal",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "team_id": "TEAM_C01_E24",
        },
        {
            "id": "s2",
            "event_name": "Street Play",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 10, 15, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 15, tzinfo=timezone.utc),
            "team_id": "TEAM_C01_E24",
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "TEAM_CLASH" in types


def test_conflict_judge_double_booking():
    detector = PureConflictDetector(_base_venues())
    sessions = [
        {
            "id": "s1",
            "event_name": "Solo Dance",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "assigned_judges": ["JDG_01"],
        },
        {
            "id": "s2",
            "event_name": "Battle of Bands",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 30, tzinfo=timezone.utc),
            "assigned_judges": ["JDG_01"],
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "JUDGE_DOUBLE_BOOKING" in types


def test_conflict_volunteer_double_booking():
    detector = PureConflictDetector(_base_venues(), available_volunteers_total=10)
    sessions = [
        {
            "id": "s1",
            "event_name": "Event A",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "volunteers_required": 8,
        },
        {
            "id": "s2",
            "event_name": "Event B",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "volunteers_required": 8,
        },
    ]
    # Total volunteers required = 16 > 10
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "VOLUNTEER_DOUBLE_BOOKING" in types


def test_conflict_venue_double_booking():
    detector = PureConflictDetector(_base_venues())
    sessions = [
        {
            "id": "s1",
            "event_name": "Event A",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
        },
        {
            "id": "s2",
            "event_name": "Event B",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 30, tzinfo=timezone.utc),
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "VENUE_DOUBLE_BOOKING" in types


def test_conflict_capacity_violation():
    detector = PureConflictDetector(_base_venues())  # V01 capacity is 50
    sessions = [
        {
            "id": "s1",
            "event_name": "Mega Event",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "entrants_count": 75,
        }
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "CAPACITY_VIOLATION" in types


def test_conflict_equipment_conflict():
    adapter = DefaultEquipmentAdapter(stock_map={"projector": 1})
    detector = PureConflictDetector(_base_venues(), equipment_port=adapter)
    sessions = [
        {
            "id": "s1",
            "event_name": "Presentation A",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "equipment_required": "projector",
        },
        {
            "id": "s2",
            "event_name": "Presentation B",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "equipment_required": "projector",
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "EQUIPMENT_CONFLICT" in types


def test_conflict_insufficient_travel_time():
    detector = PureConflictDetector(_base_venues())  # default 15m travel between V01 and V02
    sessions = [
        {
            "id": "s1",
            "event_name": "Event A",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "assigned_participant_ids": ["P001"],
        },
        {
            "id": "s2",
            "event_name": "Event B",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 11, 5, tzinfo=timezone.utc),  # only 5m gap < 15m
            "end_at": datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
            "assigned_participant_ids": ["P001"],
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "INSUFFICIENT_TRAVEL_TIME" in types


def test_conflict_setup_teardown_conflict():
    detector = PureConflictDetector(_base_venues())  # 15m setup and teardown
    sessions = [
        {
            "id": "s1",
            "event_name": "Event A",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
        },
        {
            "id": "s2",
            "event_name": "Event B",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 11, 10, tzinfo=timezone.utc),  # only 10m gap < 15m teardown/setup
            "end_at": datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "SETUP_TEARDOWN_CONFLICT" in types


def test_conflict_operating_hour_conflict():
    detector = PureConflictDetector(_base_venues())  # V01 availability is 08:00 - 22:00
    sessions = [
        {
            "id": "s1",
            "event_name": "Late Night Jam",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 22, 30, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc),
        }
    ]
    conflicts = detector.detect_conflicts(sessions)
    types = [c["conflict_type"] for c in conflicts]
    assert "OPERATING_HOUR_CONFLICT" in types


def test_zero_venue_overlaps_is_never_reported_as_zero_conflicts():
    detector = PureConflictDetector(_base_venues())
    # Two sessions in different venues (zero venue overlap!), but same participant double-booked
    sessions = [
        {
            "id": "s1",
            "event_name": "Debate",
            "venue_id": "V01",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "assigned_participant_ids": ["P001"],
        },
        {
            "id": "s2",
            "event_name": "Quiz",
            "venue_id": "V02",
            "start_at": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            "assigned_participant_ids": ["P001"],
        },
    ]
    conflicts = detector.detect_conflicts(sessions)
    venue_overlaps = [c for c in conflicts if c["conflict_type"] == "VENUE_DOUBLE_BOOKING"]
    all_conflicts = [c for c in conflicts]

    # Explicit assertion: Zero venue overlaps != Zero conflicts
    assert len(venue_overlaps) == 0
    assert len(all_conflicts) > 0
    assert any(c["conflict_type"] == "PARTICIPANT_CLASH" for c in all_conflicts)
