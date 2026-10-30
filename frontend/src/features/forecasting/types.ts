export interface ForecastTimeSeriesPoint {
  timeLabel: string;
  hour: string;
  date: string;
  // Projection (solid / verified)
  confirmedDemand: number;
  confirmedCapacity: number;
  // Assumption (dashed / heuristic)
  assumedSurgeDemand: number;
  projectedTotalDemand: number;
  assumedCapacityCeiling: number;
  isProjectedGap: boolean;
}

export interface AssumptionItem {
  key: string;
  label: string;
  value: string | number;
  unit?: string;
  owner: string;
  source: string;
  reason: string;
  impactIfChanged: string;
  category: "accommodation" | "schedule" | "food" | "transport" | "operations";
}

export interface ForecastDataset {
  domain: "accommodation" | "food" | "transport";
  title: string;
  description: string;
  unit: string;
  points: ForecastTimeSeriesPoint[];
  relatedAssumptionKeys: string[];
}
