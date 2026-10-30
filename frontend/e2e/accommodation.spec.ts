import { test, expect, Page } from "@playwright/test";

async function setupAccommodationMocks(page: Page) {
  await page.route("**/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "healthy", version: "0.1.0", now: "2026-10-30T10:00:00Z" }),
    });
  });

  await page.route("**/api/v1/meta", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        version: "0.1.0",
        now: "2026-10-30T10:00:00Z",
        modules: ["auth", "accommodation", "checkin", "participants"],
        auth_disabled: false,
      }),
    });
  });

  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "mock_director_jwt_token_2026",
        token_type: "bearer",
        user: {
          id: "usr_dir_001",
          email: "director@festos.internal",
          full_name: "Dr. Devashish Roy",
          role: "FESTIVAL_DIRECTOR",
          contingent_id: null,
        },
      }),
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "usr_dir_001",
        email: "director@festos.internal",
        full_name: "Dr. Devashish Roy",
        role: "FESTIVAL_DIRECTOR",
        contingent_id: null,
        permissions: ["*"],
      }),
    });
  });

  // Accommodation Plans
  await page.route("**/api/v1/accommodation/plans", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
        warnings: ["External Accommodation Budget is unset."],
      }),
    });
  });

  // Generate Plan
  await page.route("**/api/v1/accommodation/generate-plan", async (route) => {
    const body = JSON.parse(route.request().postData() || "{}");
    const kind = body.kind || "C";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          plan_id: `plan_${kind}_custom`,
          kind,
          status: "CANDIDATE",
          name: kind === "A" ? "Plan A: Cohesion-First" : kind === "B" ? "Plan B: Cost-First" : "Plan C: Balanced",
          on_campus_placed: 710,
          external_placed: 1310,
          unplaced_count: 120,
          contingent_splits: 7,
          total_cost_inr: 2850000,
          safety_flags_count: 14,
          accessibility_issues_count: 1,
          relaxed_constraints_count: 10,
          sacrifices_summary: "Re-calculated candidate plan with updated parameters.",
          created_at: new Date().toISOString(),
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // Shortages
  await page.route("**/api/v1/accommodation/shortages", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          total_unplaced: 116,
          grouped_by_reason: [
            {
              reason_code: "UNKNOWN_GENDER",
              title: "Gender Unknown (Safety Gate #2)",
              count: 48,
              description: "Room allocation cannot enforce campus hostel gender segregation safety rules.",
              affected_contingents: ["C05", "C08", "C12"],
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
          ],
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // Why-not
  await page.route("**/api/v1/accommodation/why-not/*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          participant_id: "P0104",
          name: "Sneha Mukherjee",
          contingent_id: "C05",
          blocking_requirement: "Rule 2: Gender-Appropriate Allocation & Safety Policy",
          missing_information: "Gender attribute is UNKNOWN in raw import dataset.",
          rejected_options: [
            { location: "Hostel 3 (Wing B)", reason: "Boys hostel block" },
          ],
          counterfactual_impact:
            "If verified as 'Female', 4 beds in Hostel 4 become immediately assignable.",
          verification_target: { field: "gender", entity_id: "P0104" },
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // Occupancy Map
  await page.route("**/api/v1/accommodation/occupancy", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
                          participant_id: "P0103",
                          participant_name: "Rohan Deshmukh",
                          is_leader: true,
                          version: 1,
                        },
                        {
                          bed_id: "H3-101-B",
                          status: "FREE",
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
          ],
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // Check constraints
  await page.route("**/api/v1/accommodation/check-constraints", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          allowed: true,
          is_hard_violation: false,
          violations: [],
          relaxed_soft_constraints: [
            { code: "CONTINGENT_COHESION", message: "Target bed places participant near leader." },
          ],
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // Assign bed with 409 support
  let assignmentAttemptCount = 0;
  await page.route("**/api/v1/accommodation/assign", async (route) => {
    assignmentAttemptCount++;
    const postData = JSON.parse(route.request().postData() || "{}");

    // First attempt hits 409 VERSION_CONFLICT if participant_id is P0104
    if (postData.payload?.participant_id === "P0104" && assignmentAttemptCount === 1) {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "VERSION_CONFLICT",
            message: "Concurrency Conflict: This bed was assigned or modified by another coordinator.",
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          change_set_id: "cs_assigned_100",
          status: "APPLIED",
          why_card: {
            id: "why_assign_100",
            subject: "Bed Assignment: P0104 -> H3-101-B",
            recommendation: "Assigned within contingent cluster.",
            hard_satisfied: true,
            soft_relaxed: [{ constraint: "Contingent Proximity", reason: postData.reason }],
            alternatives_rejected: [],
            cost_impact: 0,
            people_affected: 1,
            approved_by: "FESTIVAL_DIRECTOR",
            created_at: new Date().toISOString(),
          },
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // Checkin board & participant
  await page.route("**/api/v1/checkin/board", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          counts: { pending_count: 2180, arrived_count: 42, checked_in_count: 594, late_arrivals_count: 18 },
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
              notes: "Curfew breach arrival",
            },
          ],
          recent_checkins: [],
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  await page.route("**/api/v1/checkin/participant/*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          participant: {
            id: "P0102",
            name: "Aarav Sharma",
            contingent_id: "C05",
            college: "IIT Bombay",
            role: "LEADER",
            status: "EXPECTED",
            gender: "Male",
            age: 21,
            is_minor: false,
            diet: "UNKNOWN",
            accommodation_requested: "YES",
          },
          room_assignment: {
            bed_id: "H3-101-A",
            room_number: "101",
            building: "Hostel 3",
            floor: 0,
            cleaning_status: "READY",
            cleaning_ready_at: "2026-10-30T09:00:00Z",
            is_accessible: true,
          },
          alerts: {
            accessibility: "Requires Ground Floor Bed",
            diet: "Diet is UNKNOWN",
            safety: null,
          },
          unknown_prompts: [
            { field: "diet", prompt: "Select dietary preference", options: ["VEG", "NON_VEG", "JAIN"] },
          ],
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  await page.route("**/api/v1/checkin/verify-arrival", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          participant_id: "P0102",
          status: "CHECKED_IN",
          checked_in_at: new Date().toISOString(),
          room_key_released: true,
          merch_eligible: true,
        },
        meta: {},
        warnings: [],
      }),
    });
  });
}

async function login(page: Page) {
  await page.goto("/login");
  await page.waitForSelector('[data-testid="login-submit"]');
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL((url) => !url.pathname.includes("/login"));
}

test.describe("Accommodation & Check-in E2E Flow (p3/09-ui-accom)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAccommodationMocks(page);
  });

  test("1. Accommodation Lead compares plans, generates candidate plan, and inspects trade-offs", async ({ page }) => {
    await login(page);
    await page.goto("/accommodation");

    // Verify header and budget banner
    await expect(page.locator("h1")).toContainText("Accommodation Workspace");
    await expect(page.locator('[data-testid="budget-unset-banner"]')).toBeVisible();

    // Verify compare table
    await expect(page.getByText("Side-by-Side Candidate Plan Comparison")).toBeVisible();
    await expect(page.getByText("Plan A: Cohesion-First")).toBeVisible();
    await expect(page.getByText("Plan B: Cost-First")).toBeVisible();
    await expect(page.getByText("Plan C: Balanced (Recommended)")).toBeVisible();

    // Switch to Plan B and run solver
    await page.click('[data-testid="plan-b-btn"]');
    await page.click('[data-testid="generate-plan-btn"]');

    // Verify Recharts trade-off chart
    await expect(page.getByText("Cost-versus-Cohesion Trade-Off Chart")).toBeVisible();
  });

  test("2. Explain unplaced participant with Why-not? diagnosis panel", async ({ page }) => {
    await login(page);
    await page.goto("/accommodation");

    // Click Shortages tab
    await page.click("text=Shortage View");

    // Click Why-not? button for P0104
    await page.waitForSelector('[data-testid="why-not-P0104"]');
    await page.click('[data-testid="why-not-P0104"]');

    // Drawer opens with diagnostic explanation
    await expect(page.getByText("Why-not? Unplaced Diagnosis Panel")).toBeVisible();
    await expect(page.getByText("Rule 2: Gender-Appropriate Allocation & Safety Policy")).toBeVisible();
    await expect(page.getByText("Counterfactual Resolution")).toBeVisible();
  });

  test("3. Manual assign with reason, hit 409 conflict, and recover", async ({ page }) => {
    await login(page);
    await page.goto("/accommodation");

    // Open Manual Move/Assign modal
    await page.click('[data-testid="open-assign-modal-btn"]');
    await expect(page.getByText("Operational Bed Assignment & Constraint Evaluation")).toBeVisible();

    // Fill target participant P0104
    await page.fill('[data-testid="participant-input"]', "P0104");
    await page.fill('[data-testid="bed-input"]', "H3-101-B");

    // Proceed to ConfirmWithReason
    await page.click('[data-testid="proceed-assign-btn"]');
    await expect(page.getByText("Confirm Bed Assignment")).toBeVisible();

    // Enter operational justification
    await page.fill('[data-testid="reason-input"]', "Emergency buffer allocation test");
    await page.click("text=Confirm & Commit Assignment");

    // 1st attempt hits 409 conflict
    await expect(page.locator('[data-testid="conflict-alert"]')).toBeVisible();
    await expect(page.getByText("Concurrency Conflict (409 Version Conflict)")).toBeVisible();

    // Click Refresh & Retry
    await page.click("text=Refresh Occupancy Map & Retry");

    // Retry assignment (2nd attempt succeeds with WhyCard)
    await page.click('[data-testid="proceed-assign-btn"]');
    await page.fill('[data-testid="reason-input"]', "Recovered operational allocation");
    await page.click("text=Confirm & Commit Assignment");

    // Successfully displays WhyCard
    await expect(page.getByText("Assignment Committed to Plan Engine")).toBeVisible();
  });

  test("4. Check-in desk search/scan, dietary verification, and key release", async ({ page }) => {
    await login(page);
    await page.goto("/checkin");

    // Search/scan participant
    await expect(page.locator("h1")).toContainText("Check-in Desk & Reception Terminal");
    await page.fill('[data-testid="checkin-search-input"]', "P0102");
    await page.click('[data-testid="checkin-search-btn"]');

    // Verify room readiness & dietary clearance alert
    await expect(page.locator('[data-testid="participant-desk-card"]')).toBeVisible();
    await expect(page.getByText("ROOM READY FOR KEY RELEASE")).toBeVisible();

    // Verify arrival & release room key
    await page.click('[data-testid="verify-checkin-btn"]');
  });
});
