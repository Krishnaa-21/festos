export type PlanKind = "A" | "B" | "C" | "LIVE";
export type PlanStatus = "CANDIDATE" | "APPROVED" | "LIVE" | "ARCHIVED";

export interface AccommodationPlan {
  plan_id: string;
  kind: PlanKind;
  status: PlanStatus;
  name: string;
  on_campus_placed: number;
  external_placed: number;
  unplaced_count: number;
  contingent_splits: number;
  total_cost_inr: number;
  safety_flags_count: number;
  accessibility_issues_count: number;
  relaxed_constraints_count: number;
  sacrifices_summary: string;
  parameters_applied?: {
    cleaning_buffer_minutes: number;
    max_distance_km: number;
    allow_split_contingents: boolean;
  };
  created_at: string;
}

export interface PlansResponseData {
  plans: AccommodationPlan[];
  budget_ceiling_inr: number | null;
  is_budget_unset: boolean;
}

export interface ShortageGroup {
  reason_code: "UNKNOWN_GENDER" | "HARD_ACCESSIBILITY" | "EXTERNAL_CAPACITY_EXHAUSTED" | "MINOR_ESCORT_RESTRICTION";
  title: string;
  count: number;
  description: string;
  affected_contingents: string[];
  criticality: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface UnplacedParticipantItem {
  participant_id: string;
  name: string;
  contingent_id: string;
  college: string;
  blocking_reason: string;
  accessibility_needed: boolean;
  housing_preference: string;
  gender: string;
}

export interface ShortagesResponseData {
  total_unplaced: number;
  grouped_by_reason: ShortageGroup[];
  unplaced_items: UnplacedParticipantItem[];
}

export interface WhyNotDiagnostic {
  participant_id: string;
  name: string;
  contingent_id: string;
  blocking_requirement: string;
  missing_information: string;
  rejected_options: Array<{ location: string; reason: string }>;
  counterfactual_impact: string;
  verification_target: {
    field: string;
    entity_id: string;
  };
}

export type BedStatus = "FREE" | "OCCUPIED" | "CLEANING" | "CLOSED" | "ACCESSIBLE" | "UNVERIFIED";

export interface Bed {
  bed_id: string;
  status: BedStatus;
  contingent_id?: string | null;
  contingent_name?: string | null;
  contingent_color?: string | null;
  participant_id?: string | null;
  participant_name?: string | null;
  is_leader?: boolean;
  version: number;
}

export interface Room {
  room_id: string;
  room_number: string;
  accessible: boolean;
  status: "AVAILABLE" | "OCCUPIED" | "CLEANING" | "MAINTENANCE";
  cleaning_status: "READY" | "CLEANING" | "DIRTY";
  cleaning_remaining_minutes?: number;
  beds: Bed[];
}

export interface Floor {
  floor_number: number;
  is_ground: boolean;
  rooms: Room[];
}

export interface HostelBlock {
  block_id: string;
  name: string;
  gender_class: "boys" | "girls" | "mixed";
  total_beds: number;
  occupied_beds: number;
  cleaning_beds: number;
  closed_beds: number;
  free_beds: number;
  floors: Floor[];
}

export interface ExternalProperty {
  property_id: string;
  name: string;
  total_beds: number;
  occupied_beds: number;
  free_beds: number;
  cost_per_bed_night: number;
  distance_km: number;
  accessibility_verified: boolean;
  gender_suitability_verified: boolean;
  transport_limited: boolean;
}

export interface OccupancyData {
  blocks: HostelBlock[];
  external_properties: ExternalProperty[];
}

export interface ConstraintViolation {
  code: string;
  severity: number;
  hard: boolean;
  message: string;
}

export interface RelaxedConstraint {
  code: string;
  message: string;
}

export interface ConstraintCheckResult {
  allowed: boolean;
  is_hard_violation: boolean;
  violations: ConstraintViolation[];
  relaxed_soft_constraints: RelaxedConstraint[];
}

export interface CheckinBoardData {
  counts: {
    pending_count: number;
    arrived_count: number;
    checked_in_count: number;
    late_arrivals_count: number;
  };
  late_arrivals: Array<{
    participant_id: string;
    name: string;
    college: string;
    contingent_id: string;
    flight_pnr?: string;
    expected_arrival: string;
    delay_minutes: number;
    is_curfew_breach: boolean;
    notes: string;
  }>;
  recent_checkins: Array<{
    participant_id: string;
    name: string;
    college: string;
    room_number: string;
    checked_in_at: string;
    volunteer: string;
  }>;
}

export interface ParticipantCheckinDetail {
  participant: {
    id: string;
    name: string;
    contingent_id: string;
    college: string;
    role: string;
    status: string;
    gender: string;
    age: number;
    is_minor: boolean;
    diet: string;
    accommodation_requested: string;
  };
  room_assignment?: {
    bed_id: string;
    room_number: string;
    building: string;
    floor: number;
    cleaning_status: string;
    cleaning_ready_at: string;
    is_accessible: boolean;
  };
  alerts: {
    accessibility?: string | null;
    diet?: string | null;
    safety?: string | null;
  };
  unknown_prompts: Array<{
    field: string;
    prompt: string;
    options: string[];
  }>;
}
