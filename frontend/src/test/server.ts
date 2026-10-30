import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("*/health", () => {
    return HttpResponse.json({
      status: "healthy",
      version: "0.1.0",
      now: "2026-10-30T10:00:00Z",
    });
  }),

  http.get("*/api/v1/meta", () => {
    return HttpResponse.json({
      version: "0.1.0",
      now: "2026-10-30T10:00:00Z",
      modules: ["participants", "contingents", "reconciliation", "unknowns"],
      auth_disabled: true,
    });
  }),

  http.post("*/api/v1/_example/items", async ({ request }) => {
    const body = (await request.json()) as any;
    if (body.name === "fail") {
      return HttpResponse.json(
        {
          error: {
            code: "VALIDATION_ERROR",
            message: "Invalid name",
            request_id: "req_test_123",
          },
        },
        { status: 422 }
      );
    }
    return HttpResponse.json({
      data: {
        change_set_id: "cs_mock_123",
        status: "APPLIED",
        violations: [],
      },
      meta: {},
      warnings: [],
    });
  }),

  // Participants Endpoints
  http.get("*/api/v1/participants", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "P0102",
            canonical_participant_id: "P0102",
            name: "Aarav Sharma",
            college: "IIT Bombay",
            contingent_id: "C05",
            role: "PARTICIPANT",
            status: "EXPECTED",
            diet: "UNKNOWN",
            housing_preference: "UNKNOWN",
            accommodation_requested: "YES",
            gender: "Male",
            tshirt_size: "L",
            arrival_at: "2026-10-31T08:30:00Z",
          },
          {
            id: "P0103",
            canonical_participant_id: "P0103",
            name: "Rohan Deshmukh",
            college: "IIT Bombay",
            contingent_id: "C05",
            role: "LEADER",
            status: "EXPECTED",
            diet: "VEG",
            housing_preference: "CAMPUS_HOSTEL",
            accommodation_requested: "YES",
            gender: "Male",
            tshirt_size: "XL",
            arrival_at: "2026-10-31T07:00:00Z",
          },
        ],
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/participants/:id/360", ({ params }) => {
    const id = params.id as string;
    return HttpResponse.json({
      data: {
        participant: {
          id,
          canonical_participant_id: id,
          name: "Aarav Sharma",
          college: "IIT Bombay",
          email: "a***@iitb.ac.in",
          phone: "+91 98**** 1234",
          role: "PARTICIPANT",
          status: "EXPECTED",
          arrival_at: "2026-10-31T08:30:00Z",
          departure_at: "2026-11-03T18:00:00Z",
          diet: "UNKNOWN",
          accommodation_requested: "YES",
        },
        contingent: {
          id: "C05",
          code: "C05",
          name: "IIT Bombay Contingent",
          college: "IIT Bombay",
          leader_name: "Rohan Deshmukh",
          leader_found: true,
          escort_name: "Dr. V. K. Raman",
          escort_found: false,
        },
        registrations: [
          {
            registration_id: "reg_001",
            event_id: "EV01",
            event_name: "RoboWars",
            team_id: "TM_05",
            status: "REGISTERED",
          },
        ],
        diet: {
          preference: "UNKNOWN",
          status: "UNVERIFIED",
          verification_history: [],
        },
        accessibility: {
          needs: {},
          requires_ground_floor: false,
          requires_accessible_transit: false,
        },
        merchandise: {
          tshirt_size: "L",
          entitlement: "PENDING",
          claims: [],
        },
        operational_status: {
          current_status: "EXPECTED",
          can_transition_to: ["ARRIVED", "CANCELLED", "NO_SHOW"],
          last_updated: "2026-10-30T10:00:00Z",
        },
        sections: {
          accommodation: {
            status: "UNASSIGNED",
            plan_kind: null,
            room: null,
          },
          transport: {
            shuttle_assigned: false,
          },
        },
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/participants/:id/timeline", ({ params }) => {
    return HttpResponse.json({
      data: {
        participant_id: params.id,
        events: [
          {
            id: "aud_112233",
            action: "participant.change_status",
            actor_id: "usr_reception01",
            actor_role: "VOLUNTEER",
            reason: "Physical arrival verified at reception desk",
            timestamp: "2026-10-31T08:35:10Z",
            before: { status: "EXPECTED" },
            after: { status: "ARRIVED" },
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/participants/:id/status", async () => {
    return HttpResponse.json({
      data: {
        change_set_id: "cs_status_123",
        status: "APPLIED",
        violations: [],
      },
      meta: {},
      warnings: [],
    });
  }),

  // Contingents Endpoints
  http.get("*/api/v1/contingents", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "C05",
            code: "C05",
            name: "IIT Bombay Contingent",
            college: "IIT Bombay",
            leader: "Rohan Deshmukh",
            escort: "Dr. V. K. Raman",
            strength_declared: 80,
            strength_actual: 72,
            gap: -8,
            leader_status: "FOUND",
            escort_status: "MISSING",
            status: "ACTIVE",
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
        total_pages: 1,
      },
      meta: {
        total_declared: 2842,
        total_actual: 2836,
        contingents_with_mismatch: 7,
      },
      warnings: [],
    });
  }),

  http.get("*/api/v1/contingents/:id/status", ({ params }) => {
    return HttpResponse.json({
      data: {
        contingent_id: params.id,
        college: "IIT Bombay",
        strength: {
          declared: 80,
          actual: 72,
          gap: -8,
          status: "DISCREPANCY_UNDER",
        },
        leadership: {
          leader: {
            name: "Rohan Deshmukh",
            participant_id: "P0102",
            status: "FOUND",
            role: "LEADER",
            attendance: "EXPECTED",
          },
          escort: {
            name: "Dr. V. K. Raman",
            participant_id: null,
            status: "MISSING",
            note: "Escort declared in master but missing from participant rosters",
          },
        },
        attendance: {
          EXPECTED: 68,
          ARRIVED: 4,
          CHECKED_IN: 0,
        },
        travel_coordination: {
          earliest_arrival: "2026-10-31T06:00:00Z",
          latest_departure: "2026-11-03T20:00:00Z",
          arrival_windows: [
            { window: "2026-10-31 Morning (06:00-12:00)", count: 52 },
            { window: "2026-10-31 Afternoon (12:00-18:00)", count: 20 },
          ],
        },
        event_participation: {
          total_registrations: 142,
          unique_events: 16,
          events: [
            { event_id: "EV01", name: "RoboWars", participants_count: 8 },
          ],
        },
        dietary_summary: {
          VEG: 45,
          NON_VEG: 18,
          JAIN: 2,
          UNKNOWN: 7,
        },
        merchandise_summary: {
          eligible: 72,
          claimed: 0,
          pending: 72,
          size_breakdown: {
            S: 10,
            M: 28,
            L: 24,
            XL: 8,
            UNKNOWN: 2,
          },
        },
        alerts: [
          {
            code: "STRENGTH_MISMATCH",
            severity: 2,
            message: "Declared strength 80 differs from actual rosters 72 (gap: -8).",
          },
        ],
        housing_fragmentation: {
          status: "OPTIMIZED",
          properties_count: 1,
          buildings_count: 2,
          leader_proximity_meters: 65,
          split_reason: "Campus gender separation: 48 male members assigned to Hostel 3; 24 female members to Hostel 4.",
          allocations: [
            { building: "Hostel 3", count: 48, category: "Male" },
            { building: "Hostel 4", count: 24, category: "Female" },
          ],
        },
      },
      meta: {},
      warnings: [],
    });
  }),

  // Reconciliation Endpoints
  http.get("*/api/v1/reconciliation/waterfall", () => {
    return HttpResponse.json({
      data: {
        counts: {
          raw: 2836,
          narrative_expected: 2400,
          declared: 2842,
          declared_vs_raw_gap: -6,
          exact_duplicates: 0,
          likely_duplicates: 7,
          possible_duplicates: 305,
          invalid: 3,
          unexplained: 426,
        },
        waterfall: [
          {
            step: "DECLARED_TOTAL",
            label: "Total Declared Across 38 Contingents",
            count: 2842,
            delta: 2842,
            note: "Sum of strength_declared in contingents.csv",
          },
          {
            step: "RAW_ROSTER_TOTAL",
            label: "Raw Imported Participant Rosters",
            count: 2836,
            delta: 0,
            note: "Exact count in participants.csv",
          },
          {
            step: "NARRATIVE_SURPLUS",
            label: "Unexplained Surplus Over Narrative Baseline",
            count: 2400,
            delta: -426,
            note: "Surplus roster participants over early planning narrative (2,400)",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/reconciliation/duplicates", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "dup_0102a",
            participant_a_id: "P0412",
            participant_b_id: "P1845",
            participant_a_name: "Aditya Verma",
            participant_b_name: "Aditya Verma",
            college_a: "BITS Pilani",
            college_b: "BITS Pilani",
            score: 0.92,
            classification: "LIKELY",
            reasons: {
              name_similarity: 1.0,
              contingent_match: true,
              phone_similarity: 0.9,
            },
            status: "PENDING",
            created_at: "2026-10-30T10:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/reconciliation/merge", () => {
    return HttpResponse.json({
      data: {
        merge_record_id: "mrg_abc12345",
        canonical_id: "P0412",
        merged_id: "P1845",
        repointed_registrations: 1,
        repointed_claims: 0,
        status: "APPLIED",
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/reconciliation/undo-merge/:id", () => {
    return HttpResponse.json({
      data: {
        merge_record_id: "mrg_abc12345",
        restored_canonical_id: "P0412",
        restored_participant_id: "P1845",
        status: "REVERTED",
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/reconciliation/keep-separate", () => {
    return HttpResponse.json({
      data: {
        candidate_id: "dup_0102a",
        status: "IGNORED",
      },
      meta: {},
      warnings: [],
    });
  }),

  // Unknowns Endpoints
  http.get("*/api/v1/unknowns/queue", () => {
    return HttpResponse.json({
      data: {
        total_unresolved_fields: 1284,
        queue: [
          {
            field: "accommodation_requested",
            entity_type: "participant",
            count: 418,
            criticality: 4,
            score: 1672,
            owner: "ACCOMMODATION_LEAD",
            impact_text: "Beds cannot be definitively blocked in Plan A/B without confirmed housing requirement.",
            sample_entity_ids: ["P0012", "P0045"],
          },
          {
            field: "diet",
            entity_type: "participant",
            count: 394,
            criticality: 3,
            score: 1182,
            owner: "FOOD_OPS_MANAGER",
            impact_text: "Catering procurement buffers risk meal shortages or food waste.",
            sample_entity_ids: ["P0001"],
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/unknowns/items", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "P0001",
            name: "Rohan Deshmukh",
            contingent_id: "C05",
            field: "diet",
            current_value: "UNKNOWN",
            status: "UNKNOWN",
            owner: "FOOD_OPS_MANAGER",
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/unknowns/verify", () => {
    return HttpResponse.json({
      data: {
        change_set_id: "cs_unk_verify_1",
        status: "APPLIED",
        violations: [],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/unknowns/token", () => {
    return HttpResponse.json({
      data: {
        token: "tok_test_leader_signed_123",
        expires_at: "2026-10-31T18:00:00Z",
        entity_type: "participant",
        entity_id: "P0001",
        field: "diet",
      },
      meta: {},
      warnings: [],
    });
  }),
];

export const server = setupServer(...handlers);
