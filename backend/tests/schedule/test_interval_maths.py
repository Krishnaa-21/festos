# OWNER: P1
from datetime import datetime, timedelta, timezone

from app.engines.scheduling import (
    fits_in_venue_windows,
    interval_overlaps,
    parse_availability_windows,
    person_is_free,
    person_is_present,
)


def test_parse_availability_windows():
    s = "2026-10-30 08:00-22:00;2026-10-31 08:00-20:00"
    windows = parse_availability_windows(s)
    assert len(windows) == 2
    assert windows[0][0] == datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    assert windows[0][1] == datetime(2026, 10, 30, 22, 0, tzinfo=timezone.utc)
    assert windows[1][0] == datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)
    assert windows[1][1] == datetime(2026, 10, 31, 20, 0, tzinfo=timezone.utc)


def test_interval_overlaps():
    t0 = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc)
    t3 = datetime(2026, 10, 31, 11, 30, tzinfo=timezone.utc)
    t4 = datetime(2026, 10, 31, 11, 10, tzinfo=timezone.utc)

    # Overlapping: [10:00, 11:00] and [10:30, 11:30]
    assert interval_overlaps(t0, t1, t2, t3) is True

    # Non-overlapping: [10:00, 11:00] and [11:10, 11:30] without buffer
    assert interval_overlaps(t0, t1, t4, t3) is False

    # Overlapping when 15m buffer is added to [10:00, 11:00] (reaches 11:15)
    assert interval_overlaps(t0, t1, t4, t3, buffer_after=timedelta(minutes=15)) is True


def test_fits_in_venue_windows():
    windows = [
        (datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc), datetime(2026, 10, 31, 22, 0, tzinfo=timezone.utc))
    ]
    setup = timedelta(minutes=15)
    teardown = timedelta(minutes=15)

    # Starts at 08:15 (eff_start 08:00), ends at 21:45 (eff_end 22:00) -> Fits
    s1 = datetime(2026, 10, 31, 8, 15, tzinfo=timezone.utc)
    e1 = datetime(2026, 10, 31, 21, 45, tzinfo=timezone.utc)
    assert fits_in_venue_windows(s1, e1, windows, setup, teardown) is True

    # Starts at 08:00 (eff_start 07:45 < 08:00) -> Does not fit
    s2 = datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)
    assert fits_in_venue_windows(s2, e1, windows, setup, teardown) is False


def test_person_presence_and_free():
    arr = datetime(2026, 10, 31, 7, 0, tzinfo=timezone.utc)
    dep = datetime(2026, 10, 31, 20, 0, tzinfo=timezone.utc)
    s = datetime(2026, 10, 31, 9, 0, tzinfo=timezone.utc)
    e = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)

    # Arrived at 07:00, event at 09:00 (> 60m checkin buffer), departs at 20:00 -> Present
    assert person_is_present(arr, dep, s, e, checkin_buffer_min=60) is True

    # Arrived at 08:30 (< 60m buffer before 09:00) -> Not present
    arr_late = datetime(2026, 10, 31, 8, 30, tzinfo=timezone.utc)
    assert person_is_present(arr_late, dep, s, e, checkin_buffer_min=60) is False

    # Check person free
    p_busy = [
        (datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc), datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc), "V01")
    ]
    # At same venue V01 right after (11:00 to 12:00) -> Free
    assert person_is_free(p_busy, datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc), datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc), "V01", travel_min=15) is True

    # At different venue V02 right after (11:00 to 12:00, needs 15m travel) -> Not free
    assert person_is_free(p_busy, datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc), datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc), "V02", travel_min=15) is False
