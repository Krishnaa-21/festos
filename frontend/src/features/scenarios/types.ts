export interface SandboxMetric {
  key: string;
  label: string;
  liveValue: number | string;
  scenarioValue: number | string;
  delta: number | string;
  unit?: string;
  impactStatus: "IMPROVED" | "DEGRADED" | "NEUTRAL";
}

export interface ScenarioDisruptionOption {
  id: string;
  name: string;
  description: string;
  defaultTarget: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM";
  category: "accommodation" | "food" | "events" | "logistics" | "staff" | "transport";
}

export interface SimulationScenario {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  actorId: string;
  actorName: string;
  status: "ACTIVE" | "COMMITTED" | "DISCARDED";
  isStale: boolean;
  liveMutationsSinceFork: number;
  lastSyncedAt: string;
  disruptionsApplied: Array<{
    id: string;
    disruptionId: string;
    targetId: string;
    appliedAt: string;
    summary: string;
  }>;
  metricsComparison: SandboxMetric[];
  candidatePlans: Array<{
    id: string;
    name: string;
    strategy: string;
    peopleMoved: number;
    costDeltaInr: number;
    scheduleChanges: number;
    constraintsRelaxed: string[];
    isRecommended: boolean;
  }>;
  selectedPlanId?: string;
}

