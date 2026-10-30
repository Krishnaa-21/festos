export interface DietaryMatrixCell {
  category: "VEG" | "NON_VEG" | "JAIN" | "VEGAN" | "GLUTEN_FREE";
  meal_slot: "BREAKFAST" | "LUNCH" | "SNACKS" | "DINNER" | "LATE_NIGHT";
  venue_id: string;
  capacity: number;
  demand: number;
  deficit: number;
  is_zero_coverage: boolean;
  vendor_names: string[];
}

export interface DietaryCoverageResponse {
  categories: string[];
  meal_slots: string[];
  venues: { id: string; name: string }[];
  matrix: DietaryMatrixCell[];
  summary: {
    zero_coverage_count: number;
    critical_alerts: {
      category: string;
      meal_slot: string;
      venue_name: string;
      affected: number;
    }[];
  };
}

export interface VendorItem {
  id: string;
  name: string;
  status: "ACTIVE" | "SHUTDOWN" | "SUSPENDED";
  dietary_options: string;
  menu_description: string;
  capacity: number;
  hours: string;
  hygiene_certificate_expiry: string;
  days_to_expiry: number;
  payment_terms: string;
  base_rate_per_meal_inr: number;
  contact_phone: string;
}

export interface VendorComplianceData {
  certifications: {
    vendor_id: string;
    vendor_name: string;
    certificate_type: string;
    certificate_number: string;
    valid_until: string;
    days_left: number;
    status: "VALID" | "WARNING_EXPIRING" | "CRITICAL_EXPIRING";
    audit_pass: boolean;
  }[];
  mismatches: {
    id: string;
    vendor_id: string;
    vendor_name: string;
    item_name: string;
    issue: string;
    severity: string;
  }[];
}

export interface ReplacementVendor {
  vendor_id: string;
  vendor_name: string;
  available_capacity: number;
  dietary_match: string;
  proximity_score: number;
  rate_per_meal_inr: number;
  cost_delta_inr: number;
  rank: number;
  rationale: string;
}

export interface NotificationDraft {
  id: string;
  recipient_group: string;
  channel: string;
  subject: string;
  body: string;
  requires_approval: boolean;
}

export interface ShutdownImpactResponse {
  vendor_id: string;
  vendor_name: string;
  lost_capacity: number;
  affected_slots: {
    date: string;
    meal_slot: string;
    venue_name: string;
    meals_deficit: number;
  }[];
  ranked_replacements: ReplacementVendor[];
  cost_delta_inr: number;
  notification_drafts: NotificationDraft[];
}
