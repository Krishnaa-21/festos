# OWNER: P1
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings

_demo_time: Optional[datetime] = None

def set_demo_time(dt: Optional[datetime]) -> None:
    """Set or clear a simulated fest time for demo or testing purposes."""
    global _demo_time
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    _demo_time = dt

def get_demo_time() -> Optional[datetime]:
    return _demo_time

def now() -> datetime:
    """Single source of truth for the current time.
    Returns UTC timezone-aware datetime.
    Supports demo time override and FESTOS_NOW env variable.
    """
    if _demo_time is not None:
        return _demo_time

    if settings.FESTOS_NOW:
        try:
            dt = datetime.fromisoformat(settings.FESTOS_NOW)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    return datetime.now(timezone.utc)

def to_fest_tz(dt: datetime) -> datetime:
    """Convert UTC datetime to fest local timezone (e.g. Asia/Kolkata)."""
    tz = ZoneInfo(settings.FESTOS_TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)
