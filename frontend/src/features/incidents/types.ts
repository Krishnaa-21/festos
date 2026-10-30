export type ScenarioId =
  | "late_contingent"
  | "duplicate_participant"
  | "hostel_closure"
  | "equipment_failure"
  | "venue_change"
  | "vendor_shutdown"
  | "duplicate_merchandise_claim"
  | "dining_power_outage"
  | "wildcard_surge"
  | "medical_escort"
  | "keycard_wave"
  | "flash_weather";

export interface ScenarioDefinition {
  id: ScenarioId;
  title: string;
  category: "Accommodation" | "Events" | "Vendors" | "Participants" | "Logistics" | "Operations";
  description: string;
  defaultSeverity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  isPrimary: boolean;
  defaultParams: Record<string, any>;
  paramFields: Array<{
    name: string;
    label: string;
    type: "text" | "number" | "select";
    options?: Array<{ value: string; label: string }>;
    defaultValue: any;
  }>;
}

export interface DownstreamUpdateItem {
  id: string;
  domain: "Accommodation" | "Schedule" | "Catering" | "Transport" | "Logistics" | "Staff" | "Finance";
  label: string;
  status: "PENDING" | "UPDATED" | "VERIFIED";
  details: string;
  entityRoute: string;
  verifiedAt?: string;
  verifiedBy?: string;
}

export interface RecoveryPlanOption {
  id: "plan_a" | "plan_b" | "plan_c";
  name: string;
  strategy: string;
  isRecommended: boolean;
  peopleMoved: number;
  scheduleChanges: number;
  resourceMoves: number;
  costDeltaInr: number;
  constraintsRelaxed: Array<{
    type: "SOFT" | "HARD";
    constraint: string;
    rationale: string;
  }>;
  summary: string;
}

export interface DryRunImpact {
  incidentId: string;
  scenarioId: ScenarioId;
  title: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  peopleAffected: number;
  affectedEntities: {
    participants: number;
    rooms: number;
    events: number;
    venues: number;
    meals: number;
    shuttles: number;
    staff: number;
  };
  keyRisks: string[];
  plans: RecoveryPlanOption[];
  simulatedTimeDeltaMin: number;
}

export interface IncidentRecord {
  id: string;
  scenarioId: ScenarioId;
  title: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "ACTIVE" | "INVESTIGATING" | "RESOLVING" | "RESOLVED" | "SIMULATED";
  createdAt: string;
  resolvedAt?: string;
  peopleAffected: number;
  approvedPlan?: string;
  approvedBy?: string;
  approvalReason?: string;
  downstreamUpdates: DownstreamUpdateItem[];
  beforeMetrics: {
    unplacedParticipants: number;
    mealShortages: number;
    delayedEvents: number;
    transportDeficit: number;
    extraCostInr: number;
  };
  afterMetrics: {
    unplacedParticipants: number;
    mealShortages: number;
    delayedEvents: number;
    transportDeficit: number;
    extraCostInr: number;
  };
}
