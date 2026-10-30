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
];

export const server = setupServer(...handlers);

