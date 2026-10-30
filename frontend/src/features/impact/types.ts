export interface ImpactTreeNode {
  id: string;
  type: "participant" | "accommodation" | "event" | "venue" | "vendor" | "transport" | "staff" | "inventory";
  label: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  peopleAffected: number;
  status: "AT_RISK" | "DISRUPTED" | "REALLOCATED" | "MITIGATED" | "NORMAL";
  details?: Record<string, any>;
  children?: ImpactTreeNode[];
}

export interface ImpactReportData {
  rootChange: {
    id: string;
    action: string;
    entityType: string;
    entityId: string;
    description: string;
    triggeredAt: string;
    actor: string;
  };
  countsByType: {
    participants: number;
    accommodation: number;
    events: number;
    venues: number;
    vendors: number;
    transport: number;
    staff: number;
    inventory: number;
  };
  tree: ImpactTreeNode[];
  beforeAfterComparison: {
    metric: string;
    before: string | number;
    after: string | number;
    delta: string;
    status: "improved" | "degraded" | "neutral";
  }[];
}

