# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FinanceSummaryData(BaseModel):
    external_budget_inr: Optional[float] = None
    external_budget_ceiling_inr: Optional[float] = None
    budget_status: str  # BUDGET_UNSET | BUDGET_SET
    budget_explanation: str
    total_spend_committed_inr: float
    total_spend_projected_inr: float
    cost_variance_inr: float
    variance_inr: Optional[float] = None
    budget_utilization_pct: Optional[float] = None
    breakdown: Dict[str, float]


class AccommodationSpendProperty(BaseModel):
    property_id: str
    name: str
    property_name: Optional[str] = None
    capacity_beds: int
    booked_beds: int
    nights: int
    rate_per_bed_night_inr: float
    total_spend_inr: float
    total_cost_inr: Optional[float] = None
    contract_status: str
    payment_status: str


class AccommodationSpendResponseData(BaseModel):
    properties: List[AccommodationSpendProperty]
    total_external_spend_inr: float


class VendorSettlementSchema(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    payment_terms: str
    contract_total_inr: float
    advance_paid_inr: float
    balance_due_inr: float
    due_date: str
    status: str
    dispute: Optional[Dict[str, Any]] = None


class RecordPaymentRequest(BaseModel):
    amount_inr: float
    payment_reference: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class OpenDisputeRequest(BaseModel):
    amount_inr: Optional[float] = None
    disputed_amount_inr: Optional[float] = None
    reason: str


class EmergencySpendSchema(BaseModel):
    id: str
    description: str
    amount_inr: float
    category: str
    reason: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    audit_link: Optional[str] = None
    status: str


class EmergencySpendRequest(BaseModel):
    description: Optional[str] = None
    title: Optional[str] = None
    amount_inr: float
    category: str = "VENDOR_BACKUP"
    reason: Optional[str] = None
    justification: Optional[str] = None


class FinancialOverrideReportItem(BaseModel):
    id: str
    category: str
    target_entity: str
    delta_inr: float
    reason: str
    authorized_by: str
    authorized_at: str
    audit_event_id: str


class SetBudgetRequest(BaseModel):
    budget_inr: float
    reason: str
