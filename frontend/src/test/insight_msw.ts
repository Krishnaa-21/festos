import { http, HttpResponse } from "msw";
import {
  DashboardMetricsResponse,
  AttentionItem,
  HeatmapCell,
} from "../features/dashboard/types";
import {
  SimulationScenario,
  ScenarioDisruptionOption,
} from "../features/scenarios/types";
import {
  HourlyPremortemState,
  SpofItem,
  PreventiveActionItem,
  FestResilienceReport,
} from "../features/premortem/types";
import {
  ForecastDataset,
  AssumptionItem,
} from "../features/forecasting/types";
import { DecisionCardItem } from "../features/decisions/types";
import {
  UnknownQueueItem,
  WhyNotParticipantExplanation,
} from "../features/unknowns/types";

// ============================================================================
// 1. DASHBOARD OVERVIEW MOCK DATA
// ============================================================================

export let mockDashboardMetrics: DashboardMetricsResponse = {
  total_participants: 2836,
  narrative_participants: 2400,
  raw_participants: 2836,
  arrived: 1420,
  checked_in: 1285,
  pending_arrivals: 1416,
  occupancy_pct: 94.2,
  available_beds: 58,
  unplaced_participants: 85,
  active_sessions: 14,
  open_conflicts: 3,
  equipment_availability: 88.5,
  equipment_in_transit: 12,
  equipment_under_repair: 4,
  merchandise_stock: 420,
  merch_issued: 2416,
  vendor_status: "DEGRADED",
  food_coverage_gaps: 2,
  uncovered_meals: 220,
  staff_availability: 42,
  core_team_active: 48,
  peak_staffing_gap: 6,
  open_incidents: 2,
  pending_approvals: 4,
  active_overrides: 3,
  calculated_at: new Date().toISOString(),
};

export let mockAttentionQueue: AttentionItem[] = [
  {
    id: "att_01",
    module: "accommodation",
    kind: "ACCESSIBILITY_ARRIVAL_IMMINENT",
    title: "3 Participants with unconfirmed ground-floor accessibility needs arriving within 2h",
    severity: "CRITICAL",
    severityLevel: 4,
    urgencyLevel: 5, // <=1h
    hoursToImpact: 1.2,
    peopleAffected: 3,
    uncertainty: 0.05,
    resourceCriticality: 5,
    attentionScore: 4 * 5 * 3, // 60
    action: {
      label: "Assign Accessible Rooms",
      route: "/accommodation",
      api: "/api/v1/accommodation/allocate",
    },
    explanation: "Wheelchair-accessible ground-floor beds in Hostel 1 & 2 are unallocated. Fast-track allocation required.",
  },
  {
    id: "att_02",
    module: "food",
    kind: "DIETARY_SHORTAGE_IMMINENT",
    title: "220 Jain & Vegan lunch meals unassigned due to Spice Kitchen (VND04) health pause",
    severity: "CRITICAL",
    severityLevel: 4,
    urgencyLevel: 4, // <=4h
    hoursToImpact: 2.5,
    peopleAffected: 220,
    uncertainty: 0.1,
    resourceCriticality: 5,
    attentionScore: 4 * 4 * 220, // 3520
    action: {
      label: "Reallocate to Annapurna",
      route: "/food",
      api: "/api/v1/food/reallocate",
    },
    explanation: "Spice Kitchen failed sudden safety inspection. Divert dietary vouchers to Annapurna Caterers.",
  },
  {
    id: "att_03",
    module: "accommodation",
    kind: "UNPLACED_BED_SHORTAGE",
    title: "85 Participants stranded in Hostel 3 basement waterline burst",
    severity: "CRITICAL",
    severityLevel: 4,
    urgencyLevel: 4, // <=4h
    hoursToImpact: 3.0,
    peopleAffected: 85,
    uncertainty: 0.15,
    resourceCriticality: 4,
    attentionScore: 4 * 4 * 85, // 1360
    action: {
      label: "Evacuate to Lakeview",
      route: "/incidents",
      api: "/api/v1/incidents/dry-run",
    },
    explanation: "Hostel 3 plumbing main line failure forced immediate evacuation of 85 residents.",
  },
  {
    id: "att_04",
    module: "transport",
    kind: "SHUTTLE_CAPACITY_DEFICIT",
    title: "Lakeview midnight shuttle route exceeds confirmed fleet capacity by 14 seats",
    severity: "HIGH",
    severityLevel: 3,
    urgencyLevel: 3, // <=12h
    hoursToImpact: 8.0,
    peopleAffected: 14,
    uncertainty: 0.2,
    resourceCriticality: 3,
    attentionScore: 3 * 3 * 14, // 126
    action: {
      label: "Dispatch Extra Shuttle",
      route: "/transport",
      api: "/api/v1/transport/shuttles",
    },
    explanation: "Late-night return surge from Main Auditorium requires an additional 14-seater loop.",
  },
  {
    id: "att_05",
    module: "staff",
    kind: "UNCOVERED_CONCOURSE_SHIFT",
    title: "Registration Concourse shift (12:00-14:00) is uncovered: 1 volunteer missing",
    severity: "MEDIUM",
    severityLevel: 2,
    urgencyLevel: 4, // <=4h
    hoursToImpact: 2.0,
    peopleAffected: 65,
    uncertainty: 0.05,
    resourceCriticality: 3,
    attentionScore: 2 * 4 * 65, // 520
    action: {
      label: "Emergency Replace Staff",
      route: "/staff",
      api: "/api/v1/staff/emergency-replace",
    },
    explanation: "Volunteer Pooja Sharma has worked 11 consecutive hours and requires mandatory relief.",
  },
  {
    id: "att_06",
    module: "unknowns",
    kind: "UNKNOWN_GENDER_CORRIDOR",
    title: "417 Participants with UNKNOWN gender blocking hostel corridor segregation",
    severity: "HIGH",
    severityLevel: 3,
    urgencyLevel: 2, // <=24h
    hoursToImpact: 18.0,
    peopleAffected: 417,
    uncertainty: 0.5,
    resourceCriticality: 4,
    attentionScore: 3 * 2 * 417, // 2502
    action: {
      label: "Burn Down Unknowns",
      route: "/unknowns",
      api: "/api/v1/unknowns/token",
    },
    explanation: "Room allocation engine cannot auto-assign beds without violating gender buffer constraints.",
  },
];

// Helper to compute attention score
function computeAttentionScore(item: AttentionItem): number {
  return item.severityLevel * item.urgencyLevel * Math.max(item.peopleAffected, 1);
}

// ============================================================================
// 2. SCENARIO SIMULATOR MOCK DATA
// ============================================================================

export const mockDisruptionCatalog: ScenarioDisruptionOption[] = [
  {
    id: "hostel_closure",
    name: "Hostel 3 Plumbing Failure (85 Beds)",
    description: "Basement waterline rupture floods electrical conduits. Requires immediate evacuation of 85 students.",
    defaultTarget: "HOSTEL-03",
    severity: "CRITICAL",
    category: "accommodation",
  },
  {
    id: "vendor_shutdown",
    name: "Spice Kitchen (VND04) Health Shutdown",
    description: "FSSAI safety compliance violation forces closure of stall VND04, creating a 220 Jain/Vegan meal deficit.",
    defaultTarget: "VND04",
    severity: "HIGH",
    category: "food",
  },
  {
    id: "equipment_failure",
    name: "Main Auditorium PA Audio Console Failure",
    description: "Yamaha CL5 master console power supply blown 45 minutes before keynote.",
    defaultTarget: "EQ-AUDIO-01",
    severity: "HIGH",
    category: "logistics",
  },
  {
    id: "wildcard_surge",
    name: "Wildcard Finalist Surge (+65 Participants)",
    description: "Late qualifiers arrive unannounced from East zone, exceeding booked room inventory.",
    defaultTarget: "CONTINGENT_EAST",
    severity: "HIGH",
    category: "accommodation",
  },
];

export let mockScenarios: SimulationScenario[] = [
  {
    id: "scen_live_fork_01",
    name: "Hostel 3 Emergency Evacuation Sandbox",
    description: "Testbed for reallocating 85 students to Lakeview Resort without impacting production state.",
    createdAt: "2026-10-31T07:00:00Z",
    actorId: "usr_dir_001",
    actorName: "Dr. Devashish Roy (Festival Director)",
    status: "ACTIVE",
    isStale: false,
    liveMutationsSinceFork: 0,
    lastSyncedAt: "2026-10-31T07:00:00Z",
    disruptionsApplied: [
      {
        id: "da_01",
        disruptionId: "hostel_closure",
        targetId: "HOSTEL-03",
        appliedAt: "2026-10-31T07:05:00Z",
        summary: "Injected 85 unplaced beds in Hostel 3 basement flooding simulation.",
      },
    ],
    metricsComparison: [
      {
        key: "unplaced_participants",
        label: "Unplaced Participants",
        liveValue: 85,
        scenarioValue: 0,
        delta: -85,
        impactStatus: "IMPROVED",
      },
      {
        key: "meal_shortages",
        label: "Meal Shortages",
        liveValue: 85,
        scenarioValue: 0,
        delta: -85,
        impactStatus: "IMPROVED",
      },
      {
        key: "schedule_delays_min",
        label: "Schedule Delay",
        liveValue: 0,
        scenarioValue: 45,
        delta: "+45m",
        unit: "min",
        impactStatus: "DEGRADED",
      },
      {
        key: "cost_delta_inr",
        label: "Additional Cost",
        liveValue: 0,
        scenarioValue: 42500,
        delta: "+₹42,500",
        unit: "INR",
        impactStatus: "DEGRADED",
      },
      {
        key: "contingent_cohesion_pct",
        label: "Contingent Cohesion",
        liveValue: 98,
        scenarioValue: 96,
        delta: "-2%",
        impactStatus: "NEUTRAL",
      },
    ],
    candidatePlans: [
      {
        id: "plan_a",
        name: "Plan A: Cohesion-First Evacuation",
        strategy: "Keep contingents intact at Lakeview Resort and Campus Guest House.",
        peopleMoved: 85,
        costDeltaInr: 42500,
        scheduleChanges: 1,
        constraintsRelaxed: ["Proximity ladder: Campus vs External (Soft)"],
        isRecommended: true,
      },
      {
        id: "plan_b",
        name: "Plan B: Cost-First Distribution",
        strategy: "Disperse students into cheaper scattered lodges across town.",
        peopleMoved: 85,
        costDeltaInr: 21000,
        scheduleChanges: 4,
        constraintsRelaxed: ["Contingent cohesion (Soft)", "Proximity (Soft)"],
        isRecommended: false,
      },
    ],
    selectedPlanId: "plan_a",
  },
  {
    id: "scen_stale_demo",
    name: "Stale Fork: Vendor Surge Experiment",
    description: "Created 2 hours ago; live DB has since processed 4 new participant check-ins.",
    createdAt: "2026-10-31T05:00:00Z",
    actorId: "usr_food_001",
    actorName: "Kavita Rao (Food Ops Lead)",
    status: "ACTIVE",
    isStale: true,
    liveMutationsSinceFork: 4,
    lastSyncedAt: "2026-10-31T05:00:00Z",
    disruptionsApplied: [],
    metricsComparison: [
      {
        key: "uncovered_meals",
        label: "Uncovered Meals",
        liveValue: 220,
        scenarioValue: 180,
        delta: -40,
        impactStatus: "IMPROVED",
      },
    ],
    candidatePlans: [],
  },
];

// ============================================================================
// 3. FEST PRE-MORTEM MOCK DATA (72-HOUR TIMELINE SCRUBBER)
// ============================================================================

export function generatePremortemHours(): HourlyPremortemState[] {
  const hours: HourlyPremortemState[] = [];
  const startEpoch = new Date("2026-10-30T06:00:00Z").getTime();

  for (let i = 0; i < 72; i++) {
    const currentMs = startEpoch + i * 3600 * 1000;
    const dt = new Date(currentMs);
    const dayIndex = Math.floor(i / 24);
    const dayLabel =
      dayIndex === 0
        ? "Day 1 (Arrivals)"
        : dayIndex === 1
        ? "Day 2 (Main Events)"
        : "Day 3 (Finals & Close)";

    const hourOfDay = dt.getUTCHours();
    const timeLabel = `${dt.toISOString().substring(5, 10)} ${String(hourOfDay).padStart(2, "0")}:00`;

    // Dynamic wave curves over the 3 days
    // Bed occupancy starts lower on Day 1, peaks on Day 2 night (1601 peak beds)
    let campusOccupied = 450 + Math.min(260, Math.floor(i * 5));
    if (campusOccupied > 710) campusOccupied = 705;
    let externalOccupied = Math.max(0, Math.floor(i * 12));
    if (externalOccupied > 740) externalOccupied = 720;
    const totalAvail = 710 + 740 - (campusOccupied + externalOccupied);

    // Food slot
    let slotName = "None";
    let confirmedDemand = 0;
    let deficit = 0;
    let dietaryGap = 0;
    if (hourOfDay >= 7 && hourOfDay <= 9) {
      slotName = "Breakfast";
      confirmedDemand = 1650;
    } else if (hourOfDay >= 12 && hourOfDay <= 14) {
      slotName = "Lunch";
      confirmedDemand = 2200;
      if (i >= 26 && i <= 34) {
        // Critical hour spike around Day 2 Lunch (hour 28-32)
        deficit = 220;
        dietaryGap = 220;
      }
    } else if (hourOfDay >= 16 && hourOfDay <= 17) {
      slotName = "High Tea";
      confirmedDemand = 1100;
    } else if (hourOfDay >= 19 && hourOfDay <= 22) {
      slotName = "Dinner";
      confirmedDemand = 2350;
    }

    // Critical risks appearing dynamically at critical hours
    const activeCriticalRisks: HourlyPremortemState["activeCriticalRisks"] = [];

    // Hour 14 (Day 1 Evening): Concourse registration surge
    if (i >= 12 && i <= 16) {
      activeCriticalRisks.push({
        id: "risk_h14_concourse",
        title: "Registration Concourse Bottleneck: 450 arrivals per hour",
        severity: "HIGH",
        peopleAffected: 450,
        explanation: "Check-in desk scan capacity (300/hr) breached by simultaneous arrival of Western Railway contingents.",
        preventiveAction: "Pre-kit 500 kitbags and open 4 Express QR lanes.",
        route: "/checkin",
      });
    }

    // Hour 28 to 32 (Day 2 Lunch): Vendor failure & power overload
    if (i >= 28 && i <= 32) {
      activeCriticalRisks.push({
        id: "risk_h30_food_spof",
        title: "Critical Food SPOF: Spice Kitchen shutdown creates 220 Jain meal gap",
        severity: "CRITICAL",
        peopleAffected: 220,
        explanation: "West Campus has no backup FSSAI-certified Jain caterer within 5km.",
        preventiveAction: "Activate Annapurna emergency annex standby contract.",
        route: "/food",
      });
      activeCriticalRisks.push({
        id: "risk_h30_generator",
        title: "Main Auditorium Generator G01 thermal trip risk at 92% load",
        severity: "CRITICAL",
        peopleAffected: 850,
        explanation: "Stage 1 spotlights + PA system exceed single generator safety threshold during opening acts.",
        preventiveAction: "Deploy backup 125kVA generator G02 in parallel synchronization.",
        route: "/logistics",
      });
    }

    // Hour 42 to 46 (Day 2 Midnight): Lakeview shuttle deficit
    if (i >= 42 && i <= 46) {
      activeCriticalRisks.push({
        id: "risk_h44_transit",
        title: "Night transit deficit: 14 students stranded without return shuttle",
        severity: "HIGH",
        peopleAffected: 14,
        explanation: "Cultural night overruns schedule by 45 minutes; scheduled shuttle fleet finishes at 23:30.",
        preventiveAction: "Extend shuttle operation hours to 02:00 with security escort.",
        route: "/transport",
      });
    }

    hours.push({
      hourIndex: i,
      timestamp: dt.toISOString(),
      festDay: dayLabel,
      timeLabel,
      bedOccupancy: {
        campusOccupied,
        externalOccupied,
        totalAvailable: Math.max(0, totalAvail),
        occupancyPct: Math.round(((campusOccupied + externalOccupied) / 1450) * 100),
        unplacedCount: i >= 20 && i <= 36 ? 85 : 0,
      },
      foodDemand: {
        activeSlotName: slotName,
        confirmedDemand,
        vendorCapacity: slotName !== "None" ? 2400 : 0,
        deficit,
        specialDietaryGap: dietaryGap,
      },
      venueUtilisation: {
        overallPct: hourOfDay >= 9 && hourOfDay <= 21 ? 84 : 22,
        activeVenuesCount: hourOfDay >= 9 && hourOfDay <= 21 ? 8 : 2,
        totalVenues: 9,
        peakVenue: "Main Auditorium (V01)",
      },
      equipmentDemand: {
        audioConsolesInUse: hourOfDay >= 9 && hourOfDay <= 22 ? 8 : 2,
        projectorsInUse: hourOfDay >= 9 && hourOfDay <= 20 ? 12 : 3,
        powerGeneratorsInUse: hourOfDay >= 9 && hourOfDay <= 23 ? 3 : 1,
        criticalShortageCount: i >= 28 && i <= 32 ? 1 : 0,
      },
      volunteerCoverage: {
        demandCount: hourOfDay >= 8 && hourOfDay <= 22 ? 48 : 12,
        onShiftCount: hourOfDay >= 8 && hourOfDay <= 22 ? 44 : 14,
        uncoveredSlots: hourOfDay >= 8 && hourOfDay <= 22 ? 4 : 0,
        overloadedCount: hourOfDay >= 14 && hourOfDay <= 18 ? 3 : 0,
      },
      transport: {
        shuttleDemandSeats: hourOfDay >= 22 || hourOfDay <= 2 ? 64 : 24,
        confirmedCapacitySeats: 48,
        deficitSeats: hourOfDay >= 22 || hourOfDay <= 2 ? 16 : 0,
        activeEscorts: 4,
      },
      activeCriticalRisks,
    });
  }

  return hours;
}

export let mockPremortemHours = generatePremortemHours();

export let mockSpofList: SpofItem[] = [
  {
    id: "spof_01",
    name: "Main Auditorium Master Generator G01",
    component: "Power & Electrical Infrastructure",
    vulnerability: "Powers Auditorium A & Central Stage 1; operates at 92% load without hot-spare auto-transfer.",
    failureImpact: "Instant blackout of 850 audience seats and video livestream blackout.",
    peopleAtRisk: 850,
    resilienceTier: "CRITICAL",
    recommendedMitigation: "Pre-position 125kVA Standby Generator G02 with manual transfer switch.",
    mitigationRoute: "/logistics",
  },
  {
    id: "spof_02",
    name: "Spice Kitchen (VND04) - West Campus",
    component: "Catering & Dietary Compliance",
    vulnerability: "Sole vendor certified for Jain/Vegan warm lunches on West campus academic quad.",
    failureImpact: "220 participants with dietary restrictions go without food within 90 minutes of failure.",
    peopleAtRisk: 220,
    resilienceTier: "CRITICAL",
    recommendedMitigation: "Contract Annapurna Caterers for 250-pack emergency standby Jain buffer.",
    mitigationRoute: "/food",
  },
  {
    id: "spof_03",
    name: "Hostel 3 Plumbing / Electrical Conduit Riser",
    component: "Campus Accommodation",
    vulnerability: "Single water line junction above electrical shaft in basement.",
    failureImpact: "Flooding shuts down 85 beds across 3 floors simultaneously.",
    peopleAtRisk: 85,
    resilienceTier: "HIGH",
    recommendedMitigation: "Inspect shut-off valve; block 50 contingency beds at Lakeview Resort.",
    mitigationRoute: "/accommodation",
  },
  {
    id: "spof_04",
    name: "Lakeview Late-Night Shuttle Loop",
    component: "Transit & Night Safety",
    vulnerability: "Single 12-seater vehicle V3 operating between 23:00 and 02:00.",
    failureImpact: "Breakdown strands 40+ students overnight at external resort with no public transit.",
    peopleAtRisk: 40,
    resilienceTier: "HIGH",
    recommendedMitigation: "Pair V3 with backup vehicle V1 and verified night escort team.",
    mitigationRoute: "/transport",
  },
];

export let mockPreventiveActions: PreventiveActionItem[] = [
  {
    id: "pa_01",
    title: "Deploy 125kVA Standby Generator to Main Stage",
    category: "Power",
    urgency: "IMMEDIATE",
    projectedRiskReductionPct: 18,
    status: "PENDING",
    actionLabel: "Requisition Generator",
    actionRoute: "/logistics",
  },
  {
    id: "pa_02",
    title: "Pre-authorize Emergency Catering Agreement with Annapurna",
    category: "Food",
    urgency: "BEFORE_DAY_2",
    projectedRiskReductionPct: 24,
    status: "PLANNED",
    actionLabel: "Approve Standby PO",
    actionRoute: "/food",
  },
  {
    id: "pa_03",
    title: "Block 45 Contingency Beds at Lakeview Resort",
    category: "Accommodation",
    urgency: "BEFORE_DAY_2",
    projectedRiskReductionPct: 15,
    status: "EXECUTED",
    actionLabel: "View Allocation",
    actionRoute: "/accommodation",
  },
  {
    id: "pa_04",
    title: "Schedule Supplementary Shuttle Run S-04 for Midnight",
    category: "Transport",
    urgency: "BEFORE_DAY_2",
    projectedRiskReductionPct: 12,
    status: "PENDING",
    actionLabel: "Confirm Shuttle Run",
    actionRoute: "/transport",
  },
];

export let mockResilienceReport: FestResilienceReport = {
  overallScore: 78,
  grade: "MODERATE RESILIENCE",
  components: [
    {
      component: "Accommodation & Housing",
      score: 82,
      weight: 0.25,
      status: "HEALTHY",
      keyVulnerability: "Buffer depleted if unplaced participants exceed 65 beds.",
    },
    {
      component: "Food Ops & Dietary Integrity",
      score: 68,
      weight: 0.25,
      status: "VULNERABLE",
      keyVulnerability: "Jain/Vegan catering lacks local redundancy on West Campus quad.",
    },
    {
      component: "Logistics & Stage Power",
      score: 85,
      weight: 0.2,
      status: "HEALTHY",
      keyVulnerability: "High dependency on Generator G01 for prime keynote window.",
    },
    {
      component: "Staffing & Volunteer Coverage",
      score: 74,
      weight: 0.15,
      status: "HEALTHY",
      keyVulnerability: "Registration concourse peak shift (12:00-14:00) has zero volunteer slack.",
    },
    {
      component: "Transport & Night Safety",
      score: 79,
      weight: 0.15,
      status: "HEALTHY",
      keyVulnerability: "Midnight shuttle deficit of 14 seats on Lakeview loop.",
    },
  ],
  methodology: {
    title: "FestOS Weighted Resilience Scoring (FWS v1.2)",
    description: "The FestOS Resilience Score aggregates real-time headroom and redundancy buffers across the 5 core operational domains. Weights reflect participant safety and critical operational continuity.",
    formula: "Resilience Score = ∑ (Component_Score_i × Weight_i) - (Critical_SPOF_Penalty)",
    ladderRule: "Hard safety constraints (gender segregation, minor protection, FSSAI) deduct 15 points per active breach; soft constraint relaxations deduct 3 points.",
  },
};

// ============================================================================
// 4. FORECASTING CHARTS MOCK DATA (RECHARTS COMPATIBLE)
// ============================================================================

export let mockAssumptions: AssumptionItem[] = [
  {
    key: "cleaning_buffer_minutes",
    label: "Room Cleaning Buffer",
    value: 180,
    unit: "min",
    owner: "ACCOMMODATION_LEAD",
    source: "Hostel Warden Protocol v2",
    reason: "Mandatory sanitary turnover buffer between departing and arriving cohorts.",
    impactIfChanged: "Reducing to 60 min increases bed availability by 42 beds during turnover but strains housekeeping staff.",
    category: "accommodation",
  },
  {
    key: "shuttle_capacity_seats",
    label: "Standard Shuttle Capacity",
    value: 12,
    unit: "seats",
    owner: "LOGISTICS_MANAGER",
    source: "Travel Desk Fleet Roster",
    reason: "Standard seating capacity of contracted Force Traveller vehicles.",
    impactIfChanged: "Upgrading to 24-seater buses eliminates the midnight transit deficit.",
    category: "transport",
  },
  {
    key: "semifinal_ratio",
    label: "Semifinalist Advancement Ratio",
    value: 0.5,
    owner: "EVENT_LEAD",
    source: "Academic Rulebook 2026",
    reason: "Assumes 50% of registered debate/case teams advance to Day 2 afternoon rounds.",
    impactIfChanged: "Higher ratio increases venue stage utilization by 1.5 hours.",
    category: "schedule",
  },
  {
    key: "walkin_meal_buffer_pct",
    label: "Heuristic Walk-in Meal Buffer",
    value: 10,
    unit: "%",
    owner: "FOOD_OPS_MANAGER",
    source: "Catering Committee Heuristic",
    reason: "Buffer added to confirmed participant headcounts to absorb judges and faculty.",
    impactIfChanged: "Increasing to 15% costs ₹18,000 extra but guarantees zero meal rejections.",
    category: "food",
  },
  {
    key: "minor_age_threshold",
    label: "Minor Safety Protection Threshold",
    value: 18,
    unit: "years",
    owner: "FESTIVAL_DIRECTOR",
    source: "IIM Indore Institutional Policy",
    reason: "Legal adult age threshold requiring parental consent for external accommodation.",
    impactIfChanged: "Hard safety policy constraint. Cannot be modified without Director sign-off.",
    category: "operations",
  },
];

export function generateForecastDatasets(): ForecastDataset[] {
  // 1. Bed demand forecast over 72 hours
  const bedPoints = [];
  for (let h = 0; h < 24; h += 2) {
    const confirmedDemand = 600 + h * 38;
    const assumedSurgeDemand = Math.floor(confirmedDemand * 0.12);
    bedPoints.push({
      timeLabel: `Day 2 ${String(h).padStart(2, "0")}:00`,
      hour: `${h}:00`,
      date: "2026-10-31",
      confirmedDemand,
      confirmedCapacity: 1450,
      assumedSurgeDemand,
      projectedTotalDemand: confirmedDemand + assumedSurgeDemand,
      assumedCapacityCeiling: 1450,
      isProjectedGap: confirmedDemand + assumedSurgeDemand > 1450,
    });
  }

  // 2. Meal demand forecast
  const mealPoints = [];
  const mealSlots = [
    { label: "D1 Dinner", time: "19:00", confirmed: 1800, surge: 180, cap: 2400 },
    { label: "D2 Breakfast", time: "08:00", confirmed: 1650, surge: 150, cap: 2400 },
    { label: "D2 Lunch", time: "13:00", confirmed: 2200, surge: 250, cap: 2400 },
    { label: "D2 High Tea", time: "16:30", confirmed: 1100, surge: 120, cap: 2400 },
    { label: "D2 Dinner", time: "20:00", confirmed: 2350, surge: 280, cap: 2400 },
    { label: "D3 Breakfast", time: "08:00", confirmed: 1700, surge: 140, cap: 2400 },
    { label: "D3 Lunch", time: "13:00", confirmed: 2150, surge: 200, cap: 2400 },
  ];

  for (const s of mealSlots) {
    mealPoints.push({
      timeLabel: s.label,
      hour: s.time,
      date: "2026-10-31",
      confirmedDemand: s.confirmed,
      confirmedCapacity: s.cap,
      assumedSurgeDemand: s.surge,
      projectedTotalDemand: s.confirmed + s.surge,
      assumedCapacityCeiling: s.cap,
      isProjectedGap: s.confirmed + s.surge > s.cap,
    });
  }

  // 3. Shuttle demand forecast
  const shuttlePoints = [];
  const hoursList = [8, 11, 14, 17, 20, 23, 2];
  for (const h of hoursList) {
    const confirmedDemand = h >= 20 || h <= 2 ? 58 : 22;
    const assumedSurgeDemand = h >= 20 || h <= 2 ? 14 : 4;
    shuttlePoints.push({
      timeLabel: `${String(h).padStart(2, "0")}:00`,
      hour: `${h}:00`,
      date: "2026-10-31",
      confirmedDemand,
      confirmedCapacity: 48,
      assumedSurgeDemand,
      projectedTotalDemand: confirmedDemand + assumedSurgeDemand,
      assumedCapacityCeiling: 48,
      isProjectedGap: confirmedDemand + assumedSurgeDemand > 48,
    });
  }

  return [
    {
      domain: "accommodation",
      title: "Bed Occupancy & Arrival Demand Projection",
      description: "Confirmed check-ins (solid) vs heuristic late-arrival surge (dashed) against 1,450 bed ceiling.",
      unit: "Beds",
      points: bedPoints,
      relatedAssumptionKeys: ["cleaning_buffer_minutes", "minor_age_threshold"],
    },
    {
      domain: "food",
      title: "Meal Consumption Demand vs Preparation Ceiling",
      description: "Confirmed meal tokens (solid) vs 10% heuristic walk-in buffer (dashed) vs 2,400 vendor preparation limit.",
      unit: "Meal Tokens",
      points: mealPoints,
      relatedAssumptionKeys: ["walkin_meal_buffer_pct"],
    },
    {
      domain: "transport",
      title: "Shuttle Transit Demand vs Confirmed Fleet Capacity",
      description: "Confirmed passenger bookings (solid) vs night return surge (dashed) against 48-seat fleet loop capacity.",
      unit: "Seats",
      points: shuttlePoints,
      relatedAssumptionKeys: ["shuttle_capacity_seats"],
    },
  ];
}

export let mockForecastDatasets = generateForecastDatasets();

// ============================================================================
// 5. DECISION LOG MOCK DATA
// ============================================================================

export let mockDecisions: DecisionCardItem[] = [
  {
    id: "DEC-2026-001",
    module: "accommodation",
    decisionType: "PLAN_APPROVAL",
    title: "Approve Plan A: Hostel 3 Emergency Evacuation to Lakeview",
    summary: "Reallocated 85 displaced participants to Lakeview Resort and Campus Guest House preserving contingent cohesion.",
    why: "Preserving contingent integrity for IIT Bombay (C05) and BITS Pilani (C12) was prioritized over travel distance, invoking the first ladder rung.",
    hardConstraintsSatisfied: [
      "Gender-separated corridors enforced in Lakeview Wings A & B",
      "Zero unplaced minor participants without adult escort",
    ],
    softConstraintsRelaxed: [
      {
        constraint: "Proximity ladder: Campus vs External",
        rationale: "Campus beds exhausted; relaxed soft proximity to keep contingents intact.",
        ladderPriority: 3,
      },
    ],
    alternativesRejected: [
      {
        option: "Plan B: Cost-First Dispersal across 4 separate budget lodges",
        why: "Fragmented teams across 12km radius, introducing severe presentation forfeit risks.",
      },
      {
        option: "Plan C: Gymnasium Floor Sleeping Mats",
        why: "Violated dignity and hygiene standards; inadequate locker security.",
      },
    ],
    costImpactInr: 42500,
    peopleAffected: 85,
    approverName: "Dr. Devashish Roy",
    approverRole: "FESTIVAL_DIRECTOR",
    createdAt: "2026-10-31T07:15:00Z",
    overrideId: "OVR-2026-004",
    changeSetId: "cs_e2e_committed_01",
    status: "RECORDED",
  },
  {
    id: "DEC-2026-002",
    module: "vendors",
    decisionType: "EMERGENCY_REALLOCATION",
    title: "Emergency Voucher Transfer to Annapurna Caterers (VND01)",
    summary: "Diverted 220 Jain & Vegan lunch meal tokens from suspended Spice Kitchen to Annapurna.",
    why: "Health inspector suspended VND04 at 10:15 due to refrigeration temperature breach. Zero meal deficit requirement invoked under section 4.1.",
    hardConstraintsSatisfied: [
      "Strict separation of Jain / Pure-Vegetarian preparation utensils",
      "Vendor holds active verified FSSAI license",
    ],
    softConstraintsRelaxed: [
      {
        constraint: "Vendor budget pre-authorization protocol",
        rationale: "Emergency food clause invoked to prevent participant meal deficit within 90 minutes.",
        ladderPriority: 2,
      },
    ],
    alternativesRejected: [
      {
        option: "Issue Cash Food Allowances",
        why: "Participants cannot leave campus during competition hours to source Jain food.",
      },
    ],
    costImpactInr: 35000,
    peopleAffected: 220,
    approverName: "Kavita Rao",
    approverRole: "FOOD_OPS_MANAGER",
    createdAt: "2026-10-31T10:30:00Z",
    changeSetId: "cs_food_realloc_02",
    status: "RECORDED",
  },
  {
    id: "DEC-2026-003",
    module: "schedule",
    decisionType: "SESSION_RESCHEDULE",
    title: "Delay National Case Competition Round 2 by 45 Minutes",
    summary: "Rescheduled Semifinal Heat B in Seminar Hall 1 to prevent forfeiture by traveling contingents.",
    why: "Traffic delay on NH-52 held up 3 university contingents. Pushing round start preserved competitive fairness.",
    hardConstraintsSatisfied: [
      "Zero venue double-booking with Stage 2 cultural rehearsal",
      "Judge quorum maintained (minimum 3 panel judges present)",
    ],
    softConstraintsRelaxed: [
      {
        constraint: "Teardown buffer minutes (reduced from 30 to 15m)",
        rationale: "Stage crew cleared fast-turnover protocol.",
        ladderPriority: 2,
      },
    ],
    alternativesRejected: [
      {
        option: "Automatic Disqualification of Delayed Teams",
        why: "Unsportsmanlike; teams notified transit control well before departure.",
      },
    ],
    costImpactInr: 0,
    peopleAffected: 42,
    approverName: "Rohan Verma",
    approverRole: "EVENT_LEAD",
    createdAt: "2026-10-31T11:45:00Z",
    status: "RECORDED",
  },
];

// ============================================================================
// 6. UNKNOWNS BURN-DOWN ENHANCED DATA
// ============================================================================

export let mockEnhancedUnknownsQueue: UnknownQueueItem[] = [
  {
    field: "accommodation_requested",
    entity_type: "participant",
    count: 418,
    criticality: 4,
    score: 1672,
    owner: "ACCOMMODATION_LEAD",
    impact_text: "Beds cannot be definitively blocked in Plan A/B without confirmed housing requirement.",
    computed_gain: "+418 beds de-risked; unlocks definitive bed blocking in Plan A/B",
    method_label: "DIRECT_LEADER_SMS",
    sample_entity_ids: ["P0012", "P0045", "P0104"],
  },
  {
    field: "gender",
    entity_type: "participant",
    count: 417,
    criticality: 4,
    score: 1668,
    owner: "ACCOMMODATION_LEAD",
    impact_text: "Room allocation cannot enforce campus gender segregation safety constraints.",
    computed_gain: "+417 participants placed without violating gender corridor buffers",
    method_label: "ARRIVAL_KIOSK",
    sample_entity_ids: ["P0003", "P0019", "P0212"],
  },
  {
    field: "diet",
    entity_type: "participant",
    count: 394,
    criticality: 3,
    score: 1182,
    owner: "FOOD_OPS_MANAGER",
    impact_text: "Catering procurement buffers risk meal shortages or food waste during banquets.",
    computed_gain: "+394 dietary clearances; eliminates 220 Jain meal deficit risks",
    method_label: "WHATSAPP_LINK",
    sample_entity_ids: ["P0001", "P0005", "P0102"],
  },
  {
    field: "guardian_consent",
    entity_type: "participant",
    count: 14,
    criticality: 4,
    score: 56,
    owner: "FESTIVAL_DIRECTOR",
    impact_text: "Minors under 18 cannot be checked into external Lakeview Resort without parental affidavit.",
    computed_gain: "+14 minor safety approvals unlocked for external resort lodging",
    method_label: "CALL_DESK",
    sample_entity_ids: ["P0482", "P0921"],
  },
];

export let mockWhyNotExplanations: Record<string, WhyNotParticipantExplanation> = {
  P0102: {
    participantId: "P0102",
    name: "Aarav Sharma",
    contingentId: "C05",
    contingentName: "IIT Bombay",
    status: "EXPECTED",
    isUnplaced: true,
    blockingReasons: [
      {
        field: "accommodation_requested",
        currentValue: "UNKNOWN",
        ruleName: "Housing Requirement Check",
        explanation: "System cannot assign a bed until housing requirement is affirmatively confirmed (YES/NO). A blank never means NO or YES.",
        fixAction: "Send 1-click confirmation link to contingent leader.",
      },
      {
        field: "gender",
        currentValue: "UNKNOWN",
        ruleName: "Gender-Separated Corridor Buffer",
        explanation: "Hard constraint prohibits assigning unverified gender into gender-segregated Hostels 1 & 2 corridors.",
        fixAction: "Record gender via Arrival Kiosk or Leader confirmation.",
      },
    ],
    availableOptions: [
      "Confirm gender & accommodation via Leader WhatsApp link",
      "Assign provisional holding bed in Guest House Wing B under Director override",
    ],
  },
  unplaced_summary: {
    participantId: "AGGREGATE_UNPLACED",
    name: "85 Unplaced Participants Aggregate",
    contingentId: "ALL",
    contingentName: "Multiple Contingents",
    status: "UNPLACED",
    isUnplaced: true,
    blockingReasons: [
      {
        field: "accommodation_requested",
        currentValue: "48 UNKNOWN records",
        ruleName: "Missing housing preference",
        explanation: "48 of 85 unplaced participants have UNKNOWN accommodation_requested status.",
        fixAction: "Trigger bulk Leader SMS confirmation wave.",
      },
      {
        field: "gender",
        currentValue: "37 UNKNOWN records",
        ruleName: "Corridor segregation safety barrier",
        explanation: "37 unplaced records lack confirmed gender, blocking room placement in Hostels 1, 2 and 3.",
        fixAction: "Direct desk verification during check-in.",
      },
    ],
    availableOptions: [
      "Run Unknowns Burn-down wave",
      "Activate Plan A Lakeview Contingency Beds",
    ],
  },
};

// ============================================================================
// MSW HANDLERS DEFINITION
// ============================================================================

export const insightHandlers = [
  // 1. Dashboard Metrics
  http.get("*/api/v1/dashboard/metrics", ({ request }) => {
    const url = new URL(request.url);
    const role = url.searchParams.get("role") || "DIRECTOR";

    // Role-filtered responses
    if (role === "VOLUNTEER") {
      return HttpResponse.json({
        data: {
          ...mockDashboardMetrics,
          open_incidents: 0,
          pending_approvals: 0,
          active_overrides: 0,
        },
        meta: { role: "VOLUNTEER", filtered: true },
      });
    }

    return HttpResponse.json({
      data: mockDashboardMetrics,
      meta: { role, calculated_at: mockDashboardMetrics.calculated_at },
    });
  }),

  // 2. Attention Queue (Ranked strictly by Severity x Urgency x max(people, 1))
  http.get("*/api/v1/dashboard/attention", ({ request }) => {
    const url = new URL(request.url);
    const moduleFilter = url.searchParams.get("module");
    const minSeverity = url.searchParams.get("min_severity");

    let items = [...mockAttentionQueue];

    if (moduleFilter) {
      items = items.filter((i) => i.module === moduleFilter);
    }
    if (minSeverity) {
      items = items.filter((i) => i.severityLevel >= Number(minSeverity));
    }

    // Sort descending by attention score
    items.sort((a, b) => computeAttentionScore(b) - computeAttentionScore(a));

    return HttpResponse.json({
      data: {
        items,
        total: items.length,
      },
    });
  }),

  // 3. Snooze / Acknowledge Attention Item
  http.post("*/api/v1/dashboard/attention/:id/snooze", async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as any;
    const { reason, minutes, acknowledged } = body;

    const item = mockAttentionQueue.find((i) => i.id === id);
    if (item) {
      if (acknowledged) {
        item.acknowledgedBy = "Dr. Devashish Roy";
        item.acknowledgedAt = new Date().toISOString();
      } else {
        item.isSnoozed = true;
        item.snoozeReason = reason || "Operational review underway";
        item.snoozedUntil = new Date(Date.now() + (minutes || 60) * 60000).toISOString();
      }
    }

    return HttpResponse.json({
      data: {
        id,
        status: acknowledged ? "ACKNOWLEDGED" : "SNOOZED",
        reason,
      },
    });
  }),

  // 4. Risk Heatmap (Severity x Time Window)
  http.get("*/api/v1/dashboard/heatmap", () => {
    const timeWindows: Array<HeatmapCell["timeWindow"]> = [
      "<=1h",
      "1-4h",
      "4-12h",
      "12-24h",
      ">24h",
    ];
    const severities: Array<HeatmapCell["severity"]> = [
      "CRITICAL",
      "HIGH",
      "MEDIUM",
      "LOW",
    ];

    const cells: HeatmapCell[] = [];

    severities.forEach((sev, sIdx) => {
      timeWindows.forEach((tw, tIdx) => {
        const matching = mockAttentionQueue.filter((item) => {
          const sevMatch = item.severity === sev;
          let twMatch = false;
          if (tw === "<=1h") twMatch = item.hoursToImpact <= 1;
          else if (tw === "1-4h") twMatch = item.hoursToImpact > 1 && item.hoursToImpact <= 4;
          else if (tw === "4-12h") twMatch = item.hoursToImpact > 4 && item.hoursToImpact <= 12;
          else if (tw === "12-24h") twMatch = item.hoursToImpact > 12 && item.hoursToImpact <= 24;
          else twMatch = item.hoursToImpact > 24;

          return sevMatch && twMatch;
        });

        const totalPeople = matching.reduce((acc, cur) => acc + cur.peopleAffected, 0);
        const avgUncertainty =
          matching.length > 0
            ? matching.reduce((acc, cur) => acc + cur.uncertainty, 0) / matching.length
            : 0;

        cells.push({
          severity: sev,
          severityLevel: 4 - sIdx,
          timeWindow: tw,
          timeWindowIndex: tIdx,
          itemCount: matching.length,
          totalPeopleAffected: totalPeople,
          avgUncertainty,
          items: matching,
        });
      });
    });

    return HttpResponse.json({
      data: {
        cells,
        totalRisks: mockAttentionQueue.length,
      },
    });
  }),

  // 5. Scenarios Simulator
  http.get("*/api/v1/scenarios", () => {
    return HttpResponse.json({
      data: {
        items: mockScenarios,
        catalog: mockDisruptionCatalog,
        total: mockScenarios.length,
      },
    });
  }),

  http.post("*/api/v1/scenarios", async ({ request }) => {
    const body = (await request.json()) as any;
    const newScen: SimulationScenario = {
      id: `scen_${Date.now()}`,
      name: body.name || "Custom Fork Scenario",
      description: body.description || "Sandbox fork of live database",
      createdAt: new Date().toISOString(),
      actorId: "usr_dir_001",
      actorName: "Dr. Devashish Roy",
      status: "ACTIVE",
      isStale: false,
      liveMutationsSinceFork: 0,
      lastSyncedAt: new Date().toISOString(),
      disruptionsApplied: [],
      metricsComparison: [
        {
          key: "unplaced_participants",
          label: "Unplaced Participants",
          liveValue: 85,
          scenarioValue: 85,
          delta: 0,
          impactStatus: "NEUTRAL",
        },
        {
          key: "uncovered_meals",
          label: "Meal Shortages",
          liveValue: 220,
          scenarioValue: 220,
          delta: 0,
          impactStatus: "NEUTRAL",
        },
        {
          key: "cost_delta_inr",
          label: "Cost Delta",
          liveValue: 0,
          scenarioValue: 0,
          delta: "₹0",
          impactStatus: "NEUTRAL",
        },
      ],
      candidatePlans: [],
    };

    mockScenarios.unshift(newScen);
    return HttpResponse.json({ data: newScen }, { status: 201 });
  }),

  http.get("*/api/v1/scenarios/:id", ({ params }) => {
    const scen = mockScenarios.find((s) => s.id === params.id) || mockScenarios[0];
    return HttpResponse.json({ data: scen });
  }),

  http.get("*/api/v1/scenarios/:id/compare", ({ params }) => {
    const scen = mockScenarios.find((s) => s.id === params.id) || mockScenarios[0];
    return HttpResponse.json({
      data: {
        scenario_id: scen.id,
        is_stale: scen.isStale,
        live_mutations_since_fork: scen.liveMutationsSinceFork,
        metrics: scen.metricsComparison,
        plans: scen.candidatePlans,
      },
    });
  }),

  http.post("*/api/v1/scenarios/:id/simulate-incident", async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as any;
    const scen = mockScenarios.find((s) => s.id === id);

    if (scen) {
      scen.disruptionsApplied.push({
        id: `da_${Date.now()}`,
        disruptionId: body.incident_type || "hostel_closure",
        targetId: body.target_id || "HOSTEL-03",
        appliedAt: new Date().toISOString(),
        summary: body.details || "Injected disruption into sandbox simulation.",
      });

      // Update scenario comparison metrics
      if (body.incident_type === "hostel_closure") {
        scen.metricsComparison = [
          {
            key: "unplaced_participants",
            label: "Unplaced Participants",
            liveValue: 85,
            scenarioValue: 0,
            delta: -85,
            impactStatus: "IMPROVED",
          },
          {
            key: "cost_delta_inr",
            label: "Additional Cost",
            liveValue: 0,
            scenarioValue: 42500,
            delta: "+₹42,500",
            impactStatus: "DEGRADED",
          },
        ];
        scen.candidatePlans = [
          {
            id: "plan_a",
            name: "Plan A: Cohesion-First Evacuation",
            strategy: "Keep contingents intact at Lakeview Resort and Campus Guest House.",
            peopleMoved: 85,
            costDeltaInr: 42500,
            scheduleChanges: 1,
            constraintsRelaxed: ["Proximity ladder (Soft)"],
            isRecommended: true,
          },
        ];
      }
    }

    return HttpResponse.json({
      data: {
        scenario: scen,
        message: "Disruption applied to sandbox.",
      },
    });
  }),

  http.post("*/api/v1/scenarios/:id/commit", async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as any;
    const scen = mockScenarios.find((s) => s.id === id);

    if (scen) {
      scen.status = "COMMITTED";
    }

    return HttpResponse.json({
      data: {
        scenario_id: id,
        status: "COMMITTED",
        reason: body.reason,
        change_set_id: `cs_scen_${Date.now()}`,
      },
    });
  }),

  http.post("*/api/v1/scenarios/:id/discard", ({ params }) => {
    const { id } = params;
    const idx = mockScenarios.findIndex((s) => s.id === id);
    if (idx !== -1) {
      mockScenarios[idx].status = "DISCARDED";
    }

    return HttpResponse.json({
      data: {
        scenario_id: id,
        status: "DISCARDED",
        message: "Sandbox storage deleted. Live production untouched.",
      },
    });
  }),

  // 6. Fest Pre-Mortem Endpoints
  http.get("*/api/v1/premortem/timeline", () => {
    return HttpResponse.json({
      data: {
        hours: mockPremortemHours,
        totalHours: mockPremortemHours.length,
        festStartDate: "2026-10-30T06:00:00Z",
        festEndDate: "2026-11-01T23:00:00Z",
      },
    });
  }),

  http.get("*/api/v1/premortem/spof", () => {
    return HttpResponse.json({
      data: {
        items: mockSpofList,
        total: mockSpofList.length,
      },
    });
  }),

  http.get("*/api/v1/premortem/preventive", () => {
    return HttpResponse.json({
      data: {
        items: mockPreventiveActions,
        total: mockPreventiveActions.length,
      },
    });
  }),

  http.post("*/api/v1/premortem/preventive/:id/execute", ({ params }) => {
    const { id } = params;
    const item = mockPreventiveActions.find((p) => p.id === id);
    if (item) {
      item.status = "EXECUTED";
    }
    return HttpResponse.json({
      data: { id, status: "EXECUTED" },
    });
  }),

  http.get("*/api/v1/premortem/resilience", () => {
    return HttpResponse.json({
      data: mockResilienceReport,
    });
  }),

  // 7. Forecasting & Assumptions
  http.get("*/api/v1/forecasting/datasets", () => {
    return HttpResponse.json({
      data: {
        datasets: mockForecastDatasets,
      },
    });
  }),

  http.get("*/api/v1/assumptions", () => {
    return HttpResponse.json({
      data: {
        items: mockAssumptions,
        total: mockAssumptions.length,
      },
    });
  }),

  http.patch("*/api/v1/assumptions/:key", async ({ params, request }) => {
    const { key } = params;
    const body = (await request.json()) as any;
    const item = mockAssumptions.find((a) => a.key === key);
    if (item) {
      item.value = body.value;
      if (body.reason) item.reason = body.reason;
    }
    return HttpResponse.json({
      data: item,
      message: "Assumption updated and forecasts recalculated.",
    });
  }),

  // 8. Decision Log
  http.get("*/api/v1/decisions", ({ request }) => {
    const url = new URL(request.url);
    const moduleFilter = url.searchParams.get("module");
    const approverFilter = url.searchParams.get("approver");

    let items = [...mockDecisions];
    if (moduleFilter) items = items.filter((d) => d.module === moduleFilter);
    if (approverFilter) items = items.filter((d) => d.approverRole === approverFilter || d.approverName.includes(approverFilter));

    return HttpResponse.json({
      data: {
        items,
        total: items.length,
      },
    });
  }),

  http.get("*/api/v1/decisions/:id/why", ({ params }) => {
    const { id } = params;
    const card = mockDecisions.find((d) => d.id === id) || mockDecisions[0];

    return HttpResponse.json({
      data: {
        id: card.id,
        title: card.title,
        summary: card.summary,
        why: card.why,
        hard_constraints_satisfied: card.hardConstraintsSatisfied,
        soft_constraints_relaxed: card.softConstraintsRelaxed,
        alternatives_rejected: card.alternativesRejected,
        cost_impact_inr: card.costImpactInr,
        people_affected: card.peopleAffected,
        approver_name: card.approverName,
        approver_role: card.approverRole,
        created_at: card.createdAt,
        override_id: card.overrideId,
      },
    });
  }),

  // 9. Unknowns Burn-down Enhanced
  http.get("*/api/v1/unknowns/why-not", ({ request }) => {
    const url = new URL(request.url);
    const pid = url.searchParams.get("participant_id") || "unplaced_summary";
    const explanation = mockWhyNotExplanations[pid] || mockWhyNotExplanations["unplaced_summary"];

    return HttpResponse.json({
      data: explanation,
    });
  }),

  http.get("*/api/v1/unknowns/queue-enhanced", () => {
    return HttpResponse.json({
      data: {
        items: mockEnhancedUnknownsQueue,
        total: mockEnhancedUnknownsQueue.length,
      },
    });
  }),
];
