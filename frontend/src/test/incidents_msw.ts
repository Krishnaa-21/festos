import { http, HttpResponse } from "msw";
import { IncidentRecord, ScenarioId, DryRunImpact } from "../features/incidents/types";
import { ImpactReportData } from "../features/impact/types";
import {
  StaffMember,
  ShiftAssignment,
  CoverageHourlySlot,
  HandoverNoteRecord,
  ReplacementCandidate,
} from "../features/staff/types";
import {
  TransportAssumptions,
  ShuttlePlanSlot,
  NightSafetyParticipant,
  GuardianQueueEntry,
  SafetyCoverageSummary,
  TransportAlert,
} from "../features/transport/types";
import { NotificationDraft, DeliveryLogEntry } from "../features/notifications/types";

// In-memory state for mocks
export let mockIncidents: IncidentRecord[] = [
  {
    id: "INC-2026-001",
    scenarioId: "hostel_closure",
    title: "Hostel 3 Emergency Plumbing Failure (85 Beds)",
    severity: "CRITICAL",
    status: "ACTIVE",
    createdAt: "2026-10-31T06:30:00Z",
    peopleAffected: 85,
    approvedPlan: "Plan A: Cohesion-First Evacuation",
    approvedBy: "Devashish Roy (Festival Director)",
    approvalReason: "Plumbing main line burst in Hostel 3 basement flooding electrical shafts.",
    downstreamUpdates: [
      {
        id: "ds_01",
        domain: "Accommodation",
        label: "Reallocate 85 participants to Lakeview Resort & Campus Guest House",
        status: "UPDATED",
        details: "45 beds blocked at Lakeview Resort, 40 beds at Campus Guest House Wing B",
        entityRoute: "/accommodation",
      },
      {
        id: "ds_02",
        domain: "Transport",
        label: "Schedule 7 Express Shuttle Runs between Lakeview and Campus Hub",
        status: "UPDATED",
        details: "Assigned Vehicles V1 and V3 for hourly loops starting 07:00",
        entityRoute: "/transport",
      },
      {
        id: "ds_03",
        domain: "Catering",
        label: "Shift breakfast/dinner distribution to West Wing Dining Annex",
        status: "PENDING",
        details: "85 meal tokens redirected from Hostel 3 mess hall to Annapurna West",
        entityRoute: "/food",
      },
      {
        id: "ds_04",
        domain: "Schedule",
        label: "Delay C05 Prelim Presentation slot by 45 minutes",
        status: "VERIFIED",
        details: "Heats adjusted to avoid forfeiture during luggage relocation",
        entityRoute: "/events",
        verifiedAt: "2026-10-31T07:15:00Z",
        verifiedBy: "Rohan Verma (Event Lead)",
      },
      {
        id: "ds_05",
        domain: "Staff",
        label: "Deploy 4 Night Escorts for Lakeview Transit Hub",
        status: "UPDATED",
        details: "Volunteers Pooja Sharma and Ankit Mehra assigned to shuttle boarding",
        entityRoute: "/staff",
      },
    ],
    beforeMetrics: {
      unplacedParticipants: 85,
      mealShortages: 85,
      delayedEvents: 2,
      transportDeficit: 38,
      extraCostInr: 0,
    },
    afterMetrics: {
      unplacedParticipants: 0,
      mealShortages: 0,
      delayedEvents: 0,
      transportDeficit: 0,
      extraCostInr: 42500,
    },
  },
  {
    id: "INC-2026-002",
    scenarioId: "vendor_shutdown",
    title: "Spice Kitchen (VND04) Emergency Health Violation Shutdown",
    severity: "HIGH",
    status: "INVESTIGATING",
    createdAt: "2026-10-31T09:45:00Z",
    peopleAffected: 220,
    downstreamUpdates: [
      {
        id: "ds_06",
        domain: "Catering",
        label: "Transfer 220 Jain & Vegan lunch tokens to Annapurna Caterers (VND01)",
        status: "PENDING",
        details: "VND01 verified with active FSSAI certificate to absorb capacity",
        entityRoute: "/food",
      },
      {
        id: "ds_07",
        domain: "Finance",
        label: "Hold escrow payout for VND04 and issue ₹35,000 emergency PO",
        status: "PENDING",
        details: "Contractual penalty clause invoked under section 8.2",
        entityRoute: "/finance",
      },
    ],
    beforeMetrics: {
      unplacedParticipants: 0,
      mealShortages: 220,
      delayedEvents: 0,
      transportDeficit: 0,
      extraCostInr: 0,
    },
    afterMetrics: {
      unplacedParticipants: 0,
      mealShortages: 0,
      delayedEvents: 0,
      transportDeficit: 0,
      extraCostInr: 35000,
    },
  },
];

export let mockTransportAssumptions: TransportAssumptions = {
  shuttle_capacity_seats: 12,
  shuttle_vehicle_count: 3,
  shuttle_travel_min: 25,
  transport_hours: "06:00-22:00",
  cleaning_buffer_minutes: 180,
  late_night_start: "22:00",
  late_night_end: "06:00",
  minor_age_threshold: 18,
};

export let mockStaffList: StaffMember[] = [
  {
    id: "STF01",
    name: "Aarav Sharma",
    email: "aarav.sharma@festos.internal",
    role: "LEAD",
    skills: ["Incident Commander", "Accommodation", "First Aid"],
    totalHoursWorked: 8,
    consecutiveHours: 4,
    isOverloaded: false,
    hasConflict: false,
    assignedVenueId: "V01",
    phone: "+91 98765 43210",
  },
  {
    id: "STF02",
    name: "Pooja Sharma",
    email: "pooja.s@festos.internal",
    role: "VOLUNTEER",
    skills: ["Registration Desk", "Crowd Control", "First Aid"],
    totalHoursWorked: 11,
    consecutiveHours: 11,
    isOverloaded: true,
    hasConflict: false,
    assignedVenueId: "V04",
    phone: "+91 98765 43211",
  },
  {
    id: "STF03",
    name: "Rohan Verma",
    email: "rohan.v@festos.internal",
    role: "COORDINATOR",
    skills: ["Audio Visual", "Stage Management"],
    totalHoursWorked: 6,
    consecutiveHours: 3,
    isOverloaded: false,
    hasConflict: true,
    assignedVenueId: "V02",
    phone: "+91 98765 43212",
  },
  {
    id: "STF04",
    name: "Kavita Rao",
    email: "kavita.r@festos.internal",
    role: "VOLUNTEER",
    skills: ["Merchandise Desk", "Crowd Control"],
    totalHoursWorked: 5,
    consecutiveHours: 2,
    isOverloaded: false,
    hasConflict: false,
    assignedVenueId: "V05",
    phone: "+91 98765 43213",
  },
  {
    id: "STF05",
    name: "Ankit Mehra",
    email: "ankit.m@festos.internal",
    role: "SECURITY",
    skills: ["Night Patrol", "Escort Escort", "Emergency Evacuation"],
    totalHoursWorked: 7,
    consecutiveHours: 3,
    isOverloaded: false,
    hasConflict: false,
    assignedVenueId: "V09",
    phone: "+91 98765 43214",
  },
  {
    id: "STF06",
    name: "Sunita Reddy",
    email: "sunita.r@festos.internal",
    role: "VOLUNTEER",
    skills: ["First Aid", "Catering Support"],
    totalHoursWorked: 4,
    consecutiveHours: 2,
    isOverloaded: false,
    hasConflict: false,
    assignedVenueId: "V03",
    phone: "+91 98765 43215",
  },
];

export let mockShifts: ShiftAssignment[] = [
  {
    id: "SH-08-AUD",
    staffId: "STF01",
    staffName: "Aarav Sharma",
    role: "LEAD",
    venueId: "V01",
    venueName: "Main Auditorium",
    hour: "08:00",
    date: "2026-10-31",
    status: "CONFIRMED",
    isOverloaded: false,
    isOverlapping: false,
    handoverCompleted: true,
    handoverNotes: "Stage checks cleared. PA system calibrated.",
  },
  {
    id: "SH-10-AUD",
    staffId: "STF03",
    staffName: "Rohan Verma",
    role: "COORDINATOR",
    venueId: "V01",
    venueName: "Main Auditorium",
    hour: "10:00",
    date: "2026-10-31",
    status: "IN_PROGRESS",
    isOverloaded: false,
    isOverlapping: true,
    handoverCompleted: true,
    handoverNotes: "Keynote presentation microphones switched to channel 4.",
  },
  {
    id: "SH-10-DIN",
    staffId: "STF03",
    staffName: "Rohan Verma",
    role: "COORDINATOR",
    venueId: "V03",
    venueName: "Central Dining Hall",
    hour: "10:00",
    date: "2026-10-31",
    status: "IN_PROGRESS",
    isOverloaded: false,
    isOverlapping: true,
    handoverCompleted: false,
  },
  {
    id: "SH-12-REG",
    staffId: "STF02",
    staffName: "Pooja Sharma",
    role: "VOLUNTEER",
    venueId: "V04",
    venueName: "Registration Concourse",
    hour: "12:00",
    date: "2026-10-31",
    status: "IN_PROGRESS",
    isOverloaded: true,
    isOverlapping: false,
    handoverCompleted: false,
  },
  {
    id: "SH-14-REG",
    staffId: "STF02",
    staffName: "Pooja Sharma",
    role: "VOLUNTEER",
    venueId: "V04",
    venueName: "Registration Concourse",
    hour: "14:00",
    date: "2026-10-31",
    status: "ASSIGNED",
    isOverloaded: true,
    isOverlapping: false,
    handoverCompleted: false,
  },
  {
    id: "SH-16-HUB",
    staffId: "STF05",
    staffName: "Ankit Mehra",
    role: "SECURITY",
    venueId: "V09",
    venueName: "Transport Hub",
    hour: "16:00",
    date: "2026-10-31",
    status: "ASSIGNED",
    isOverloaded: false,
    isOverlapping: false,
    handoverCompleted: true,
    handoverNotes: "Shuttles 1 and 2 on schedule.",
  },
];

export let mockHandovers: HandoverNoteRecord[] = [
  {
    id: "HO-01",
    venueId: "V01",
    venueName: "Main Auditorium",
    hour: "08:00",
    outgoingStaffName: "Night Shift Lead",
    incomingStaffName: "Aarav Sharma",
    notes: "Fire exits inspected. AC unit in backstage green room serviced.",
    timestamp: "2026-10-31T08:00:00Z",
    isMissing: false,
    acknowledgedByIncoming: true,
  },
  {
    id: "HO-02",
    venueId: "V04",
    venueName: "Registration Concourse",
    hour: "14:00",
    outgoingStaffName: "Pooja Sharma",
    incomingStaffName: "Pending Replacement",
    notes: "",
    timestamp: "2026-10-31T14:00:00Z",
    isMissing: true,
    acknowledgedByIncoming: false,
  },
];

export let mockTransportAlerts: TransportAlert[] = [
  {
    id: "ALT-01",
    severity: "CRITICAL",
    message: "14 participants are scheduled to leave Lakeview at midnight, but no verified shuttle is assigned.",
    suggestedActionLabel: "Assign Express Shuttle Run",
    actionPayload: { propertyId: "prop_01", hour: "00:00", vehicle: "V1" },
    isResolved: false,
  },
  {
    id: "ALT-02",
    severity: "HIGH",
    message: "3 minors arriving from C12 at 23:15 have unconfirmed external property guardian waivers.",
    suggestedActionLabel: "Review Guardian Queue",
    actionPayload: { contingentId: "C12", filter: "minors" },
    isResolved: false,
  },
  {
    id: "ALT-03",
    severity: "MEDIUM",
    message: "Vehicle 2 driver shift expires at 21:00 with 45 passengers pending transfer to Silver Oak.",
    suggestedActionLabel: "Extend Driver Shift",
    actionPayload: { vehicleId: "V2", extensionHours: 2 },
    isResolved: false,
  },
];

export let mockGuardianQueue: GuardianQueueEntry[] = [
  {
    id: "GQ-01",
    participantId: "P0482",
    name: "Isha Malhotra",
    age: 17,
    contingentId: "C12",
    contingentName: "BITS Pilani",
    externalProperty: "Lakeview Resort",
    stayDuration: "3 nights",
    guardianName: "Sunil Malhotra",
    guardianContact: "+91 98111 22334",
    isMasked: false,
    status: "PENDING_REVIEW",
    escortAssigned: "Ankit Mehra",
  },
  {
    id: "GQ-02",
    participantId: "P0921",
    name: "Dev Patel",
    age: 16,
    contingentId: "C18",
    contingentName: "NIT Trichy",
    externalProperty: "Green Palms",
    stayDuration: "2 nights",
    guardianName: "Meena Patel",
    guardianContact: "+91 98222 33445",
    isMasked: false,
    status: "PENDING_REVIEW",
  },
  {
    id: "GQ-03",
    participantId: "P1244",
    name: "Karan Johar",
    age: 17,
    contingentId: "C05",
    contingentName: "IIT Bombay",
    externalProperty: "Campus Guest House",
    stayDuration: "4 nights",
    guardianName: "Rajiv Johar",
    guardianContact: "+91 98333 44556",
    isMasked: false,
    status: "APPROVED",
    escortAssigned: "Pooja Sharma",
    reviewedBy: "Festival Director",
    reviewReason: "Valid parental affidavit received via college dean.",
  },
];

export let mockNightRoster: NightSafetyParticipant[] = [
  {
    id: "NR-01",
    participantId: "P0102",
    name: "Aarav Sharma",
    contingentId: "C05",
    contingentName: "IIT Bombay",
    origin: "Main Auditorium (V01)",
    destination: "Lakeview Resort",
    travelTime: "23:30",
    isMinor: false,
    assignedEscortId: "STF05",
    assignedEscortName: "Ankit Mehra",
    isVerified: true,
    verifiedAt: "2026-10-31T23:35:00Z",
    verifiedBy: "Security Lead",
  },
  {
    id: "NR-02",
    participantId: "P0482",
    name: "Isha Malhotra",
    contingentId: "C12",
    contingentName: "BITS Pilani",
    origin: "Dining Annex (V03)",
    destination: "Lakeview Resort",
    travelTime: "00:15",
    isMinor: true,
    assignedEscortId: "STF05",
    assignedEscortName: "Ankit Mehra",
    isVerified: false,
  },
  {
    id: "NR-03",
    participantId: "P0781",
    name: "Simran Kaur",
    contingentId: "C09",
    contingentName: "SRCC Delhi",
    origin: "Sports Complex (V02)",
    destination: "Campus Guest House",
    travelTime: "01:00",
    isMinor: false,
    assignedEscortId: "STF06",
    assignedEscortName: "Sunita Reddy",
    isVerified: false,
  },
];

export let mockNotificationDrafts: NotificationDraft[] = [
  {
    id: "ND-01",
    audience: "LEADERS",
    audienceLabel: "Contingent Leaders",
    recipientCount: 38,
    subject: "[URGENT] Schedule Adjustment Notice for Preliminary Heats",
    body: "Dear Contingent Leaders, due to a logistical delay affecting multiple transit corridors, afternoon preliminary rounds at Main Auditorium and Sports Complex are adjusted forward by 45 minutes. Please verify updated team slots in the FestOS participant portal.",
    priority: "URGENT",
    status: "DRAFT",
    triggerIncidentId: "INC-2026-001",
    triggerEventLabel: "Hostel 3 & Transit Corridor Realignment",
    createdAt: "2026-10-31T07:30:00Z",
  },
  {
    id: "ND-02",
    audience: "VOLUNTEERS",
    audienceLabel: "Staff & Volunteers",
    recipientCount: 48,
    subject: "Emergency Shift Support: Registration Desk & Transport Hub",
    body: "All off-duty volunteers in Zone 2: please report to the Central Registration Concourse and Transport Hub for crowd support during peak contingent arrival waves.",
    priority: "HIGH",
    status: "APPROVED",
    triggerIncidentId: "INC-2026-001",
    triggerEventLabel: "Volunteer Surge Allocation",
    createdAt: "2026-10-31T08:00:00Z",
    approvedBy: "Devashish Roy (Festival Director)",
  },
  {
    id: "ND-03",
    audience: "VENDORS",
    audienceLabel: "Food Vendors",
    recipientCount: 14,
    subject: "Capacity Reallocation Notice: Annapurna Caterers & Annex",
    body: "Attn Vendor Leads: Spice Kitchen (VND04) operations are paused. Annapurna Caterers (VND01) will absorb 220 Jain/Vegan lunch packs. Meal redemption counters at West Wing are active.",
    priority: "HIGH",
    status: "DRAFT",
    triggerIncidentId: "INC-2026-002",
    triggerEventLabel: "Vendor VND04 Hygiene Suspension",
    createdAt: "2026-10-31T10:00:00Z",
  },
  {
    id: "ND-04",
    audience: "COORDINATORS",
    audienceLabel: "Accommodation Coordinators",
    recipientCount: 12,
    subject: "Hostel 3 Evacuation: Room Reallocation Roster Complete",
    body: "Coordinators: 85 participants from Hostel 3 have been assigned to Lakeview Resort (45) and Campus Guest House (40). Key handover desks are operational at Hub Desk A.",
    priority: "URGENT",
    status: "SENT",
    triggerIncidentId: "INC-2026-001",
    triggerEventLabel: "Hostel 3 Structural Evacuation",
    createdAt: "2026-10-31T07:00:00Z",
    approvedBy: "Devashish Roy (Festival Director)",
    sentAt: "2026-10-31T07:10:00Z",
  },
  {
    id: "ND-05",
    audience: "ORGANISERS",
    audienceLabel: "Event Organisers",
    recipientCount: 31,
    subject: "Equipment Replacement: Main Stage Audio Rig Calibrated",
    body: "Organisers: Backup Yamaha 32-channel digital console has been transferred from Logistics Warehouse B to Main Auditorium. Soundcheck scheduled at 11:30.",
    priority: "NORMAL",
    status: "DRAFT",
    triggerEventLabel: "Equipment Recovery Drill",
    createdAt: "2026-10-31T09:00:00Z",
  },
];

export let mockDeliveryLog: DeliveryLogEntry[] = [
  {
    id: "DL-01",
    draftId: "ND-04",
    audience: "COORDINATORS",
    audienceLabel: "Accommodation Coordinators",
    recipientCount: 12,
    channel: "WHATSAPP_API",
    subject: "Hostel 3 Evacuation: Room Reallocation Roster Complete",
    bodyPreview: "Coordinators: 85 participants from Hostel 3 have been assigned to Lakeview Resort...",
    sentAt: "2026-10-31T07:10:00Z",
    deliveredCount: 12,
    acknowledgedCount: 11,
    status: "ACKNOWLEDGED",
  },
  {
    id: "DL-02",
    draftId: "ND-PREV-01",
    audience: "LEADERS",
    audienceLabel: "Contingent Leaders",
    recipientCount: 38,
    channel: "SMS_BROADCAST",
    subject: "Welcome to FestOS Aarohan 2026 - Central Helpdesk Active",
    bodyPreview: "Welcome Contingents. For assistance, visit Registration Concourse or dial internal extension 404.",
    sentAt: "2026-10-30T18:00:00Z",
    deliveredCount: 38,
    acknowledgedCount: 35,
    status: "DELIVERED",
  },
];

export const incidentHandlers = [
  // ==========================================
  // 1. INCIDENTS & DISRUPTION CONSOLE
  // ==========================================
  http.get("*/api/v1/incidents", () => {
    return HttpResponse.json({
      data: {
        items: mockIncidents,
        total: mockIncidents.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/incidents/concurrent-warning", () => {
    const activeIncidents = mockIncidents.filter((i) => i.status === "ACTIVE" || i.status === "INVESTIGATING");
    const hasConcurrent = activeIncidents.length >= 2;
    return HttpResponse.json({
      data: {
        has_concurrent_incidents: hasConcurrent,
        active_count: activeIncidents.length,
        message: hasConcurrent
          ? `Concurrent Active Disruptions Detected: ${activeIncidents.length} incidents in progress (${activeIncidents.map((i) => i.title).join("; ")}). Cross-resource contention warning.`
          : null,
        active_incident_ids: activeIncidents.map((i) => i.id),
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/incidents/dry-run", async ({ request }) => {
    const body = (await request.json()) as any;
    const scenarioId: ScenarioId = body.scenario_id || "hostel_closure";

    let dryRunData: DryRunImpact;
    if (scenarioId === "hostel_closure") {
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId: "hostel_closure",
        title: "Hostel 3 Structural / Plumbing Evacuation",
        severity: "CRITICAL",
        peopleAffected: 85,
        affectedEntities: {
          participants: 85,
          rooms: 28,
          events: 3,
          venues: 1,
          meals: 85,
          shuttles: 7,
          staff: 4,
        },
        keyRisks: [
          "85 participants stranded with no on-campus beds",
          "Potential conflict with C05 presentation schedule if check-in delayed",
          "Demand spike on Lakeview shuttle route exceeds confirmed fleet capacity by 14 seats",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Cohesion-First Evacuation",
            strategy: "Keep contingents intact by blocking contiguous blocks at Lakeview Resort and Campus Guest House.",
            isRecommended: true,
            peopleMoved: 85,
            scheduleChanges: 1,
            resourceMoves: 7,
            costDeltaInr: 42500,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Proximity ladder: Campus vs External",
                rationale: "Campus beds exhausted; relaxed soft proximity to preserve contingent cohesion.",
              },
            ],
            summary: "Preserves team unity for IIT Bombay & BITS Pilani. Extra transport loops arranged.",
          },
          {
            id: "plan_b",
            name: "Plan B: Cost-First Distribution",
            strategy: "Split participants into remaining scattered single beds across 4 external properties.",
            isRecommended: false,
            peopleMoved: 85,
            scheduleChanges: 4,
            resourceMoves: 12,
            costDeltaInr: 21000,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Contingent cohesion",
                rationale: "Contingents split across multiple lodges to maximize cheapest bed-rate utilization.",
              },
              {
                type: "SOFT",
                constraint: "Proximity ladder",
                rationale: "Travel times increase to 40+ minutes.",
              },
            ],
            summary: "Saves ₹21,500 but fragments contingents and increases schedule delays.",
          },
          {
            id: "plan_c",
            name: "Plan C: Balanced Fast Recovery",
            strategy: "Prioritize female and minor participants on-campus in Hostels 1 & 2; transfer senior males to Lakeview.",
            isRecommended: false,
            peopleMoved: 85,
            scheduleChanges: 2,
            resourceMoves: 5,
            costDeltaInr: 32000,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Gender-separated corridor buffer",
                rationale: "Repurposed Hostel 2 Wing C with dedicated security barrier.",
              },
            ],
            summary: "Zero minor travel at night; balanced cost delta.",
          },
        ],
        simulatedTimeDeltaMin: 45,
      };
    } else if (scenarioId === "vendor_shutdown") {
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId: "vendor_shutdown",
        title: "Vendor VND04 Emergency Hygiene Suspension",
        severity: "HIGH",
        peopleAffected: 220,
        affectedEntities: {
          participants: 220,
          rooms: 0,
          events: 0,
          venues: 1,
          meals: 220,
          shuttles: 0,
          staff: 2,
        },
        keyRisks: [
          "220 Jain & Vegan participants without lunch in 90 minutes",
          "Risk of food safety cross-contamination if stall remains open",
          "Dispute over vendor advance security deposit",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Express Reallocation to Annapurna (VND01)",
            strategy: "Divert all 220 special dietary tokens to Annapurna Caterers with emergency express prep.",
            isRecommended: true,
            peopleMoved: 0,
            scheduleChanges: 0,
            resourceMoves: 2,
            costDeltaInr: 35000,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Vendor budget pre-authorization",
                rationale: "Emergency food clause invoked to prevent participant meal disruption.",
              },
            ],
            summary: "Zero meal deficit; Annapurna holds verified FSSAI certification and has kitchen capacity.",
          },
          {
            id: "plan_b",
            name: "Plan B: External Catering Order from Indore Central",
            strategy: "Order boxed meals from certified external cloud kitchen with 45 min delivery.",
            isRecommended: false,
            peopleMoved: 0,
            scheduleChanges: 1,
            resourceMoves: 4,
            costDeltaInr: 58000,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "On-campus vendor exclusivity",
                rationale: "External food permitted under emergency protocol.",
              },
            ],
            summary: "Guaranteed quality but ₹23,000 higher cost and traffic delivery risk.",
          },
        ],
        simulatedTimeDeltaMin: 30,
      };
    } else if (scenarioId === "late_contingent") {
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId: "late_contingent",
        title: "Contingent C05 (IIT Bombay, 42 Pax) Bus Delay (3 Hours)",
        severity: "HIGH",
        peopleAffected: 42,
        affectedEntities: {
          participants: 42,
          rooms: 14,
          events: 3,
          venues: 2,
          meals: 42,
          shuttles: 3,
          staff: 2,
        },
        keyRisks: [
          "Contingent arrives after scheduled prelim round heats at 11:00",
          "Hostel check-in queue overflow during lunch hour",
          "Missed lunch slot requires hot food reservation",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Dynamic Heat Shift & Fast-Track Check-In",
            strategy: "Swap C05 heats to afternoon slot 15:30; pre-print room keys and box lunch at transport drop-off.",
            isRecommended: true,
            peopleMoved: 42,
            scheduleChanges: 2,
            resourceMoves: 1,
            costDeltaInr: 4500,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Standard heat scheduling order",
                rationale: "Heats swapped with C18 willing contingent.",
              },
            ],
            summary: "Zero forfeits; smooth participant experience with hot meals ready upon arrival.",
          },
          {
            id: "plan_b",
            name: "Plan B: Strict Forfeit Policy Enforcement",
            strategy: "Enforce arrival deadline; disqualified participants move directly to spectator status.",
            isRecommended: false,
            peopleMoved: 0,
            scheduleChanges: 0,
            resourceMoves: 0,
            costDeltaInr: 0,
            constraintsRelaxed: [],
            summary: "Strict adherence to rulebook but severe contingent dissatisfaction.",
          },
        ],
        simulatedTimeDeltaMin: 180,
      };
    } else if (scenarioId === "equipment_failure") {
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId: "equipment_failure",
        title: "Main Stage Digital Audio Console Power Circuit Failure",
        severity: "CRITICAL",
        peopleAffected: 650,
        affectedEntities: {
          participants: 650,
          rooms: 0,
          events: 2,
          venues: 1,
          meals: 0,
          shuttles: 0,
          staff: 3,
        },
        keyRisks: [
          "Battle of the Bands and Inaugural Keynote cannot broadcast audio",
          "Auditorium audience waiting with no sound",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Deploy Logistics Warehouse Backup Rig",
            strategy: "Dispatch backup Yamaha 32-channel console from Warehouse B with express setup crew.",
            isRecommended: true,
            peopleMoved: 0,
            scheduleChanges: 1,
            resourceMoves: 1,
            costDeltaInr: 12000,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Setup buffer time minimum (15 min)",
                rationale: "Accelerated parallel patch testing with 4 sound technicians.",
              },
            ],
            summary: "25-minute delay; restores full 32-track recording capability.",
          },
        ],
        simulatedTimeDeltaMin: 25,
      };
    } else if (scenarioId === "venue_change") {
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId: "venue_change",
        title: "Heavy Rain Waterlogging: Amphitheatre to Sports Complex",
        severity: "HIGH",
        peopleAffected: 450,
        affectedEntities: {
          participants: 450,
          rooms: 0,
          events: 2,
          venues: 2,
          meals: 0,
          shuttles: 2,
          staff: 8,
        },
        keyRisks: [
          "Indoor Sports Complex seating capacity (900) vs expected crowd (1,100)",
          "15-minute inter-venue travel walk in rain",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Relocate to Indoor Sports Complex with Overflow Screen",
            strategy: "Transfer sound/lighting gear indoors; setup live LED stream in Dining Hall for overflow.",
            isRecommended: true,
            peopleMoved: 450,
            scheduleChanges: 1,
            resourceMoves: 4,
            costDeltaInr: 28000,
            constraintsRelaxed: [
              {
                type: "SOFT",
                constraint: "Venue travel buffer (15 min)",
                rationale: "Added covered walkway escort volunteers.",
              },
            ],
            summary: "Full rain protection; all 1,100 attendees accommodated across main & overflow zones.",
          },
        ],
        simulatedTimeDeltaMin: 35,
      };
    } else if (scenarioId === "duplicate_participant") {
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId: "duplicate_participant",
        title: "Duplicate Participant Collision (P0102 Aarav Sharma / P0103)",
        severity: "MEDIUM",
        peopleAffected: 2,
        affectedEntities: {
          participants: 2,
          rooms: 1,
          events: 1,
          venues: 0,
          meals: 2,
          shuttles: 0,
          staff: 1,
        },
        keyRisks: [
          "Ghost bed occupied in Hostel 1 Room 102",
          "Double meal pass and event registration conflict",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Merge Canonical Record & Release Ghost Bed",
            strategy: "Consolidate P0103 into P0102; release unused bed H1-102-B into available pool.",
            isRecommended: true,
            peopleMoved: 0,
            scheduleChanges: 0,
            resourceMoves: 0,
            costDeltaInr: 0,
            constraintsRelaxed: [],
            summary: "Instant reconciliation; 1 bed freed up for shortage queue; reversible merge record logged.",
          },
        ],
        simulatedTimeDeltaMin: 0,
      };
    } else {
      // duplicate_merchandise_claim and other extras
      dryRunData = {
        incidentId: `INC-${Date.now()}`,
        scenarioId,
        title: "Duplicate Merchandise Claim Fraud Prevention",
        severity: "MEDIUM",
        peopleAffected: 1,
        affectedEntities: {
          participants: 1,
          rooms: 0,
          events: 0,
          venues: 1,
          meals: 0,
          shuttles: 0,
          staff: 1,
        },
        keyRisks: [
          "T-shirt QR code presented at Counter 2 after prior issuance at Counter 1",
          "Volunteer inventory discrepancy risk",
        ],
        plans: [
          {
            id: "plan_a",
            name: "Plan A: Reject Second Claim & Display Audit History",
            strategy: "Lock item issuance with ALREADY_ISSUED violation and display previous transaction log.",
            isRecommended: true,
            peopleMoved: 0,
            scheduleChanges: 0,
            resourceMoves: 0,
            costDeltaInr: 0,
            constraintsRelaxed: [],
            summary: "Hard constraint unique(canonical_participant_id, item_id) strictly enforced.",
          },
        ],
        simulatedTimeDeltaMin: 0,
      };
    }

    return HttpResponse.json({
      data: dryRunData,
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/incidents/:id/approve", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    const planId = body.plan_id || "plan_a";
    const reason = body.reason || "Operational emergency recovery approved by Festival Director";

    // Find or create incident
    let incident = mockIncidents.find((i) => i.id === id);
    if (!incident) {
      incident = {
        id,
        scenarioId: body.scenario_id || "hostel_closure",
        title: body.title || "Emergency Operational Incident",
        severity: "CRITICAL",
        status: "RESOLVING",
        createdAt: new Date().toISOString(),
        peopleAffected: 85,
        approvedPlan: planId,
        approvedBy: "Devashish Roy (Festival Director)",
        approvalReason: reason,
        downstreamUpdates: [
          {
            id: `ds_${Date.now()}_1`,
            domain: "Accommodation",
            label: "Reallocate participants to external properties",
            status: "UPDATED",
            details: "Beds reallocated; state synced with ChangeService",
            entityRoute: "/accommodation",
          },
          {
            id: `ds_${Date.now()}_2`,
            domain: "Transport",
            label: "Dispatch express shuttle loops",
            status: "UPDATED",
            details: "Capacity augmented with 3 express loops",
            entityRoute: "/transport",
          },
          {
            id: `ds_${Date.now()}_3`,
            domain: "Catering",
            label: "Transfer meal distribution tokens",
            status: "UPDATED",
            details: "Dietary needs matched and vendor notified",
            entityRoute: "/food",
          },
          {
            id: `ds_${Date.now()}_4`,
            domain: "Staff",
            label: "Deploy replacement and night escorts",
            status: "PENDING",
            details: "Staff notification sent; waiting for volunteer check-in",
            entityRoute: "/staff",
          },
        ],
        beforeMetrics: {
          unplacedParticipants: 85,
          mealShortages: 85,
          delayedEvents: 2,
          transportDeficit: 38,
          extraCostInr: 0,
        },
        afterMetrics: {
          unplacedParticipants: 0,
          mealShortages: 0,
          delayedEvents: 0,
          transportDeficit: 0,
          extraCostInr: 42500,
        },
      };
      mockIncidents.unshift(incident);
    } else {
      incident.status = "RESOLVED";
      incident.resolvedAt = new Date().toISOString();
      incident.approvedPlan = planId;
      incident.approvalReason = reason;
    }

    return HttpResponse.json({
      data: {
        change_set_id: `cs_inc_${Date.now()}`,
        status: "APPLIED",
        incident,
        message: "Recovery plan approved and applied through ChangeService. Operational state updated.",
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/incidents/:id/verify-downstream", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    const downstreamId = body.downstream_id;

    const incident = mockIncidents.find((i) => i.id === id);
    if (incident) {
      const item = incident.downstreamUpdates.find((d) => d.id === downstreamId);
      if (item) {
        item.status = "VERIFIED";
        item.verifiedAt = new Date().toISOString();
        item.verifiedBy = "Auditor / Lead";
      }
    }

    return HttpResponse.json({
      data: {
        status: "VERIFIED",
        downstream_id: downstreamId,
      },
      meta: {},
      warnings: [],
    });
  }),

  // ==========================================
  // 2. IMPACT ANALYSIS & BLAST RADIUS
  // ==========================================
  http.get("*/api/v1/impact/tree", ({ request }) => {
    const url = new URL(request.url);
    const incidentId = url.searchParams.get("incident_id") || "INC-2026-001";

    const report: ImpactReportData = {
      rootChange: {
        id: incidentId,
        action: "hostel.emergency_closure",
        entityType: "accommodation_building",
        entityId: "HOSTEL-03",
        description: "Hostel 3 structural plumbing burst flooding ground floor and electrical ducting.",
        triggeredAt: "2026-10-31T06:30:00Z",
        actor: "Director Devashish Roy",
      },
      countsByType: {
        participants: 85,
        accommodation: 28,
        events: 3,
        venues: 2,
        vendors: 1,
        transport: 7,
        staff: 6,
        inventory: 14,
      },
      tree: [
        {
          id: "grp_participants",
          type: "participant",
          label: "Participants Affected (85 students)",
          severity: "CRITICAL",
          peopleAffected: 85,
          status: "REALLOCATED",
          children: [
            {
              id: "P0102",
              type: "participant",
              label: "Aarav Sharma (IIT Bombay - Contingent C05)",
              severity: "CRITICAL",
              peopleAffected: 1,
              status: "REALLOCATED",
              details: {
                originalBed: "Hostel 3 Room 102",
                reallocatedBed: "Lakeview Resort Room 304",
                transportStatus: "Shuttle Run S-02 Assigned",
              },
            },
            {
              id: "P0103",
              type: "participant",
              label: "Rohan Deshmukh (IIT Bombay - Contingent C05)",
              severity: "HIGH",
              peopleAffected: 1,
              status: "REALLOCATED",
              details: {
                originalBed: "Hostel 3 Room 102",
                reallocatedBed: "Lakeview Resort Room 304",
              },
            },
            {
              id: "P0482",
              type: "participant",
              label: "Isha Malhotra (BITS Pilani - Minor, Age 17)",
              severity: "CRITICAL",
              peopleAffected: 1,
              status: "MITIGATED",
              details: {
                originalBed: "Hostel 3 Room 204",
                reallocatedBed: "Campus Guest House Wing B (On-Campus Safe Zone)",
                guardianApproval: "VERIFIED",
                nightEscort: "Assigned (Ankit Mehra)",
              },
            },
          ],
        },
        {
          id: "grp_accom",
          type: "accommodation",
          label: "Accommodation & Housing (28 rooms disrupted)",
          severity: "CRITICAL",
          peopleAffected: 85,
          status: "DISRUPTED",
          children: [
            {
              id: "ROOM_H3_101",
              type: "accommodation",
              label: "Hostel 3 Room 101 - 108 (Ground Floor Flooded)",
              severity: "CRITICAL",
              peopleAffected: 24,
              status: "DISRUPTED",
            },
            {
              id: "PROP_LAKEVIEW",
              type: "accommodation",
              label: "Lakeview Resort (External Property - 45 Beds Absorbed)",
              severity: "MEDIUM",
              peopleAffected: 45,
              status: "REALLOCATED",
            },
          ],
        },
        {
          id: "grp_events",
          type: "event",
          label: "Events & Scheduling (3 events delayed/rescheduled)",
          severity: "HIGH",
          peopleAffected: 42,
          status: "MITIGATED",
          children: [
            {
              id: "EVT-PRELIM-01",
              type: "event",
              label: "Battle of the Bands - Preliminary Heat 2",
              severity: "HIGH",
              peopleAffected: 18,
              status: "MITIGATED",
              details: {
                originalTime: "11:00",
                rescheduledTime: "11:45 (+45 min buffer)",
                venue: "Main Auditorium (V01)",
              },
            },
          ],
        },
        {
          id: "grp_transport",
          type: "transport",
          label: "Transportation & Shuttles (7 shuttle runs impacted)",
          severity: "HIGH",
          peopleAffected: 85,
          status: "REALLOCATED",
          children: [
            {
              id: "S-RUN-01",
              type: "transport",
              label: "Express Shuttle Loop: Lakeview <-> Campus Hub",
              severity: "HIGH",
              peopleAffected: 45,
              status: "REALLOCATED",
              details: {
                assignedVehicle: "Vehicle 1 & 3",
                hourlyFrequency: "Every 25 mins",
              },
            },
          ],
        },
        {
          id: "grp_food",
          type: "vendor",
          label: "Food & Catering (85 breakfast/lunch rations shifted)",
          severity: "MEDIUM",
          peopleAffected: 85,
          status: "MITIGATED",
          children: [
            {
              id: "VND-ANNAPURNA",
              type: "vendor",
              label: "Annapurna Caterers (West Wing Annex)",
              severity: "LOW",
              peopleAffected: 85,
              status: "MITIGATED",
            },
          ],
        },
      ],
      beforeAfterComparison: [
        {
          metric: "Unplaced Participants",
          before: "85 unplaced",
          after: "0 unplaced (all placed)",
          delta: "-85",
          status: "improved",
        },
        {
          metric: "Contingent Separation Index",
          before: "0% split",
          after: "0% split (cohesion preserved)",
          delta: "0%",
          status: "neutral",
        },
        {
          metric: "Shuttle Capacity Deficit",
          before: "-38 seats short",
          after: "+10 seats surplus (express loops added)",
          delta: "+48",
          status: "improved",
        },
        {
          metric: "Operational Cost Delta",
          before: "₹0",
          after: "+₹42,500",
          delta: "+₹42,500",
          status: "degraded",
        },
      ],
    };

    return HttpResponse.json({
      data: report,
      meta: {},
      warnings: [],
    });
  }),

  // ==========================================
  // 3. STAFF & SHIFTS
  // ==========================================
  http.get("*/api/v1/staff", () => {
    return HttpResponse.json({
      data: {
        items: mockStaffList,
        total: mockStaffList.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/staff/shifts", () => {
    return HttpResponse.json({
      data: {
        items: mockShifts,
        total: mockShifts.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/staff/demand", () => {
    const slots: CoverageHourlySlot[] = [
      { hour: "08:00", demand: 4, onShift: 4, deficit: 0, status: "COVERED" },
      { hour: "10:00", demand: 6, onShift: 6, deficit: 0, status: "COVERED" },
      { hour: "12:00", demand: 8, onShift: 5, deficit: 3, status: "UNCOVERED" },
      { hour: "14:00", demand: 8, onShift: 4, deficit: 4, status: "UNCOVERED" },
      { hour: "16:00", demand: 6, onShift: 6, deficit: 0, status: "COVERED" },
      { hour: "18:00", demand: 7, onShift: 6, deficit: 1, status: "TIGHT" },
      { hour: "20:00", demand: 9, onShift: 8, deficit: 1, status: "TIGHT" },
      { hour: "22:00", demand: 5, onShift: 5, deficit: 0, status: "COVERED" },
      { hour: "00:00", demand: 3, onShift: 2, deficit: 1, status: "UNCOVERED" },
    ];
    return HttpResponse.json({
      data: {
        slots,
        totalDemand: 56,
        totalOnShift: 46,
        uncoveredHoursCount: 3,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/staff/overloaded", () => {
    const overloaded = mockStaffList.filter((s) => s.isOverloaded);
    return HttpResponse.json({
      data: {
        items: overloaded,
        total: overloaded.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/staff/conflicts", () => {
    const conflicting = mockShifts.filter((s) => s.isOverlapping);
    return HttpResponse.json({
      data: {
        items: conflicting,
        total: conflicting.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/staff/replacements/suggest", () => {
    const candidates: ReplacementCandidate[] = [
      {
        staffId: "STF06",
        name: "Sunita Reddy",
        role: "VOLUNTEER",
        matchScore: 94,
        skillsMatched: ["Registration Desk", "Crowd Control", "First Aid"],
        hoursWorkedToday: 4,
        proximityMinutes: 3,
        reason: "Well rested, nearby in Dining Hall, verified skills match.",
      },
      {
        staffId: "STF04",
        name: "Kavita Rao",
        role: "VOLUNTEER",
        matchScore: 82,
        skillsMatched: ["Crowd Control"],
        hoursWorkedToday: 5,
        proximityMinutes: 8,
        reason: "Available after 13:00, moderate fatigue score.",
      },
    ];
    return HttpResponse.json({
      data: { candidates },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/staff/shifts/:id/replace", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    const replacementStaffId = body.replacement_staff_id || body.payload?.replacement_staff_id || "STF06";
    const handoverNote = body.handover_notes || body.payload?.handover_notes || body.reason;

    if (!handoverNote || !handoverNote.trim()) {
      return HttpResponse.json(
        {
          error: {
            code: "VALIDATION_ERROR",
            message: "A shift handover note is strictly enforced under FestOS policy.",
          },
        },
        { status: 422 }
      );
    }

    const shift = mockShifts.find((s) => s.id === id);
    const replacement = mockStaffList.find((s) => s.id === replacementStaffId);
    if (shift && replacement) {
      shift.staffId = replacement.id;
      shift.staffName = replacement.name;
      shift.role = replacement.role;
      shift.status = "REPLACED";
      shift.isOverloaded = false;
      shift.handoverCompleted = true;
      shift.handoverNotes = handoverNote;
    }

    return HttpResponse.json({
      data: {
        status: "REPLACED",
        shift,
        message: `Shift successfully reassigned to ${replacement?.name || "replacement staff"}. Handover recorded.`,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/staff/handovers", () => {
    return HttpResponse.json({
      data: {
        items: mockHandovers,
        total: mockHandovers.length,
        missing_count: mockHandovers.filter((h) => h.isMissing).length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/staff/handovers", async ({ request }) => {
    const body = (await request.json()) as any;
    const newHandover: HandoverNoteRecord = {
      id: `HO-${Date.now()}`,
      venueId: body.venue_id || "V04",
      venueName: body.venue_name || "Registration Concourse",
      hour: body.hour || "14:00",
      outgoingStaffName: body.outgoing_staff_name || "Staff Lead",
      incomingStaffName: body.incoming_staff_name || "Incoming Lead",
      notes: body.notes || "Standard shift transition completed.",
      timestamp: new Date().toISOString(),
      isMissing: false,
      acknowledgedByIncoming: true,
    };
    mockHandovers.unshift(newHandover);

    return HttpResponse.json({
      data: newHandover,
      meta: {},
      warnings: [],
    });
  }),

  // ==========================================
  // 4. TRANSPORTATION & SAFETY
  // ==========================================
  http.get("*/api/v1/transport/assumptions", () => {
    return HttpResponse.json({
      data: mockTransportAssumptions,
      meta: { is_assumed: true },
      warnings: ["All shuttle and transport models are heuristic ASSUMED parameters."],
    });
  }),

  http.patch("*/api/v1/transport/assumptions", async ({ request }) => {
    const body = (await request.json()) as any;
    const payload = body.payload || body;
    mockTransportAssumptions = {
      ...mockTransportAssumptions,
      ...payload,
    };
    return HttpResponse.json({
      data: mockTransportAssumptions,
      meta: { is_assumed: true },
      warnings: [],
    });
  }),

  http.get("*/api/v1/transport/shuttles/plan", () => {
    const slots: ShuttlePlanSlot[] = [
      {
        id: "SP-01",
        propertyId: "PROP-01",
        propertyName: "Lakeview Resort",
        hour: "08:00",
        passengerDemand: 38,
        assignedVehicles: 2,
        confirmedCapacity: 24,
        deficit: -14,
        status: "DEFICIT",
      },
      {
        id: "SP-02",
        propertyId: "PROP-01",
        propertyName: "Lakeview Resort",
        hour: "10:00",
        passengerDemand: 24,
        assignedVehicles: 2,
        confirmedCapacity: 24,
        deficit: 0,
        status: "OK",
      },
      {
        id: "SP-03",
        propertyId: "PROP-02",
        propertyName: "Campus Guest House",
        hour: "12:00",
        passengerDemand: 12,
        assignedVehicles: 1,
        confirmedCapacity: 12,
        deficit: 0,
        status: "OK",
      },
      {
        id: "SP-04",
        propertyId: "PROP-03",
        propertyName: "Green Palms",
        hour: "14:00",
        passengerDemand: 20,
        assignedVehicles: 1,
        confirmedCapacity: 12,
        deficit: -8,
        status: "DEFICIT",
      },
      {
        id: "SP-05",
        propertyId: "PROP-04",
        propertyName: "Silver Oak",
        hour: "21:00",
        passengerDemand: 45,
        assignedVehicles: 2,
        confirmedCapacity: 24,
        deficit: -21,
        status: "DEFICIT",
      },
      {
        id: "SP-06",
        propertyId: "PROP-01",
        propertyName: "Lakeview Resort",
        hour: "00:00",
        passengerDemand: 14,
        assignedVehicles: 0,
        confirmedCapacity: 0,
        deficit: -14,
        status: "DEFICIT",
      },
    ];
    return HttpResponse.json({
      data: {
        slots,
        totalDemand: 153,
        totalCapacity: 96,
        netDeficit: -57,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/transport/safety/night-roster", () => {
    return HttpResponse.json({
      data: {
        items: mockNightRoster,
        total: mockNightRoster.length,
        unverified_count: mockNightRoster.filter((n) => !n.isVerified).length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/transport/safety/verify", async ({ request }) => {
    const body = (await request.json()) as any;
    const participantId = body.participant_id || body.payload?.participant_id;

    const item = mockNightRoster.find((n) => n.participantId === participantId || n.id === participantId);
    if (item) {
      item.isVerified = !item.isVerified;
      if (item.isVerified) {
        item.verifiedAt = new Date().toISOString();
        item.verifiedBy = "Duty Officer";
      } else {
        item.verifiedAt = undefined;
        item.verifiedBy = undefined;
      }
    }

    return HttpResponse.json({
      data: {
        status: item?.isVerified ? "VERIFIED" : "UNVERIFIED",
        item,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/transport/guardians/queue", () => {
    return HttpResponse.json({
      data: {
        items: mockGuardianQueue,
        total: mockGuardianQueue.length,
        pending_count: mockGuardianQueue.filter((g) => g.status === "PENDING_REVIEW").length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/transport/guardians/:id/approve", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    const action = body.action || "APPROVE";
    const reason = body.reason || "Guardian consent document verified with university dean";

    const entry = mockGuardianQueue.find((g) => g.id === id || g.participantId === id);
    if (entry) {
      entry.status = action === "APPROVE" ? "APPROVED" : "REJECTED";
      entry.reviewedBy = "Devashish Roy (Festival Director)";
      entry.reviewReason = reason;
    }

    return HttpResponse.json({
      data: {
        status: entry?.status || "APPROVED",
        entry,
        message: "Guardian authorization recorded in audit ledger.",
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/transport/coverage/summary", () => {
    const summary: SafetyCoverageSummary = {
      totalRequiringTransport: 186,
      confirmedShuttleCapacity: 168,
      uncoveredTransportRequests: 18,
      lateNightMovements: 24,
      minorExternalAccommodations: 14,
      unassignedEscorts: 5,
      highRiskPropertyTrips: 2,
    };
    return HttpResponse.json({
      data: summary,
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/transport/alerts", () => {
    return HttpResponse.json({
      data: {
        items: mockTransportAlerts,
        total: mockTransportAlerts.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/transport/alerts/:id/resolve", async ({ params }) => {
    const id = params.id as string;
    const alert = mockTransportAlerts.find((a) => a.id === id);
    if (alert) {
      alert.isResolved = true;
    }
    return HttpResponse.json({
      data: {
        status: "RESOLVED",
        alert_id: id,
        message: "Action successfully dispatched and resolved.",
      },
      meta: {},
      warnings: [],
    });
  }),

  // ==========================================
  // 5. NOTIFICATIONS
  // ==========================================
  http.get("*/api/v1/notifications/drafts", () => {
    return HttpResponse.json({
      data: {
        items: mockNotificationDrafts,
        total: mockNotificationDrafts.length,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/notifications/drafts/:id/edit", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    const draft = mockNotificationDrafts.find((d) => d.id === id);
    if (draft) {
      if (body.subject) draft.subject = body.subject;
      if (body.body) draft.body = body.body;
      if (body.priority) draft.priority = body.priority;
    }
    return HttpResponse.json({
      data: draft,
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/notifications/drafts/:id/approve", async ({ params }) => {
    const id = params.id as string;
    const draft = mockNotificationDrafts.find((d) => d.id === id);
    if (draft) {
      draft.status = "APPROVED";
      draft.approvedBy = "Devashish Roy (Festival Director)";
    }
    return HttpResponse.json({
      data: draft,
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/notifications/drafts/:id/send", async ({ params }) => {
    const id = params.id as string;
    const draft = mockNotificationDrafts.find((d) => d.id === id);
    if (draft) {
      draft.status = "SENT";
      draft.sentAt = new Date().toISOString();

      mockDeliveryLog.unshift({
        id: `DL-${Date.now()}`,
        draftId: draft.id,
        audience: draft.audience,
        audienceLabel: draft.audienceLabel,
        recipientCount: draft.recipientCount,
        channel: draft.audience === "LEADERS" ? "SMS_BROADCAST" : "WHATSAPP_API",
        subject: draft.subject,
        bodyPreview: draft.body.substring(0, 80) + "...",
        sentAt: draft.sentAt,
        deliveredCount: draft.recipientCount,
        acknowledgedCount: Math.floor(draft.recipientCount * 0.9),
        status: "DELIVERED",
      });
    }
    return HttpResponse.json({
      data: {
        status: "SENT",
        draft,
        message: `Successfully dispatched mock-send broadcast to ${draft?.recipientCount || 0} recipients.`,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/notifications/log", () => {
    return HttpResponse.json({
      data: {
        items: mockDeliveryLog,
        total: mockDeliveryLog.length,
      },
      meta: {},
      warnings: [],
    });
  }),
];
