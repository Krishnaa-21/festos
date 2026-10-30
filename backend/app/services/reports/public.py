# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, func, select

from app.models.audit import AuditEvent
from app.schemas.common import EntityRef, RiskItem
from app.services.reports.registry import get_all_reports


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return module KPI summary as of `now`."""
    total_reports = len(get_all_reports())
    exports_count = session.exec(
        select(func.count(AuditEvent.id)).where(AuditEvent.action == "report.exported")
    ).one() or 0

    bundle_exports = session.exec(
        select(func.count(AuditEvent.id)).where(AuditEvent.action == "report.bundle_exported")
    ).one() or 0

    return {
        "module": "reports",
        "status": "OPERATIONAL",
        "registered_reports_count": total_reports,
        "total_reports_exported": exports_count,
        "bundle_exports_count": bundle_exports,
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return active risks evaluated as of `now`."""
    return []


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
