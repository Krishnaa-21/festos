export interface FinanceSummary {
  external_budget_inr: number | null;
  budget_status: "BUDGET_UNSET" | "SET" | "OVER_BUDGET";
  budget_explanation: string;
  total_spend_committed_inr: number;
  total_spend_projected_inr: number;
  breakdown: {
    external_accommodation_inr: number;
    vendors_and_catering_inr: number;
    merchandise_inr: number;
    logistics_equipment_inr: number;
    approved_emergency_inr: number;
  };
}

export interface AccommodationSpendProperty {
  property_id: string;
  name: string;
  capacity_beds: number;
  booked_beds: number;
  nights: number;
  rate_per_bed_night_inr: number;
  total_spend_inr: number;
  contract_status: string;
  payment_status: string;
}

export interface VendorSettlement {
  vendor_id: string;
  vendor_name: string;
  contract_total_inr: number;
  advance_paid_inr: number;
  balance_due_inr: number;
  due_date: string;
  status: "PENDING_VERIFICATION" | "SETTLED" | "DISPUTED";
  dispute: {
    id: string;
    amount_inr: number;
    reason: string;
    opened_by: string;
    opened_at: string;
  } | null;
}

export interface MerchandiseCostItem {
  item_name: string;
  unit_cost_inr: number;
  ordered_qty: number;
  total_cost_inr: number;
  supplier: string;
  status: string;
}

export interface EmergencySpendItem {
  id: string;
  description: string;
  amount_inr: number;
  approved_by: string;
  approved_at: string;
  reason: string;
  audit_link: string;
}

export interface BudgetOverrideItem {
  id: string;
  category: string;
  target_entity: string;
  original_value: string;
  overridden_value: string;
  delta_inr: number;
  reason: string;
  authorized_by: string;
  authorized_at: string;
  audit_event_id: string;
}
