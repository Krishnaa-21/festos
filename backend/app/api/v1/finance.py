# OWNER: P2
from __future__ import annotations

from typing import Any, Dict

from app.core.db import get_session
from app.core.deps import require_permission
from app.schemas.common import Actor, Envelope
from app.schemas.finance import (
    AccommodationSpendResponseData,
    EmergencySpendRequest,
    FinanceSummaryData,
    OpenDisputeRequest,
    RecordPaymentRequest,
    SetBudgetRequest,
)
from app.services.finance.service import (
    get_accommodation_spend,
    get_emergency_spending_log,
    get_finance_summary,
    get_financial_overrides_report,
    get_merchandise_costs_overview,
    get_vendor_settlements,
    open_settlement_dispute,
    propose_emergency_spend,
    record_settlement_payment,
    set_external_budget,
)
from fastapi import APIRouter, Depends
from sqlmodel import Session

router = APIRouter(prefix="/finance", tags=["Finance & Commercials"])


@router.get("/summary", response_model=Envelope[FinanceSummaryData])
def get_finance_summary_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:read")),
):
    """Return budget gauge metrics, committed spend, projected spend, and budget-unset explanation."""
    res = get_finance_summary(session)
    return Envelope(data=res)


@router.get("/accommodation-spend", response_model=Envelope[AccommodationSpendResponseData])
def get_accommodation_spend_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:read")),
):
    """External accommodation spend broken down by external property from accommodation public contract."""
    res = get_accommodation_spend(session)
    return Envelope(data=res)


@router.get("/vendor-settlements", response_model=Envelope[Dict[str, Any]])
def get_vendor_settlements_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:read")),
):
    """Vendor commercial settlements, balances due, payment milestones, and billing disputes."""
    res = get_vendor_settlements(session)
    return Envelope(data=res)


@router.post("/vendor-settlements/{id}/pay", response_model=Envelope[Dict[str, Any]])
def record_payment_endpoint(
    id: str,
    body: RecordPaymentRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:write")),
):
    """Record an advance or balance payment against a vendor settlement via ChangeService."""
    res = record_settlement_payment(session=session, settlement_id=id, req=body, actor=actor)
    return Envelope(data=res)


@router.post("/vendor-settlements/{id}/dispute", response_model=Envelope[Dict[str, Any]])
def open_dispute_endpoint(
    id: str,
    body: OpenDisputeRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:write")),
):
    """Open a commercial billing dispute on a vendor settlement invoice."""
    res = open_settlement_dispute(session=session, settlement_id=id, req=body, actor=actor)
    return Envelope(data=res)


@router.get("/merchandise-costs", response_model=Envelope[Dict[str, Any]])
def get_merchandise_costs_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:read")),
):
    """Summary of merchandise procurement costs, unit prices, and delivered quantities."""
    res = get_merchandise_costs_overview(session)
    return Envelope(data=res)


@router.get("/emergency-spend", response_model=Envelope[Dict[str, Any]])
def get_emergency_spend_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:read")),
):
    """Log of approved emergency expenditures with justifications and Director authorizations."""
    res = get_emergency_spending_log(session)
    return Envelope(data=res)


@router.post("/emergency-spend", response_model=Envelope[Dict[str, Any]])
def propose_emergency_spend_endpoint(
    body: EmergencySpendRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:write")),
):
    """Propose an emergency expenditure via ChangeService, subject to Director approval."""
    res = propose_emergency_spend(session=session, req=body, actor=actor)
    return Envelope(data=res)


@router.get("/overrides-report", response_model=Envelope[Dict[str, Any]])
@router.get("/budget-overrides-report", response_model=Envelope[Dict[str, Any]])
def get_overrides_report_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:read")),
):
    """Audit report of all financial and constraint overrides across all festival modules."""
    res = get_financial_overrides_report(session)
    return Envelope(data=res)


@router.post("/budget/set", response_model=Envelope[Dict[str, Any]])
def set_budget_endpoint(
    body: SetBudgetRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("finance:write")),
):
    """Set the external budget limit ceiling (Festival Director only)."""
    res = set_external_budget(session=session, req=body, actor=actor)
    return Envelope(data=res)
