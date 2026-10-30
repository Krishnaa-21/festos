export interface SoftConstraintRelaxed {
  constraint: string;
  rationale: string;
  ladderPriority: number; // 1 Cohesion, 2 Cost, 3 Proximity
}

export interface AlternativeRejected {
  option: string;
  why: string;
}

export interface DecisionCardItem {
  id: string;
  module: "accommodation" | "vendors" | "food" | "schedule" | "transport" | "incidents" | "unknowns" | "finance" | "governance";
  decisionType: string;
  title: string;
  summary: string;
  why: string;
  hardConstraintsSatisfied: string[];
  softConstraintsRelaxed: SoftConstraintRelaxed[];
  alternativesRejected: AlternativeRejected[];
  costImpactInr: number;
  peopleAffected: number;
  approverName: string;
  approverRole: string;
  createdAt: string;
  overrideId?: string;
  changeSetId?: string;
  status: "RECORDED" | "SUPERSEDED" | "REVERTED";
}

