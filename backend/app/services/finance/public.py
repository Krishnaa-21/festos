# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.clock import now as clock_now
from app.models.vendors import VendorSettlement
from app.schemas.common import EntityRef, RiskItem
from app.services.finance.service import get_finance_summary


def summary(session: Session, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return financial KPI summary as of `now`."""
    if now is None:
        now = clock_now()
    fin_sum = get_finance_summary(session)
    return {
        "module": "finance",
        "status": "OPERATIONAL",
        "budget_status": fin_sum.budget_status,
        "committed_spend_inr": fin_sum.total_spend_committed_inr,
        "projected_spend_inr": fin_sum.total_spend_projected_inr,
        "external_accommodation_inr": fin_sum.breakdown.get("external_accommodation_inr", 0.0),
        "vendor_catering_inr": fin_sum.breakdown.get("vendors_and_catering_inr", 0.0),
    }


def risks(session: Session, now: Optional[datetime] = None) -> List[RiskItem]:
    """Return financial commercial risks as of `now`."""
    if now is None:
        now = clock_now()
    risk_list: List[RiskItem] = []
    settlements = session.exec(select(VendorSettlement)).all()

    for s in settlements:
        if s.status == "DISPUTED":
            risk_list.append(
                RiskItem(
                    id=f"rsk_fin_dsp_{s.id}",
                    module="finance",
                    kind="COMMERCIAL_BILLING_DISPUTE",
                    title=f"Disputed Invoice: Vendor {s.vendor_id} (₹{s.disputed_amount_inr:,.2f})",
                    severity=3,
                    hours_to_impact=12.0,
                    people_affected=1,
                    uncertainty=0.1,
                    resource_criticality=3,
                    entity_refs=[EntityRef(type="vendor_settlement", id=s.id, label=s.id)],
                    action={"label": "Review Dispute", "route": "/finance", "api": "/api/v1/finance/vendor-settlements"},
                    explanation=f"Dispute of ₹{s.disputed_amount_inr:,.2f} pending resolution: {s.dispute_reason}",
                )
            )

    return risk_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Return downstream entities affected by financial entity."""
    deps: List[EntityRef] = []
    if entity_type == "vendor_settlement":
        s = session.get(VendorSettlement, entity_id)
        if s:
            deps.append(EntityRef(type="vendor", id=s.vendor_id, label=f"Vendor {s.vendor_id}"))
    return deps
