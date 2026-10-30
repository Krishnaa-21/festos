export interface TimelineBlock {
  session_id: string;
  event_id: string;
  event_name: string;
  round: string;
  heat: string;
  start: string;
  end: string;
  setup_start: string;
  teardown_end: string;
  entrants_count: number;
  judges_assigned: number;
  judges_needed: number;
  judge_gap: boolean;
  status: string;
}

export interface VenueTimeline {
  venue_id: string;
  venue_name: string;
  blocks: TimelineBlock[];
}

export type ConflictType =
  | "VENUE_DOUBLE_BOOKING"
  | "PARTICIPANT_CLASH"
  | "JUDGE_DOUBLE_BOOKING"
  | "TEARDOWN_SETUP_OVERLAP"
  | "TRAVEL_TIME_INSUFFICIENT"
  | "ROUND_DEPENDENCY_TIMING"
  | "ARRIVAL_WINDOW_BREACH"
  | "CAPACITY_EXCEEDED"
  | "EQUIPMENT_UNAVAILABLE"
  | "ACCESSIBILITY_UNMET";

export interface ScheduleConflict {
  id: string;
  conflict_type: ConflictType;
  severity: number;
  status: "OPEN" | "RESOLVED" | "ACCEPTED";
  description: string;
  people_affected: number;
  entity_refs: Record<string, string>;
}

export interface ResolutionCandidate {
  id: string;
  rank: number;
  action: string;
  rationale: string;
  conflicts_resolved: number;
  new_conflicts_created: number;
  people_affected: number;
  suggested_start_at?: string;
  suggested_venue_id?: string;
}

export interface UnscheduledEntrant {
  participant_id: string;
  participant_name: string;
  event_id: string;
  event_name: string;
  contingent_id: string;
  contingent_name: string;
  reason: "NOT_ON_SITE_LONG_ENOUGH" | "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH";
  arrival_datetime: string;
  departure_datetime: string;
  alternatives: string[];
}

export interface ScheduleVersion {
  id: string;
  plan_name: string;
  status: string;
  sessions_count: number;
  conflicts_count: number;
  unscheduled_count: number;
  created_at: string;
  created_by: string;
  is_active: boolean;
}

export interface EventItem {
  id: string;
  name: string;
  solo_team: "SOLO" | "TEAM";
  rounds: number;
  rounds_text: string;
  duration_min: number;
  venue_requirements: string;
  equipment_needs: string;
  volunteers_needed: number;
  judges_needed: number;
  registrations_count: number;
  status: string;
}

export interface VenueItem {
  id: string;
  name: string;
  capacity: number;
  indoor_outdoor: "indoor" | "outdoor";
  accessible: boolean;
  setup_time_min: number;
  teardown_time_min: number;
  feature_tags: string[];
  availability_windows: string;
  status: string;
}

export interface FairnessDecision {
  id: string;
  title: string;
  type: "LATE_WAVE" | "WILDCARD_FINALS";
  status: "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
  requires_role: string;
  affected_participants: number;
  reason: string;
  action_route: string;
}
