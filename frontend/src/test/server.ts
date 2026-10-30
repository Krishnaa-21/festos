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
  // Accommodation Endpoints
  http.get("*/api/v1/accommodation/plans", () => {
    return HttpResponse.json({
      data: {
        plans: [
          {
            plan_id: "plan_A_cohesion",
            kind: "A",
            status: "CANDIDATE",
            name: "Plan A: Cohesion-First",
            on_campus_placed: 710,
            external_placed: 1284,
            unplaced_count: 150,
            contingent_splits: 4,
            total_cost_inr: 3315700,
            safety_flags_count: 12,
            accessibility_issues_count: 2,
            relaxed_constraints_count: 8,
            sacrifices_summary:
              "Sacrifices budget expenditure (₹33,15,700) to keep contingents unified within the same buildings.",
            created_at: "2026-10-30T10:00:00Z",
          },
          {
            plan_id: "plan_B_cost",
            kind: "B",
            status: "CANDIDATE",
            name: "Plan B: Cost-First",
            on_campus_placed: 710,
            external_placed: 1342,
            unplaced_count: 92,
            contingent_splits: 19,
            total_cost_inr: 2480000,
            safety_flags_count: 28,
            accessibility_issues_count: 4,
            relaxed_constraints_count: 31,
            sacrifices_summary:
              "Sacrifices contingent cohesion and group proximity to minimize external hotel booking costs.",
            created_at: "2026-10-30T10:00:00Z",
          },
          {
            plan_id: "plan_C_balanced",
            kind: "C",
            status: "CANDIDATE",
            name: "Plan C: Balanced (Recommended)",
            on_campus_placed: 710,
            external_placed: 1318,
            unplaced_count: 116,
            contingent_splits: 8,
            total_cost_inr: 2890000,
            safety_flags_count: 14,
            accessibility_issues_count: 1,
            relaxed_constraints_count: 12,
            sacrifices_summary:
              "Balanced compromises: permits minor contingent splits only when hotel cost exceeds threshold.",
            created_at: "2026-10-30T10:00:00Z",
          },
        ],
        budget_ceiling_inr: null,
        is_budget_unset: true,
      },
      meta: {},
      warnings: ["External Accommodation Budget is unset. Engine running in unconstrained mode."],
    });
  }),

  http.post("*/api/v1/accommodation/generate-plan", async ({ request }) => {
    const body = (await request.json()) as any;
    const kind = body.kind || "C";
    return HttpResponse.json({
      data: {
        plan_id: `plan_${kind}_generated_${Date.now()}`,
        kind,
        status: "CANDIDATE",
        name: kind === "A" ? "Plan A: Cohesion-First" : kind === "B" ? "Plan B: Cost-First" : "Plan C: Balanced (Custom)",
        on_campus_placed: 710,
        external_placed: 1310,
        unplaced_count: 124,
        contingent_splits: kind === "A" ? 4 : kind === "B" ? 18 : 7,
        total_cost_inr: kind === "A" ? 3350000 : kind === "B" ? 2450000 : 2890000,
        safety_flags_count: 14,
        accessibility_issues_count: 1,
        relaxed_constraints_count: 10,
        parameters_applied: {
          cleaning_buffer_minutes: body.cleaning_buffer_minutes ?? 180,
          max_distance_km: body.max_distance_km ?? 15,
          allow_split_contingents: body.allow_split_contingents ?? true,
        },
        sacrifices_summary:
          kind === "A"
            ? "Prioritizes contingent cohesion at maximum budget cost."
            : kind === "B"
            ? "Minimizes hotel costs by fragmenting large contingents across distant properties."
            : "Optimized balance between hotel cost and contingent integrity.",
        created_at: new Date().toISOString(),
      },
      meta: {},
      warnings: ["Generated using unverified external property constraints."],
    });
  }),

  http.get("*/api/v1/accommodation/shortages", () => {
    return HttpResponse.json({
      data: {
        total_unplaced: 116,
        grouped_by_reason: [
          {
            reason_code: "UNKNOWN_GENDER",
            title: "Gender Unknown (Safety Gate #2)",
            count: 48,
            description: "Room allocation cannot enforce campus hostel gender segregation safety rules.",
            affected_contingents: ["C05", "C08", "C12", "C15"],
            criticality: "HIGH",
          },
          {
            reason_code: "HARD_ACCESSIBILITY",
            title: "Ground-Floor Accessible Room Deficit",
            count: 14,
            description: "Participants with wheelchair/mobility needs exceed available ground-floor ramped rooms.",
            affected_contingents: ["C01", "C05", "C19"],
            criticality: "CRITICAL",
          },
          {
            reason_code: "EXTERNAL_CAPACITY_EXHAUSTED",
            title: "External Property Room Exhaustion",
            count: 34,
            description: "Remaining demand exceeds available bed blocks in verified nearby properties.",
            affected_contingents: ["C08", "C27", "C38"],
            criticality: "MEDIUM",
          },
          {
            reason_code: "MINOR_ESCORT_RESTRICTION",
            title: "Minor Participant Off-Campus Restriction",
            count: 20,
            description: "Minors (<18) without verified faculty escorts cannot be placed in off-campus hotels.",
            affected_contingents: ["C05", "C18", "C32"],
            criticality: "HIGH",
          },
        ],
        unplaced_items: [
          {
            participant_id: "P0104",
            name: "Sneha Mukherjee",
            contingent_id: "C05",
            college: "IIT Bombay",
            blocking_reason: "UNKNOWN_GENDER",
            accessibility_needed: false,
            housing_preference: "UNKNOWN",
            gender: "UNKNOWN",
          },
          {
            participant_id: "P0105",
            name: "Karan Johar",
            contingent_id: "C01",
            college: "IIM Ahmedabad",
            blocking_reason: "HARD_ACCESSIBILITY",
            accessibility_needed: true,
            housing_preference: "CAMPUS_HOSTEL",
            gender: "Male",
          },
          {
            participant_id: "P0106",
            name: "Ananya Panday",
            contingent_id: "C08",
            college: "BITS Pilani",
            blocking_reason: "EXTERNAL_CAPACITY_EXHAUSTED",
            accessibility_needed: false,
            housing_preference: "HOTEL",
            gender: "Female",
          },
          {
            participant_id: "P0107",
            name: "Aryan Khan",
            contingent_id: "C18",
            college: "SRCC Delhi",
            blocking_reason: "MINOR_ESCORT_RESTRICTION",
            accessibility_needed: false,
            housing_preference: "UNKNOWN",
            gender: "Male",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/accommodation/why-not/:id", ({ params }) => {
    const id = params.id as string;
    if (id === "P0105") {
      return HttpResponse.json({
        data: {
          participant_id: "P0105",
          name: "Karan Johar",
          contingent_id: "C01",
          blocking_requirement: "Rule 1: Hard Ground Floor Accessibility Guarantee",
          missing_information: "Wheelchair ramp certification needed on Block H1 Floor 1.",
          rejected_options: [
            { location: "Hostel 1 (Floor 2, Room 204)", reason: "Non-ground floor without elevator access" },
            { location: "Hotel Lemon Tree", reason: "Accessibility flag is UNVERIFIED" },
          ],
          counterfactual_impact: "If Hostel 1 Room 102 ground floor bed is cleared, participant can be placed immediately.",
          verification_target: { field: "accessibility_need", entity_id: "P0105" },
        },
        meta: {},
        warnings: [],
      });
    }

    return HttpResponse.json({
      data: {
        participant_id: id || "P0104",
        name: "Sneha Mukherjee",
        contingent_id: "C05",
        blocking_requirement: "Rule 2: Gender-Appropriate Allocation & Safety Policy",
        missing_information: "Gender attribute is UNKNOWN in raw import dataset.",
        rejected_options: [
          { location: "Hostel 3 (Wing B)", reason: "Boys hostel block: cannot place without gender confirmation" },
          { location: "Hostel 4 (Wing A)", reason: "Girls hostel block: cannot place without gender confirmation" },
          { location: "Hotel Radisson Rau", reason: "Property gender suitability flag is UNVERIFIED" },
        ],
        counterfactual_impact:
          "If verified as 'Female', 4 beds in Hostel 4 (Wing A, Room 204) become immediately assignable alongside contingent peers.",
        verification_target: {
          field: "gender",
          entity_id: id || "P0104",
        },
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/accommodation/occupancy", () => {
    return HttpResponse.json({
      data: {
        blocks: [
          {
            block_id: "H3",
            name: "Hostel 3 (Boys Block)",
            gender_class: "boys",
            total_beds: 360,
            occupied_beds: 348,
            cleaning_beds: 6,
            closed_beds: 2,
            free_beds: 4,
            floors: [
              {
                floor_number: 0,
                is_ground: true,
                rooms: [
                  {
                    room_id: "H3-101",
                    room_number: "101",
                    accessible: true,
                    status: "AVAILABLE",
                    cleaning_status: "READY",
                    beds: [
                      {
                        bed_id: "H3-101-A",
                        status: "OCCUPIED",
                        contingent_id: "C05",
                        contingent_name: "IIT Bombay",
                        contingent_color: "#6366f1",
                        participant_id: "P0103",
                        participant_name: "Rohan Deshmukh",
                        is_leader: true,
                        version: 1,
                      },
                      {
                        bed_id: "H3-101-B",
                        status: "FREE",
                        contingent_id: null,
                        participant_id: null,
                        version: 1,
                      },
                    ],
                  },
                  {
                    room_id: "H3-102",
                    room_number: "102",
                    accessible: true,
                    status: "CLEANING",
                    cleaning_status: "CLEANING",
                    cleaning_remaining_minutes: 120,
                    beds: [
                      {
                        bed_id: "H3-102-A",
                        status: "CLEANING",
                        contingent_id: null,
                        participant_id: null,
                        version: 1,
                      },
                      {
                        bed_id: "H3-102-B",
                        status: "FREE",
                        contingent_id: null,
                        participant_id: null,
                        version: 1,
                      },
                    ],
                  },
                ],
              },
              {
                floor_number: 1,
                is_ground: false,
                rooms: [
                  {
                    room_id: "H3-201",
                    room_number: "201",
                    accessible: false,
                    status: "OCCUPIED",
                    cleaning_status: "READY",
                    beds: [
                      {
                        bed_id: "H3-201-A",
                        status: "OCCUPIED",
                        contingent_id: "C05",
                        contingent_name: "IIT Bombay",
                        contingent_color: "#6366f1",
                        participant_id: "P0102",
                        participant_name: "Aarav Sharma",
                        is_leader: false,
                        version: 1,
                      },
                      {
                        bed_id: "H3-201-B",
                        status: "CLOSED",
                        contingent_id: null,
                        participant_id: null,
                        version: 1,
                      },
                    ],
                  },
                ],
              },
            ],
          },
          {
            block_id: "H4",
            name: "Hostel 4 (Girls Block)",
            gender_class: "girls",
            total_beds: 350,
            occupied_beds: 330,
            cleaning_beds: 10,
            closed_beds: 4,
            free_beds: 6,
            floors: [
              {
                floor_number: 0,
                is_ground: true,
                rooms: [
                  {
                    room_id: "H4-101",
                    room_number: "101",
                    accessible: true,
                    status: "AVAILABLE",
                    cleaning_status: "READY",
                    beds: [
                      {
                        bed_id: "H4-101-A",
                        status: "FREE",
                        contingent_id: null,
                        participant_id: null,
                        version: 1,
                      },
                      {
                        bed_id: "H4-101-B",
                        status: "FREE",
                        contingent_id: null,
                        participant_id: null,
                        version: 1,
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
        external_properties: [
          {
            property_id: "ext_01",
            name: "Radisson Blu Rau",
            total_beds: 200,
            occupied_beds: 184,
            free_beds: 16,
            cost_per_bed_night: 2800,
            distance_km: 11.5,
            accessibility_verified: false,
            gender_suitability_verified: false,
            transport_limited: true,
          },
          {
            property_id: "ext_02",
            name: "Lemon Tree Hotel Indore",
            total_beds: 150,
            occupied_beds: 140,
            free_beds: 10,
            cost_per_bed_night: 3200,
            distance_km: 14.2,
            accessibility_verified: false,
            gender_suitability_verified: false,
            transport_limited: false,
          },
          {
            property_id: "ext_03",
            name: "Sayaji Hotel Indore",
            total_beds: 120,
            occupied_beds: 115,
            free_beds: 5,
            cost_per_bed_night: 3800,
            distance_km: 18.0,
            accessibility_verified: false,
            gender_suitability_verified: false,
            transport_limited: true,
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/accommodation/check-constraints", async ({ request }) => {
    const body = (await request.json()) as any;
    const { participant_id, target_bed_id } = body;

    if (participant_id === "P0104" && target_bed_id?.startsWith("H3")) {
      return HttpResponse.json({
        data: {
          allowed: false,
          is_hard_violation: true,
          violations: [
            {
              code: "GENDER_MISMATCH_SAFETY",
              severity: 4,
              hard: true,
              message:
                "Hostel 3 is a Boys block. Participant P0104 has UNKNOWN gender; assignment violates hard campus safety rule #2.",
            },
          ],
          relaxed_soft_constraints: [
            {
              code: "CONTINGENT_COHESION",
              message: "Assignment places participant in same building as contingent peers.",
            },
          ],
        },
        meta: {},
        warnings: [],
      });
    }

    if (participant_id === "P0105" && target_bed_id?.includes("201")) {
      return HttpResponse.json({
        data: {
          allowed: false,
          is_hard_violation: true,
          violations: [
            {
              code: "ACCESSIBILITY_HARD_VIOLATION",
              severity: 4,
              hard: true,
              message:
                "Participant P0105 requires a Ground Floor wheelchair-accessible bed. Target room is on Floor 1 without elevator.",
            },
          ],
          relaxed_soft_constraints: [],
        },
        meta: {},
        warnings: [],
      });
    }

    return HttpResponse.json({
      data: {
        allowed: true,
        is_hard_violation: false,
        violations: [],
        relaxed_soft_constraints: [
          {
            code: "CONTINGENT_COHESION",
            message: "Target bed is on the same floor as contingent leader Rohan Deshmukh.",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/accommodation/assign", async ({ request }) => {
    const body = (await request.json()) as any;
    if (body.simulate_conflict || body.expected_version === 999) {
      return HttpResponse.json(
        {
          error: {
            code: "VERSION_CONFLICT",
            message: "This bed was assigned or updated concurrently by another coordinator. Please refresh the occupancy map.",
            request_id: "req_conflict_409",
          },
        },
        { status: 409 }
      );
    }

    return HttpResponse.json({
      data: {
        change_set_id: `cs_accom_${Date.now()}`,
        status: "APPLIED",
        assignment: {
          participant_id: body.payload?.participant_id || "P0102",
          bed_id: body.payload?.target_bed_id || "H3-101-B",
          assigned_at: new Date().toISOString(),
          assigned_by: "ACCOMMODATION_LEAD",
        },
        why_card: {
          id: `why_assign_${Date.now()}`,
          subject: `Bed Assignment: ${body.payload?.participant_id} -> ${body.payload?.target_bed_id}`,
          recommendation: "Assigned within contingent cluster while respecting floor accessibility bounds.",
          hard_satisfied: !body.payload?.override_hard_constraint,
          soft_relaxed: [
            {
              constraint: "Contingent Proximity",
              reason: body.reason || "Operational manual placement",
            },
          ],
          alternatives_rejected: [
            { option: "Hostel 3 Wing A Floor 2", why: "Splits contingent peers across separate wings" },
            { option: "Hotel Radisson Rau", why: "Incurs external hotel cost when on-campus bed is vacant" },
          ],
          cost_impact: 0,
          people_affected: 1,
          approved_by: body.payload?.override_hard_constraint ? "FESTIVAL_DIRECTOR" : "ACCOMMODATION_LEAD",
          created_at: new Date().toISOString(),
        },
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/accommodation/commit-live", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        plan_id: body.plan_id || "plan_C_balanced",
        status: "LIVE",
        committed_at: new Date().toISOString(),
        committed_by: "FESTIVAL_DIRECTOR",
        reason: body.reason,
      },
      meta: {},
      warnings: [],
    });
  }),

  // Check-in Desk Endpoints
  http.get("*/api/v1/checkin/board", () => {
    return HttpResponse.json({
      data: {
        counts: {
          pending_count: 2180,
          arrived_count: 42,
          checked_in_count: 594,
          late_arrivals_count: 18,
        },
        late_arrivals: [
          {
            participant_id: "P0412",
            name: "Aditya Verma",
            college: "BITS Pilani",
            contingent_id: "C08",
            flight_pnr: "6E-204",
            expected_arrival: "2026-10-30T18:00:00Z",
            delay_minutes: 150,
            is_curfew_breach: true,
            notes: "Late night arrival past 22:00 campus gate curfew",
          },
          {
            participant_id: "P0582",
            name: "Meera Nair",
            college: "IIT Madras",
            contingent_id: "C12",
            flight_pnr: "AI-402",
            expected_arrival: "2026-10-30T19:30:00Z",
            delay_minutes: 90,
            is_curfew_breach: false,
            notes: "Flight delayed at BOM",
          },
        ],
        recent_checkins: [
          {
            participant_id: "P0102",
            name: "Aarav Sharma",
            college: "IIT Bombay",
            room_number: "H3-101",
            checked_in_at: "2026-10-30T10:15:00Z",
            volunteer: "Dr. Devashish Roy",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/checkin/participant/:id", ({ params }) => {
    const id = params.id as string;
    return HttpResponse.json({
      data: {
        participant: {
          id: id || "P0102",
          name: id === "P0104" ? "Sneha Mukherjee" : "Aarav Sharma",
          contingent_id: "C05",
          college: "IIT Bombay",
          role: id === "P0103" ? "LEADER" : "PARTICIPANT",
          status: "EXPECTED",
          gender: id === "P0104" ? "UNKNOWN" : "Male",
          age: 21,
          is_minor: false,
          diet: "UNKNOWN",
          accommodation_requested: "YES",
        },
        room_assignment: {
          bed_id: "H3-101-A",
          room_number: "101",
          building: "Hostel 3 (Wing B)",
          floor: 0,
          cleaning_status: "READY",
          cleaning_ready_at: "2026-10-30T09:00:00Z",
          is_accessible: true,
        },
        alerts: {
          accessibility: "Requires Ground Floor Bed (Wheelchair ramp verified)",
          diet: "Diet is UNKNOWN (Prompt for quick verification at desk)",
          safety: null,
        },
        unknown_prompts: [
          {
            field: "diet",
            prompt: "Select dietary category for meal token provisioning",
            options: ["VEG", "NON_VEG", "JAIN"],
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/checkin/verify-arrival", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        participant_id: body.participant_id || "P0102",
        status: "CHECKED_IN",
        checked_in_at: new Date().toISOString(),
        room_key_released: true,
        merch_eligible: true,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/checkin/checkout", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        participant_id: body.participant_id || "P0102",
        status: "CHECKED_OUT",
        bed_id: body.bed_id || "H3-101-A",
        room_status: "CLEANING",
        cleaning_buffer_minutes: 180,
        cleaning_expected_ready_at: new Date(Date.now() + 180 * 60 * 1000).toISOString(),
      },
      meta: {},
      warnings: [],
    });
  }),

  // PWA Check-in Offline Batch Sync endpoint
  http.post("*/api/v1/checkin/sync", async ({ request }) => {
    const body = (await request.json()) as any;
    const ops = body?.operations || [];
    const results = ops.map((op: any, index: number) => {
      // If op is second or matches duplicate pattern, mark DUPLICATE_IGNORED
      if (index === 1 || op.participant_id === "P0103_DUP") {
        return {
          client_op_id: op.client_op_id,
          status: "DUPLICATE_IGNORED",
          message: `Duplicate check-in ignored for participant ${op.participant_id || "P0103"} (already verified on server).`,
        };
      }
      return {
        client_op_id: op.client_op_id,
        status: "APPLIED",
        message: `Check-in verified cleanly for participant ${op.participant_id || "P0102"}.`,
      };
    });
    return HttpResponse.json({
      device_id: body.device_id,
      results,
    });
  }),

  // --- EVENTS & VENUES & SCHEDULE ---
  http.get("*/api/v1/events", ({ request }) => {
    const url = new URL(request.url);
    const q = url.searchParams.get("q")?.toLowerCase();
    const items = [
      {
        id: "E01",
        name: "Aarohan Vocals Solo",
        solo_team: "SOLO",
        rounds: 3,
        rounds_text: "prelims|semis|finals",
        duration_min: 90,
        venue_requirements: "stage; audio; seating",
        equipment_needs: "microphones; audio mixer; cables",
        volunteers_needed: 6,
        judges_needed: 2,
        registrations_count: 142,
        status: "ACTIVE",
      },
      {
        id: "E02",
        name: "Battle of the Bands",
        solo_team: "TEAM",
        rounds: 2,
        rounds_text: "prelims|finals",
        duration_min: 120,
        venue_requirements: "stage; audio; power",
        equipment_needs: "drum kit; amplifiers; audio mixer",
        volunteers_needed: 10,
        judges_needed: 3,
        registrations_count: 28,
        status: "ACTIVE",
      },
      {
        id: "E03",
        name: "Case Clash",
        solo_team: "TEAM",
        rounds: 3,
        rounds_text: "prelims|semis|finals",
        duration_min: 120,
        venue_requirements: "power; tables; projector",
        equipment_needs: "projector; extension cords",
        volunteers_needed: 8,
        judges_needed: 3,
        registrations_count: 48,
        status: "ACTIVE",
      },
      {
        id: "E04",
        name: "Street Play (Nukkad Natak)",
        solo_team: "TEAM",
        rounds: 1,
        rounds_text: "single",
        duration_min: 90,
        venue_requirements: "open ground",
        equipment_needs: "barricades; megaphone",
        volunteers_needed: 12,
        judges_needed: 2,
        registrations_count: 18,
        status: "ACTIVE",
      },
      {
        id: "E05",
        name: "Choreo Night",
        solo_team: "TEAM",
        rounds: 2,
        rounds_text: "prelims|finals",
        duration_min: 150,
        venue_requirements: "stage; lights; audio",
        equipment_needs: "lighting rigs; smoke machine; wireless mics",
        volunteers_needed: 15,
        judges_needed: 4,
        registrations_count: 32,
        status: "ACTIVE",
      },
    ];

    const filtered = q
      ? items.filter((it) => it.name.toLowerCase().includes(q) || it.id.toLowerCase().includes(q))
      : items;

    return HttpResponse.json({
      data: {
        items: filtered,
        total: filtered.length,
        page: 1,
        page_size: 50,
        total_pages: 1,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.put("*/api/v1/events/:id", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        id,
        status: "UPDATED",
        ...body,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/venues", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "V01",
            name: "Main Auditorium",
            capacity: 650,
            indoor_outdoor: "indoor",
            accessible: true,
            setup_time_min: 20,
            teardown_time_min: 20,
            feature_tags: ["stage", "audio", "lights", "air conditioned"],
            availability_windows: "08:00-23:00",
            status: "AVAILABLE",
          },
          {
            id: "V02",
            name: "Management Hall 1",
            capacity: 180,
            indoor_outdoor: "indoor",
            accessible: true,
            setup_time_min: 15,
            teardown_time_min: 15,
            feature_tags: ["projector", "power", "seating", "quiet room"],
            availability_windows: "08:00-22:00",
            status: "AVAILABLE",
          },
          {
            id: "V03",
            name: "Management Hall 2",
            capacity: 180,
            indoor_outdoor: "indoor",
            accessible: true,
            setup_time_min: 15,
            teardown_time_min: 15,
            feature_tags: ["projector", "power", "seating"],
            availability_windows: "08:00-22:00",
            status: "AVAILABLE",
          },
          {
            id: "V04",
            name: "Amphitheatre",
            capacity: 450,
            indoor_outdoor: "outdoor",
            accessible: true,
            setup_time_min: 25,
            teardown_time_min: 25,
            feature_tags: ["open ground", "stage", "seating", "audio"],
            availability_windows: "09:00-23:00",
            status: "AVAILABLE",
          },
          {
            id: "V05",
            name: "Sports Complex Plaza",
            capacity: 350,
            indoor_outdoor: "outdoor",
            accessible: false,
            setup_time_min: 15,
            teardown_time_min: 15,
            feature_tags: ["open ground", "power"],
            availability_windows: "08:00-20:00",
            status: "AVAILABLE",
          },
        ],
        total: 5,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.put("*/api/v1/venues/:id", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        id,
        status: "UPDATED",
        ...body,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/venues/compatibility", () => {
    return HttpResponse.json({
      data: {
        mapping: {
          "stage; audio; seating": ["V01", "V04"],
          "stage; audio; power": ["V01", "V04"],
          "power; tables; projector": ["V02", "V03"],
          "open ground": ["V04", "V05"],
          "stage; lights; audio": ["V01"],
        },
        status: "ASSUMED",
        notes: "Derived from prototype requirements mapping; editable by Event Lead.",
      },
      meta: {},
      warnings: ["Venue-event compatibility is ASSUMED because raw dataset contains no explicit venue assignments."],
    });
  }),

  http.put("*/api/v1/venues/compatibility", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        status: "UPDATED",
        requirement_key: body.requirement_key,
        venue_ids: body.venue_ids,
        reason: body.reason,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/schedule/timeline", () => {
    return HttpResponse.json({
      data: {
        status: "ASSUMED",
        venues: [
          {
            venue_id: "V01",
            venue_name: "Main Auditorium",
            blocks: [
              {
                session_id: "ses_001",
                event_id: "E01",
                event_name: "Aarohan Vocals Solo",
                round: "prelims",
                heat: "Heat 1",
                start: "2026-10-31T09:00:00Z",
                end: "2026-10-31T10:30:00Z",
                setup_start: "2026-10-31T08:45:00Z",
                teardown_end: "2026-10-31T10:45:00Z",
                entrants_count: 45,
                judges_assigned: 1,
                judges_needed: 2,
                judge_gap: true,
                status: "ASSUMED",
              },
              {
                session_id: "ses_002",
                event_id: "E02",
                event_name: "Battle of the Bands",
                round: "prelims",
                heat: "Heat 1",
                start: "2026-10-31T11:15:00Z",
                end: "2026-10-31T13:15:00Z",
                setup_start: "2026-10-31T10:55:00Z",
                teardown_end: "2026-10-31T13:35:00Z",
                entrants_count: 14,
                judges_assigned: 3,
                judges_needed: 3,
                judge_gap: false,
                status: "ASSUMED",
              },
            ],
          },
          {
            venue_id: "V02",
            venue_name: "Management Hall 1",
            blocks: [
              {
                session_id: "ses_003",
                event_id: "E03",
                event_name: "Case Clash",
                round: "prelims",
                heat: "Track A",
                start: "2026-10-31T09:30:00Z",
                end: "2026-10-31T11:30:00Z",
                setup_start: "2026-10-31T09:15:00Z",
                teardown_end: "2026-10-31T11:45:00Z",
                entrants_count: 24,
                judges_assigned: 2,
                judges_needed: 3,
                judge_gap: true,
                status: "ASSUMED",
              },
            ],
          },
          {
            venue_id: "V04",
            venue_name: "Amphitheatre",
            blocks: [
              {
                session_id: "ses_004",
                event_id: "E04",
                event_name: "Street Play (Nukkad Natak)",
                round: "single",
                heat: "Round 1",
                start: "2026-10-31T10:00:00Z",
                end: "2026-10-31T11:30:00Z",
                setup_start: "2026-10-31T09:35:00Z",
                teardown_end: "2026-10-31T11:55:00Z",
                entrants_count: 18,
                judges_assigned: 2,
                judges_needed: 2,
                judge_gap: false,
                status: "ASSUMED",
              },
            ],
          },
        ],
      },
      meta: {
        benchmark: "172 prototype sessions generated; labelled ASSUMED",
      },
      warnings: ["Schedule is labelled ASSUMED. Raw data contains no event times or venue assignments."],
    });
  }),

  // Conflict list and resolutions
  http.get("*/api/v1/schedule/conflicts", () => {
    return HttpResponse.json({
      data: {
        total: 10,
        items: [
          {
            id: "cfl_01",
            conflict_type: "PARTICIPANT_CLASH",
            severity: 4,
            status: "OPEN",
            description: "Participant P0042 (Aarav Sharma) double-booked between E01 Heat M1 (09:00-10:30) and E03 Track A (09:30-11:30)",
            people_affected: 1,
            entity_refs: { participant_id: "P0042", session_a: "ses_001", session_b: "ses_003" },
          },
          {
            id: "cfl_02",
            conflict_type: "VENUE_DOUBLE_BOOKING",
            severity: 4,
            status: "OPEN",
            description: "Main Auditorium (V01) assigned to two concurrent sessions: ses_001 and ses_099",
            people_affected: 59,
            entity_refs: { venue_id: "V01", session_a: "ses_001", session_b: "ses_099" },
          },
          {
            id: "cfl_03",
            conflict_type: "JUDGE_DOUBLE_BOOKING",
            severity: 3,
            status: "OPEN",
            description: "Judge J04 (Dr. K. Verma) assigned concurrently to E01 in V01 and E05 in V04",
            people_affected: 45,
            entity_refs: { judge_id: "J04", session_a: "ses_001", session_b: "ses_005" },
          },
          {
            id: "cfl_04",
            conflict_type: "TEARDOWN_SETUP_OVERLAP",
            severity: 3,
            status: "OPEN",
            description: "Teardown of ses_001 ends at 10:45 but setup of ses_002 begins at 10:40 (5m overlap)",
            people_affected: 20,
            entity_refs: { venue_id: "V01", session_a: "ses_001", session_b: "ses_002" },
          },
          {
            id: "cfl_05",
            conflict_type: "TRAVEL_TIME_INSUFFICIENT",
            severity: 3,
            status: "OPEN",
            description: "Contingent C05 has only 5m transition between V01 and V05 (minimum travel time 15m required)",
            people_affected: 18,
            entity_refs: { contingent_id: "C05", from_venue: "V01", to_venue: "V05" },
          },
          {
            id: "cfl_06",
            conflict_type: "ROUND_DEPENDENCY_TIMING",
            severity: 3,
            status: "OPEN",
            description: "Semis scheduled before prelims results compilation buffer (60m required)",
            people_affected: 32,
            entity_refs: { event_id: "E01", prelim_session: "ses_001", semi_session: "ses_012" },
          },
          {
            id: "cfl_07",
            conflict_type: "ARRIVAL_WINDOW_BREACH",
            severity: 2,
            status: "OPEN",
            description: "Heat scheduled at 08:30 for participants arriving at 09:15 train",
            people_affected: 12,
            entity_refs: { session_id: "ses_001", contingent_id: "C12" },
          },
          {
            id: "cfl_08",
            conflict_type: "CAPACITY_EXCEEDED",
            severity: 2,
            status: "OPEN",
            description: "Registration count (195) exceeds Management Hall 1 seated capacity (180)",
            people_affected: 15,
            entity_refs: { venue_id: "V02", session_id: "ses_003" },
          },
          {
            id: "cfl_09",
            conflict_type: "EQUIPMENT_UNAVAILABLE",
            severity: 2,
            status: "OPEN",
            description: "High-power audio rig reserved simultaneously by ses_002 and ses_004",
            people_affected: 30,
            entity_refs: { equipment_id: "itm_audio_01" },
          },
          {
            id: "cfl_10",
            conflict_type: "ACCESSIBILITY_UNMET",
            severity: 4,
            status: "OPEN",
            description: "Participant requiring wheelchair access scheduled in non-accessible venue V05",
            people_affected: 1,
            entity_refs: { participant_id: "P0291", venue_id: "V05" },
          },
        ],
      },
      meta: {
        types_checked: 10,
        open_conflicts: 10,
      },
      warnings: ["Zero venue overlaps does not mean zero conflicts: all 10 types are checked."],
    });
  }),

  http.get("*/api/v1/schedule/conflicts/:id/resolutions", ({ params }) => {
    const id = params.id as string;
    return HttpResponse.json({
      data: {
        conflict_id: id,
        recommendations: [
          {
            id: "res_01",
            rank: 1,
            action: "schedule.move_session",
            rationale: "Shift ses_003 (Case Clash) start to 11:45 after ses_001 teardown and buffer",
            conflicts_resolved: 2,
            new_conflicts_created: 0,
            people_affected: 24,
            suggested_start_at: "2026-10-31T11:45:00Z",
            suggested_venue_id: "V02",
          },
          {
            id: "res_02",
            rank: 2,
            action: "schedule.change_venue",
            rationale: "Reassign ses_003 to V03 (Management Hall 2) to eliminate venue contention",
            conflicts_resolved: 1,
            new_conflicts_created: 0,
            people_affected: 24,
            suggested_start_at: "2026-10-31T09:30:00Z",
            suggested_venue_id: "V03",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/schedule/conflicts/:id/apply-resolution", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        status: "APPLIED",
        conflict_id: id,
        applied_action: body.action || "schedule.move_session",
        reason: body.reason || "Applied ranked resolution candidate",
        change_set_id: "cs_sch_res_881",
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/schedule/unscheduled", () => {
    return HttpResponse.json({
      data: {
        total_registrations: 5580,
        scheduled_count: 4593,
        unscheduled_count: 987,
        unplaced_later_round_sessions: 28,
        reasons_breakdown: {
          NOT_ON_SITE_LONG_ENOUGH: 412,
          NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH: 575,
        },
        items: [
          {
            participant_id: "P0012",
            participant_name: "Karan Patel",
            event_id: "E05",
            event_name: "Choreo Night",
            contingent_id: "C02",
            contingent_name: "BITS Pilani",
            reason: "NOT_ON_SITE_LONG_ENOUGH",
            arrival_datetime: "2026-10-31T22:00:00Z",
            departure_datetime: "2026-11-01T14:00:00Z",
            alternatives: ["Request arrival extension", "Schedule in Late-Arrival Wave L1"],
          },
          {
            participant_id: "P0088",
            participant_name: "Sneha Reddy",
            event_id: "E01",
            event_name: "Aarohan Vocals Solo",
            contingent_id: "C09",
            contingent_name: "St. Xavier's",
            reason: "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH",
            arrival_datetime: "2026-10-31T08:00:00Z",
            departure_datetime: "2026-11-02T18:00:00Z",
            alternatives: ["Add supplementary heat M3", "Wildcard finals entry"],
          },
          {
            participant_id: "P0145",
            participant_name: "Rahul Verma",
            event_id: "E03",
            event_name: "Case Clash",
            contingent_id: "C14",
            contingent_name: "IIM Ahmedabad",
            reason: "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH",
            arrival_datetime: "2026-10-31T10:00:00Z",
            departure_datetime: "2026-11-02T16:00:00Z",
            alternatives: ["Reassign to Track B in V03", "Split slot into 2 heats"],
          },
        ],
      },
      meta: {
        prototype_benchmark: "987 unscheduled registrations tracked transparently",
      },
      warnings: ["Never silently drop participants: all 987 unscheduled registrations are tracked with explanations."],
    });
  }),

  http.get("*/api/v1/schedule/versions", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "sch_v1_0",
            plan_name: "Plan Alpha (Greedy Graph Clustered)",
            status: "ASSUMED",
            sessions_count: 172,
            conflicts_count: 10,
            unscheduled_count: 987,
            created_at: "2026-10-30T09:00:00Z",
            created_by: "EVENT_LEAD",
            is_active: true,
          },
          {
            id: "sch_v0_9",
            plan_name: "Plan Baseline (Sequential Heuristic)",
            status: "ARCHIVED",
            sessions_count: 154,
            conflicts_count: 24,
            unscheduled_count: 1102,
            created_at: "2026-10-29T18:00:00Z",
            created_by: "EVENT_LEAD",
            is_active: false,
          },
        ],
        total: 2,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/schedule/versions/:id/restore", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        status: "APPLIED",
        restored_version_id: id,
        reason: body.reason || "Restored schedule version",
        change_set_id: "cs_sch_rst_109",
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/schedule/fairness-decisions", () => {
    return HttpResponse.json({
      data: {
        decisions: [
          {
            id: "dec_late_wave",
            title: "Late Arrival Wave on Nov 1 Morning",
            type: "LATE_WAVE",
            status: "PENDING_APPROVAL",
            requires_role: "FESTIVAL_DIRECTOR",
            affected_participants: 138,
            reason: "13% of registered contingents arrive late night Oct 31 due to train delays.",
            action_route: "/approvals",
          },
          {
            id: "dec_wildcard_finals",
            title: "Wildcard Slot in Aarohan Vocals Finals",
            type: "WILDCARD_FINALS",
            status: "PENDING_APPROVAL",
            requires_role: "FESTIVAL_DIRECTOR",
            affected_participants: 1,
            reason: "Top scorer from prelims had emergency transport breakdown.",
            action_route: "/approvals",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  // --- LOGISTICS & EQUIPMENT ---
  http.get("*/api/v1/logistics/items", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "itm_cam_01",
            name: "Camera (DSLR 4K Media)",
            code: "L13-1",
            kind: "equipment",
            condition: "UNDER_REPAIR",
            location_id: "loc_reg_desk",
            location_name: "Registration Desk Store",
            on_hand: 31,
            reserved: 0,
            in_transit: 0,
            damaged: 0,
            under_repair: 31,
            awaiting_return: 0,
            available: 0,
            low_stock_threshold: 3,
          },
          {
            id: "itm_mic_01",
            name: "Wireless Handheld Microphone",
            code: "EQ-MIC-01",
            kind: "equipment",
            condition: "GOOD",
            location_id: "loc_store_a",
            location_name: "Central Store A",
            on_hand: 40,
            reserved: 12,
            in_transit: 4,
            damaged: 2,
            under_repair: 0,
            awaiting_return: 2,
            available: 20,
            low_stock_threshold: 10,
          },
          {
            id: "itm_tab_01",
            name: "Folding Conference Table (6ft)",
            code: "EQ-TAB-02",
            kind: "equipment",
            condition: "NEEDS_CHECK",
            location_id: "loc_sports_complex",
            location_name: "Sports Complex",
            on_hand: 42,
            reserved: 20,
            in_transit: 0,
            damaged: 0,
            under_repair: 0,
            awaiting_return: 0,
            available: 22,
            low_stock_threshold: 15,
          },
          {
            id: "itm_proj_01",
            name: "HDMI Laser Projector (5000 Lumens)",
            code: "EQ-PRJ-01",
            kind: "equipment",
            condition: "GOOD",
            location_id: "loc_main_auditorium",
            location_name: "Main Auditorium",
            on_hand: 12,
            reserved: 8,
            in_transit: 1,
            damaged: 1,
            under_repair: 0,
            awaiting_return: 0,
            available: 2,
            low_stock_threshold: 4,
          },
          {
            id: "itm_barr_01",
            name: "Crowd Control Barricade",
            code: "EQ-BAR-01",
            kind: "equipment",
            condition: "GOOD",
            location_id: "loc_sports_complex",
            location_name: "Sports Complex",
            on_hand: 100,
            reserved: 40,
            in_transit: 20,
            damaged: 5,
            under_repair: 0,
            awaiting_return: 0,
            available: 35,
            low_stock_threshold: 25,
          },
        ],
        total: 5,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/logistics/locations", () => {
    return HttpResponse.json({
      data: {
        locations: [
          { id: "loc_store_a", name: "Central Store A", building: "Administrative Block", items_count: 240 },
          { id: "loc_reg_desk", name: "Registration Desk Store", building: "Welcome Centre", items_count: 145 },
          { id: "loc_main_auditorium", name: "Main Auditorium Backstage", building: "Auditorium", items_count: 85 },
          { id: "loc_sports_complex", name: "Sports Complex Ground", building: "Sports Complex", items_count: 190 },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/logistics/transfers", () => {
    return HttpResponse.json({
      data: {
        transfers: [
          {
            id: "trf_001",
            item_id: "itm_mic_01",
            item_name: "Wireless Handheld Microphone",
            quantity: 4,
            from_location_id: "loc_store_a",
            from_location_name: "Central Store A",
            to_location_id: "loc_main_auditorium",
            to_location_name: "Main Auditorium Backstage",
            vehicle: "Utility Van 1",
            status: "IN_TRANSIT",
            eta: "2026-10-31T10:45:00Z",
            minutes_remaining: 12,
          },
          {
            id: "trf_002",
            item_id: "itm_barr_01",
            item_name: "Crowd Control Barricade",
            quantity: 20,
            from_location_id: "loc_store_a",
            from_location_name: "Central Store A",
            to_location_id: "loc_sports_complex",
            to_location_name: "Sports Complex Ground",
            vehicle: "Electric Buggy 2",
            status: "IN_TRANSIT",
            eta: "2026-10-31T11:00:00Z",
            minutes_remaining: 27,
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/logistics/transfers/:id/complete", async ({ params }) => {
    const id = params.id as string;
    return HttpResponse.json({
      data: {
        transfer_id: id,
        status: "COMPLETED",
        completed_at: new Date().toISOString(),
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/logistics/movements", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "mvt_001",
            item_id: "itm_mic_01",
            item_name: "Wireless Handheld Microphone",
            movement_type: "TRANSFER_OUT",
            from_location: "Central Store A",
            to_location: "Main Auditorium Backstage",
            quantity: 4,
            actor: "LOGISTICS_MANAGER",
            reason: "Transfer for soundcheck in Auditorium",
            created_at: "2026-10-31T09:30:00Z",
          },
          {
            id: "mvt_002",
            item_id: "itm_proj_01",
            item_name: "HDMI Laser Projector",
            movement_type: "DAMAGE",
            from_location: "Main Auditorium Backstage",
            to_location: null,
            quantity: 1,
            actor: "LOGISTICS_MANAGER",
            reason: "Bulb burnt out during trial",
            created_at: "2026-10-31T08:15:00Z",
          },
          {
            id: "mvt_003",
            item_id: "itm_barr_01",
            item_name: "Crowd Control Barricade",
            movement_type: "RECEIVE",
            from_location: "External Supplier",
            to_location: "Central Store A",
            quantity: 100,
            actor: "LOGISTICS_MANAGER",
            reason: "Vendor delivery batch 1",
            created_at: "2026-10-30T14:00:00Z",
          },
        ],
        total: 3,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/logistics/equipment/find", ({ request }) => {
    const url = new URL(request.url);
    const itemName = url.searchParams.get("item_name") || "projector";
    return HttpResponse.json({
      data: {
        item_name: itemName,
        venue_id: "V01",
        quantity_needed: 1,
        available_on_site: [
          {
            item_id: "itm_proj_01",
            location_id: "loc_main_auditorium",
            available_units: 2,
          },
        ],
        transfer_needed: [
          {
            item_id: "itm_proj_backup",
            source_location_id: "loc_store_a",
            source_location_name: "Central Store A",
            available_units: 6,
            travel_time_min: 15,
            transfer_duration_min: 15,
            feasible: true,
            latest_departure: "2026-10-31T10:00:00Z",
          },
        ],
        shortage: 0,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/logistics/reconciliation-flags", () => {
    return HttpResponse.json({
      data: {
        flags: [
          {
            code: "CAMERA_ALL_UNDER_REPAIR",
            item: "camera",
            needed: 3,
            available_good: 0,
            total_under_repair: 31,
            severity: "HIGH",
            message: "All 31 cameras across 4 locations are logged as 'under repair'; 3 needed for Media Coverage.",
            action_label: "Inspect Cameras / Reconcile",
          },
          {
            code: "TABLES_NEEDS_CHECK",
            item: "table",
            location: "Sports Complex",
            quantity: 42,
            condition: "needs check",
            severity: "MEDIUM",
            message: "42 tables in Sports Complex flagged 'needs check'; physical condition unverified before morning session.",
            action_label: "Verify Physical Condition",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/logistics/stocktake", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        status: "APPLIED",
        item_id: body.item_id || "itm_cam_01",
        delta: body.delta || 0,
        new_on_hand: body.counted_quantity || 31,
        reason: body.reason || "Physical count reconciled",
      },
      meta: {},
      warnings: [],
    });
  }),

  // --- MERCHANDISE & COUNTER MODE ---
  http.get("*/api/v1/merchandise/catalog", () => {
    return HttpResponse.json({
      data: {
        items: [
          { id: "mch_tshirt_s", name: "Festival T-shirt (Size S)", size: "S", on_hand: 449, reserved: 20, available: 429, is_per_head: true },
          { id: "mch_tshirt_m", name: "Festival T-shirt (Size M)", size: "M", on_hand: 115, reserved: 15, available: 100, is_per_head: true },
          { id: "mch_tshirt_l", name: "Festival T-shirt (Size L)", size: "L", on_hand: 234, reserved: 30, available: 204, is_per_head: true },
          { id: "mch_tshirt_xl", name: "Festival T-shirt (Size XL)", size: "XL", on_hand: 713, reserved: 29, available: 684, is_per_head: true },
          { id: "mch_tshirt_xxl", name: "Festival T-shirt (Size XXL)", size: "XXL", on_hand: 136, reserved: 10, available: 126, is_per_head: true },
          { id: "mch_id_card", name: "Accreditation ID Badge", size: "NA", on_hand: 3200, reserved: 100, available: 3100, is_per_head: true },
          { id: "mch_lanyard", name: "Fest Lanyard", size: "NA", on_hand: 3200, reserved: 100, available: 3100, is_per_head: true },
          { id: "mch_tote", name: "Festival Tote Bag", size: "NA", on_hand: 2900, reserved: 150, available: 2750, is_per_head: true },
        ],
        total: 8,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/merchandise/policy", () => {
    return HttpResponse.json({
      data: {
        policy_name: "Standard Fest Entitlement Baseline",
        is_editable: true,
        rules: [
          { item: "T-shirt", entitlement: "1 per canonical participant", per_head: true },
          { item: "ID card", entitlement: "1 per canonical participant", per_head: true },
          { item: "lanyard", entitlement: "1 per canonical participant", per_head: true },
          { item: "tote", entitlement: "1 per canonical participant", per_head: true },
          { item: "winner medal", entitlement: "Event result allocation only", per_head: false },
        ],
        size_breakdown: {
          S: { demand: 435, stock: 449, net: 14, shortage_alert: false },
          M: { demand: 850, stock: 115, net: -735, shortage_alert: true },
          L: { demand: 620, stock: 234, net: -386, shortage_alert: true },
          XL: { demand: 680, stock: 713, net: 33, shortage_alert: false },
          XXL: { demand: 110, stock: 136, net: 26, shortage_alert: false },
          UNKNOWN: { count: 141, flag: "NEEDS_SIZE_COLLECTION" },
        },
      },
      meta: {
        note: "Shortages depend on the entitlement policy (1 per verified canonical participant). Demand shifts if policy is relaxed.",
      },
      warnings: ["Critical stock shortage detected in sizes M (-735) and L (-386)."],
    });
  }),

  http.get("*/api/v1/merchandise/history", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            claim_id: "clm_001",
            participant_id: "P0012",
            participant_name: "Karan Patel",
            item_name: "T-shirt (L)",
            counter_id: "counter_north_01",
            issued_by: "usr_vol_01",
            issued_at: "2026-10-31T08:15:30Z",
          },
          {
            claim_id: "clm_002",
            participant_id: "P0088",
            participant_name: "Sneha Reddy",
            item_name: "Accreditation ID & Lanyard",
            counter_id: "counter_south_02",
            issued_by: "usr_vol_02",
            issued_at: "2026-10-31T08:22:10Z",
          },
        ],
        total: 2,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/merchandise/qr/:participant_id", ({ params }) => {
    const id = params.participant_id as string;
    return HttpResponse.json({
      data: {
        participant_id: id,
        token: `hmac_v1_${id}_secure_99`,
        qr_svg: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="#ffffff"/><rect x="10" y="10" width="30" height="30" fill="#000000"/><rect x="60" y="10" width="30" height="30" fill="#000000"/><rect x="10" y="60" width="30" height="30" fill="#000000"/><rect x="45" y="45" width="10" height="10" fill="#000000"/></svg>`,
        entitlements: ["T-shirt", "ID card", "lanyard", "tote"],
      },
      meta: {},
      warnings: [],
    });
  }),

  // Merchandise scan & issue stateful tracker for ALREADY_ISSUED test
  (() => {
    const issuedMap = new Set<string>();

    return http.post("*/api/v1/merchandise/issue", async ({ request }) => {
      const body = (await request.json()) as any;
      const pid = body.participant_id || "P0042";
      const key = `${pid}:${body.item_id || "tshirt"}`;

      if (issuedMap.has(key)) {
        return HttpResponse.json(
          {
            error: {
              code: "ALREADY_ISSUED",
              message: `Item already issued to participant ${pid}`,
              details: {
                claim_id: "clm_prev_882",
                canonical_participant_id: pid,
                claimed_at: "2026-10-31T08:35:10Z",
                counter_id: "counter_north_01",
                issued_by: "usr_vol_01 (Pooja Sharma)",
              },
            },
          },
          { status: 409 }
        );
      }

      issuedMap.add(key);
      return HttpResponse.json({
        data: {
          claim_id: `clm_${Math.random().toString(36).slice(2, 8)}`,
          canonical_participant_id: pid,
          item_id: body.item_id || "mch_tshirt_l",
          item_name: "T-shirt (Size L)",
          status: "ISSUED",
          issued_at: new Date().toISOString(),
          counter_id: body.counter_id || "counter_north_01",
          issued_by: "usr_vol_01 (Pooja Sharma)",
        },
        meta: {},
        warnings: [],
      });
    });
  })(),

  // Scan endpoint with minimal fields only for volunteers
  http.post("*/api/v1/merchandise/scan", async ({ request }) => {
    const body = (await request.json()) as any;
    const token = body.token || "";
    const pid = token.includes("P") ? token.replace(/[^A-Za-z0-9_]/g, "") : "P0042";

    return HttpResponse.json({
      data: {
        valid: true,
        canonical_participant_id: pid,
        name: "Aarav Sharma",
        contingent: "IIT Bombay",
        // Volunteers see minimal fields only - no phone, no accommodation bed, no medical notes
        entitlements: [
          { item: "ID card", status: "ISSUED", claim_id: "clm_01" },
          { item: "lanyard", status: "ISSUED", claim_id: "clm_02" },
          { item: "T-shirt", status: "PENDING", size: "L" },
          { item: "tote", status: "PENDING", size: "NA" },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  // PWA Merchandise Offline Batch Sync endpoint
  http.post("*/api/v1/merchandise/sync", async ({ request }) => {
    const body = (await request.json()) as any;
    const ops = body?.operations || [];
    const results = ops.map((op: any, index: number) => {
      if (op.participant_id === "P0042_CONFLICT" || index === 99) {
        return {
          client_op_id: op.client_op_id,
          status: "CONFLICT",
          message: `Item ${op.item_name} already claimed at Counter South at 10:15 AM.`,
          conflict_details: {
            server_claim_id: "clm_south_991",
            claimed_at: "2026-10-31T10:15:00Z",
            counter: "Counter South",
          },
        };
      }
      return {
        client_op_id: op.client_op_id,
        status: "APPLIED",
        message: `Merchandise ${op.item_name || "T-shirt"} issued to ${op.participant_id}.`,
      };
    });
    return HttpResponse.json({
      device_id: body.device_id,
      results,
    });
  }),

  // AI Command Center Execution Endpoint
  http.post("*/api/v1/commands/execute", async ({ request }) => {
    const body = (await request.json()) as any;
    const isMutating = body?.command?.is_mutating;
    return HttpResponse.json({
      result: {
        success: true,
        summary: isMutating
          ? `Change proposal submitted for approval: ${body?.command?.raw_text || "AI Proposal"}`
          : `Analysis executed for: ${body?.command?.raw_text || "Query"}`,
        items_affected: 42,
        action_route: "/approvals",
        proposal_id: `prop_${Math.random().toString(36).slice(2, 8)}`,
      },
    });
  }),

  // --- VENDORS & FOOD ---
  http.get("*/api/v1/food/coverage", () => {
    return HttpResponse.json({
      data: {
        categories: ["VEG", "NON_VEG", "JAIN", "VEGAN", "GLUTEN_FREE"],
        meal_slots: ["BREAKFAST", "LUNCH", "SNACKS", "DINNER", "LATE_NIGHT"],
        venues: [
          { id: "V01", name: "Main Auditorium" },
          { id: "V04", name: "Amphitheatre" },
          { id: "V05", name: "Sports Complex" },
          { id: "V07", name: "Central Food Court" },
        ],
        matrix: [
          // Amphitheatre Lunch Jain is 0 coverage
          { category: "JAIN", meal_slot: "LUNCH", venue_id: "V04", capacity: 0, demand: 45, deficit: 45, is_zero_coverage: true, vendor_names: [] },
          { category: "VEG", meal_slot: "LUNCH", venue_id: "V04", capacity: 350, demand: 280, deficit: 0, is_zero_coverage: false, vendor_names: ["Annapurna Caterers"] },
          { category: "NON_VEG", meal_slot: "LUNCH", venue_id: "V04", capacity: 200, demand: 150, deficit: 0, is_zero_coverage: false, vendor_names: ["Spice Junction"] },
          { category: "VEGAN", meal_slot: "LUNCH", venue_id: "V04", capacity: 60, demand: 30, deficit: 0, is_zero_coverage: false, vendor_names: ["Green Bowl"] },
          { category: "GLUTEN_FREE", meal_slot: "LUNCH", venue_id: "V04", capacity: 0, demand: 12, deficit: 12, is_zero_coverage: true, vendor_names: [] },
          
          // Food Court Lunch
          { category: "JAIN", meal_slot: "LUNCH", venue_id: "V07", capacity: 180, demand: 110, deficit: 0, is_zero_coverage: false, vendor_names: ["Shanti Rasoi"] },
          { category: "VEG", meal_slot: "LUNCH", venue_id: "V07", capacity: 600, demand: 500, deficit: 0, is_zero_coverage: false, vendor_names: ["Annapurna Caterers", "Food Plaza"] },
          { category: "NON_VEG", meal_slot: "LUNCH", venue_id: "V07", capacity: 400, demand: 320, deficit: 0, is_zero_coverage: false, vendor_names: ["Spice Junction", "Royal Feast"] },
          { category: "VEGAN", meal_slot: "LUNCH", venue_id: "V07", capacity: 100, demand: 45, deficit: 0, is_zero_coverage: false, vendor_names: ["Green Bowl"] },
          { category: "GLUTEN_FREE", meal_slot: "LUNCH", venue_id: "V07", capacity: 50, demand: 20, deficit: 0, is_zero_coverage: false, vendor_names: ["Pure Roots"] },
        ],
        summary: {
          zero_coverage_count: 2,
          critical_alerts: [
            { category: "JAIN", meal_slot: "LUNCH", venue_name: "Amphitheatre", affected: 45 },
            { category: "GLUTEN_FREE", meal_slot: "LUNCH", venue_name: "Amphitheatre", affected: 12 },
          ],
        },
      },
      meta: {},
      warnings: ["Zero-coverage cells detected: immediate vendor slot assignment required."],
    });
  }),

  http.get("*/api/v1/vendors", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "vnd_01",
            name: "Annapurna Caterers",
            status: "ACTIVE",
            dietary_options: "VEG, JAIN",
            menu_description: "North Indian Thali, Dal Baati, Jain Meal, Evening Snacks",
            capacity: 450,
            hours: "07:00-23:00",
            hygiene_certificate_expiry: "2026-11-20",
            days_to_expiry: 21,
            payment_terms: "MINIMUM_GUARANTEE_PLUS_ACTUALS",
            base_rate_per_meal_inr: 180,
            contact_phone: "+91-9876543210",
          },
          {
            id: "vnd_02",
            name: "Spice Junction",
            status: "ACTIVE",
            dietary_options: "VEG, NON_VEG",
            menu_description: "Dum Biryani, Butter Chicken, Paneer Rolls",
            capacity: 350,
            hours: "11:00-02:00",
            hygiene_certificate_expiry: "2026-10-31",
            days_to_expiry: 1,
            payment_terms: "FIXED_PER_MEAL",
            base_rate_per_meal_inr: 220,
            contact_phone: "+91-9812345678",
          },
          {
            id: "vnd_05",
            name: "Royal Feast Caterers",
            status: "ACTIVE",
            dietary_options: "VEG, NON_VEG, JAIN",
            menu_description: "Multi-Cuisine Buffet, Tandoor, Mughlai & Jain Counter",
            capacity: 500,
            hours: "08:00-01:00",
            hygiene_certificate_expiry: "2026-12-15",
            days_to_expiry: 46,
            payment_terms: "FIXED_PER_MEAL",
            base_rate_per_meal_inr: 240,
            contact_phone: "+91-9988776655",
          },
        ],
        total: 3,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/vendors/compliance", () => {
    return HttpResponse.json({
      data: {
        certifications: [
          {
            vendor_id: "vnd_02",
            vendor_name: "Spice Junction",
            certificate_type: "FSSAI Food Hygiene",
            certificate_number: "FSSAI-MP-2024-9982",
            valid_until: "2026-10-31",
            days_left: 1,
            status: "CRITICAL_EXPIRING",
            audit_pass: true,
          },
          {
            vendor_id: "vnd_01",
            vendor_name: "Annapurna Caterers",
            certificate_type: "FSSAI Commercial Catering",
            certificate_number: "FSSAI-MP-2023-1142",
            valid_until: "2026-11-20",
            days_left: 21,
            status: "VALID",
            audit_pass: true,
          },
        ],
        mismatches: [
          {
            id: "flg_mis_01",
            vendor_id: "vnd_02",
            vendor_name: "Spice Junction",
            item_name: "Paneer Butter Masala",
            issue: "Declared 'Jain-Friendly' but recipe contains onion puree.",
            severity: "HIGH",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/vendors/:id/shutdown-impact", ({ params }) => {
    const id = params.id as string;
    return HttpResponse.json({
      data: {
        vendor_id: id,
        vendor_name: "Spice Junction",
        lost_capacity: 350,
        affected_slots: [
          { date: "2026-10-31", meal_slot: "LUNCH", venue_name: "Food Court", meals_deficit: 350 },
          { date: "2026-10-31", meal_slot: "DINNER", venue_name: "Food Court", meals_deficit: 350 },
        ],
        ranked_replacements: [
          {
            vendor_id: "vnd_05",
            vendor_name: "Royal Feast Caterers",
            available_capacity: 500,
            dietary_match: "EXACT (VEG, NON_VEG)",
            proximity_score: 0.95,
            rate_per_meal_inr: 240,
            cost_delta_inr: 7000,
            rank: 1,
            rationale: "Adjacent kitchen with verified 500-meal reserve capacity and active FSSAI clearance.",
          },
          {
            vendor_id: "vnd_01",
            vendor_name: "Annapurna Caterers",
            available_capacity: 250,
            dietary_match: "PARTIAL (VEG only)",
            proximity_score: 0.85,
            rate_per_meal_inr: 180,
            cost_delta_inr: -14000,
            rank: 2,
            rationale: "Lower cost but requires secondary vendor for non-veg allocation.",
          },
        ],
        cost_delta_inr: 7000,
        notification_drafts: [
          {
            id: "not_01",
            recipient_group: "FOOD_OPS_MANAGERS",
            channel: "APP_PUSH",
            subject: "URGENT: Vendor Shutdown Enacted",
            body: "Spice Junction food stall is shut down due to hygiene protocol. Royal Feast Caterers activated.",
            requires_approval: false,
          },
          {
            id: "not_02",
            recipient_group: "AFFECTED_PARTICIPANTS",
            channel: "SMS",
            subject: "Meal Location Update",
            body: "Dining notice: Non-veg and veg meals for Lunch & Dinner are now served at Royal Feast counter.",
            requires_approval: true,
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),

  http.post("*/api/v1/vendors/:id/shutdown", async ({ params, request }) => {
    const id = params.id as string;
    const body = (await request.json()) as any;
    return HttpResponse.json({
      data: {
        status: "APPLIED",
        vendor_id: id,
        new_status: "SHUTDOWN",
        replacement_assigned: body.replacement_vendor_id || "vnd_05",
        reason: body.reason || "Emergency health shutdown",
        change_set_id: "cs_vnd_sht_991",
        notifications_queued: 2,
      },
      meta: {},
      warnings: [],
    });
  }),

  // --- FINANCE & BUDGET OVERVIEW ---
  http.get("*/api/v1/finance/summary", () => {
    return HttpResponse.json({
      data: {
        external_budget_inr: null, // Context: external_budget_inr = NULL
        budget_status: "BUDGET_UNSET",
        budget_explanation: "External accommodation budget is currently UNSET by the Festival Director. Engine is calculating committed spend against unconstrained demand. Festival Director authorization required to lock budget limit.",
        total_spend_committed_inr: 2845000,
        total_spend_projected_inr: 3450000,
        breakdown: {
          external_accommodation_inr: 1618500,
          vendors_and_catering_inr: 780000,
          merchandise_inr: 295000,
          logistics_equipment_inr: 91500,
          approved_emergency_inr: 60000,
        },
      },
      meta: {},
      warnings: ["external_budget_inr is NULL: Operating in budget-unset monitoring mode."],
    });
  }),

  http.get("*/api/v1/finance/accommodation-spend", () => {
    return HttpResponse.json({
      data: {
        properties: [
          {
            property_id: "prop_01",
            name: "Lemon Tree Hotel",
            capacity_beds: 180,
            booked_beds: 160,
            nights: 3,
            rate_per_bed_night_inr: 1800,
            total_spend_inr: 864000,
            contract_status: "CONFIRMED",
            payment_status: "ADVANCE_PAID",
          },
          {
            property_id: "prop_02",
            name: "Ginger Indore",
            capacity_beds: 120,
            booked_beds: 110,
            nights: 3,
            rate_per_bed_night_inr: 1400,
            total_spend_inr: 462000,
            contract_status: "CONFIRMED",
            payment_status: "PARTIAL",
          },
          {
            property_id: "prop_03",
            name: "Royal Palace Residency",
            capacity_beds: 90,
            booked_beds: 75,
            nights: 3,
            rate_per_bed_night_inr: 1300,
            total_spend_inr: 292500,
            contract_status: "PENDING_FINAL_ROOMING",
            payment_status: "PENDING",
          },
        ],
        total_external_spend_inr: 1618500,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/finance/vendor-settlements", () => {
    return HttpResponse.json({
      data: {
        settlements: [
          {
            vendor_id: "vnd_01",
            vendor_name: "Annapurna Caterers",
            contract_total_inr: 280000,
            advance_paid_inr: 100000,
            balance_due_inr: 180000,
            due_date: "2026-11-05",
            status: "PENDING_VERIFICATION",
            dispute: null,
          },
          {
            vendor_id: "vnd_02",
            vendor_name: "Spice Junction",
            contract_total_inr: 195000,
            advance_paid_inr: 80000,
            balance_due_inr: 115000,
            due_date: "2026-11-02",
            status: "DISPUTED",
            dispute: {
              id: "dsp_01",
              amount_inr: 18500,
              reason: "Billed for 120 extra lunch packs during Oct 31 storm delay without authorization token.",
              opened_by: "Finance Manager",
              opened_at: "2026-10-31T15:00:00Z",
            },
          },
        ],
        total_payable_inr: 295000,
        disputed_amount_inr: 18500,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/finance/merchandise-costs", () => {
    return HttpResponse.json({
      data: {
        items: [
          { item_name: "T-shirt", unit_cost_inr: 190, ordered_qty: 2850, total_cost_inr: 541500, supplier: "Aero Apparels", status: "DELIVERED" },
          { item_name: "Accreditation ID & Lanyard", unit_cost_inr: 35, ordered_qty: 3000, total_cost_inr: 105000, supplier: "PrintFast Media", status: "DELIVERED" },
          { item_name: "Festival Tote Bag", unit_cost_inr: 65, ordered_qty: 2850, total_cost_inr: 185250, supplier: "EcoBags India", status: "DELIVERED" },
        ],
        total_merchandise_spend_inr: 831750,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/finance/emergency-spend", () => {
    return HttpResponse.json({
      data: {
        items: [
          {
            id: "emg_01",
            description: "Backup Diesel Generator for Main Auditorium sound rig",
            amount_inr: 35000,
            approved_by: "Festival Director",
            approved_at: "2026-10-31T06:15:00Z",
            reason: "Grid transformer voltage fluctuation threat during Inauguration",
            audit_link: "aud_emg_991",
          },
          {
            id: "emg_02",
            description: "Heavy-duty waterproof tarpaulins for Amphitheatre equipment",
            amount_inr: 25000,
            approved_by: "Festival Director",
            approved_at: "2026-10-31T12:30:00Z",
            reason: "Sudden weather bulletin predicting rain showers",
            audit_link: "aud_emg_992",
          },
        ],
        total_emergency_spend_inr: 60000,
      },
      meta: {},
      warnings: [],
    });
  }),

  http.get("*/api/v1/finance/overrides-report", () => {
    return HttpResponse.json({
      data: {
        overrides: [
          {
            id: "ovr_fin_01",
            category: "BUDGET_OVERRIDE",
            target_entity: "Lemon Tree Hotel (prop_01)",
            original_value: "₹1,500 / bed-night",
            overridden_value: "₹1,800 / bed-night",
            delta_inr: 144000,
            reason: "Rate hike accepted to secure 160 guaranteed beds on fest weekend due to citywide hotel rush.",
            authorized_by: "Festival Director",
            authorized_at: "2026-10-28T14:20:00Z",
            audit_event_id: "aud_ovr_3120",
          },
        ],
      },
      meta: {},
      warnings: [],
    });
  }),
];

import { incidentHandlers } from "./incidents_msw";
import { insightHandlers } from "./insight_msw";

export const server = setupServer(...handlers, ...incidentHandlers, ...insightHandlers);


