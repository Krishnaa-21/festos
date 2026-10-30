export type RoleVariant =
  | "DIRECTOR"
  | "ACCOMMODATION_LEAD"
  | "EVENT_LEAD"
  | "LOGISTICS_MANAGER"
  | "FOOD_OPS_MANAGER"
  | "FINANCE_MANAGER"
  | "VOLUNTEER";

export interface SpecKpiMetric {
  id: string;
  label: string;
  value: string | number;
  subValue?: string;
  category: "participants" | "accommodation" | "events" | "logistics" | "merchandise" | "food" | "staff" | "governance";
  status: "GOOD" | "WARNING" | "CRITICAL" | "NEUTRAL";
  moduleRoute: string;
  contextExplanation?: string;
}

export interface AttentionItem {
  id: string;
  module: string;
  kind: string;
  title: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  severityLevel: number; // 4 (Critical), 3 (High), 2 (Medium), 1 (Low)
  urgencyLevel: number; // 5 (<=1h), 4 (<=4h), 3 (<=12h), 2 (<=24h), 1 (>24h)
  hoursToImpact: number;
  peopleAffected: number;
  uncertainty: number; // 0.0 to 1.0
  resourceCriticality: number; // 1 to 5
  attentionScore: number; // severityLevel * urgencyLevel * max(peopleAffected, 1)
  action: {
    label: string;
    route: string;
    api?: string;
  };
  explanation: string;
  isSnoozed?: boolean;
  snoozedUntil?: string;
  snoozeReason?: string;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
}

export interface HeatmapCell {
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  severityLevel: number;
  timeWindow: "<=1h" | "1-4h" | "4-12h" | "12-24h" | ">24h";
  timeWindowIndex: number; // 0 to 4
  itemCount: number;
  totalPeopleAffected: number;
  avgUncertainty: number;
  items: AttentionItem[];
}

export interface DashboardMetricsResponse {
  total_participants: number;
  narrative_participants: number;
  raw_participants: number;
  arrived: number;
  checked_in: number;
  pending_arrivals: number;
  occupancy_pct: number;
  available_beds: number;
  unplaced_participants: number;
  active_sessions: number;
  open_conflicts: number;
  equipment_availability: number;
  equipment_in_transit: number;
  equipment_under_repair: number;
  merchandise_stock: number;
  merch_issued: number;
  vendor_status: "OPERATIONAL" | "DEGRADED" | "CRITICAL";
  food_coverage_gaps: number;
  uncovered_meals: number;
  staff_availability: number;
  core_team_active: number;
  peak_staffing_gap: number;
  open_incidents: number;
  pending_approvals: number;
  active_overrides: number;
  calculated_at: string;
}
