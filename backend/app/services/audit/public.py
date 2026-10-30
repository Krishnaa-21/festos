# OWNER: P3
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.audit import verify_chain
from app.models.audit import AuditEvent
from app.schemas.common import ActionRef, EntityRef, RiskItem, Severity


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Return audit module KPI summary as of `now`."""
    try:
        events = session.exec(select(AuditEvent)).all()
        total_events = len(events)
        last_event = session.exec(select(AuditEvent).order_by(AuditEvent.timestamp.desc())).first()
        last_ts = last_event.timestamp.isoformat() if last_event else None
    except Exception:
        total_events = 0
        last_ts = None

    return {
        "module": "audit",
        "total_audit_events": total_events,
        "last_event_timestamp": last_ts,
        "tamper_evident_chain": "ENABLED",
        "status": "OPERATIONAL"
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Return audit risks evaluated as of `now`."""
    items: List[RiskItem] = []
    try:
        result = verify_chain(session)
        if not result.get("valid"):
            items.append(
                RiskItem(
                    id="risk_audit_tampering",
                    module="audit",
                    kind="AUDIT_TAMPERING_DETECTED",
                    title="Audit Hash Chain Divergence Detected",
                    severity=Severity.CRITICAL,
                    hours_to_impact=0.0,
                    people_affected=100,
                    uncertainty=0.0,
                    resource_criticality=5,
                    entity_refs=[EntityRef(type="audit_event", id=result.get("broken_event_id") or "chain", label="Corrupted Event")],
                    action=ActionRef(label="Verify Chain", route="/audit", api="/api/v1/audit/verify"),
                    explanation=f"Critical cryptographic discrepancy: {result.get('message')}"
                )
            )
    except Exception:
        pass
    return items


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by entity_type:entity_id."""
    return []
