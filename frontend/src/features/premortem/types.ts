export interface HourlyPremortemState {
  hourIndex: number; // 0 to 71
  timestamp: string; // ISO 8601
  festDay: "Day 1 (Arrivals)" | "Day 2 (Main Events)" | "Day 3 (Finals & Close)";
  timeLabel: string; // e.g. "Oct 31, 14:00"
  bedOccupancy: {
    campusOccupied: number;
    externalOccupied: number;
    totalAvailable: number;
    occupancyPct: number;
    unplacedCount: number;
  };
  foodDemand: {
    activeSlotName: string; // "Breakfast", "Lunch", "High Tea", "Dinner", "Night Snack", "None"
    confirmedDemand: number;
    vendorCapacity: number;
    deficit: number;
    specialDietaryGap: number; // Jain / Vegan
  };
  venueUtilisation: {
    overallPct: number;
    activeVenuesCount: number;
    totalVenues: number;
    peakVenue: string;
  };
  equipmentDemand: {
    audioConsolesInUse: number;
    projectorsInUse: number;
    powerGeneratorsInUse: number;
    criticalShortageCount: number;
  };
  volunteerCoverage: {
    demandCount: number;
    onShiftCount: number;
    uncoveredSlots: number;
    overloadedCount: number;
  };
  transport: {
    shuttleDemandSeats: number;
    confirmedCapacitySeats: number;
    deficitSeats: number;
    activeEscorts: number;
  };
  activeCriticalRisks: Array<{
    id: string;
    title: string;
    severity: "CRITICAL" | "HIGH" | "MEDIUM";
    peopleAffected: number;
    explanation: string;
    preventiveAction: string;
    route: string;
  }>;
}

export interface SpofItem {
  id: string;
  name: string;
  component: string;
  vulnerability: string;
  failureImpact: string;
  peopleAtRisk: number;
  resilienceTier: "CRITICAL" | "HIGH" | "MODERATE";
  recommendedMitigation: string;
  mitigationRoute?: string;
}

export interface PreventiveActionItem {
  id: string;
  title: string;
  category: "Accommodation" | "Food" | "Power" | "Transport" | "Staff";
  urgency: "IMMEDIATE" | "BEFORE_DAY_2" | "OPTIONAL";
  projectedRiskReductionPct: number;
  status: "PENDING" | "PLANNED" | "EXECUTED";
  actionLabel: string;
  actionRoute: string;
}

export interface ComponentResilienceScore {
  component: string;
  score: number; // 0 to 100
  weight: number;
  status: "HEALTHY" | "VULNERABLE" | "CRITICAL";
  keyVulnerability: string;
}

export interface FestResilienceReport {
  overallScore: number; // 0 to 100
  grade: "RESILIENT" | "MODERATE RESILIENCE" | "FRAGILE" | "AT RISK";
  components: ComponentResilienceScore[];
  methodology: {
    title: string;
    description: string;
    formula: string;
    ladderRule: string;
  };
}

export interface PremortemScenarioLog {
  id: string;
  title: string;
  testedHour: string;
  injectedDisruption: string;
  outcome: "MITIGATED" | "CONTAINED" | "CASCADE_FAILURE";
  testedAt: string;
  testedBy: string;
}
