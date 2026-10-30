import { test, expect, Page } from "@playwright/test";

// Mock helper to intercept backend API calls
async function setupApiMocks(page: Page) {
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
        modules: ["auth", "participants", "contingents", "reconciliation", "unknowns", "approvals"],
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

  await page.route("**/api/v1/participants*", async (route) => {
    const url = route.request().url();
    if (url.includes("/360")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            participant: {
              id: "P0102",
              name: "Aarav Sharma",
              contingent_id: "C05",
              college_name: "IIT Bombay",
              email: "a***@iitb.ac.in",
              phone: "+91 98**** 1234",
              gender: "MALE",
              diet: "UNKNOWN",
              accommodation_requested: true,
              is_contingent_leader: true,
              is_faculty_escort: false,
              arrival_at: "2026-10-31T08:30:00Z",
              departure_at: "2026-11-03T18:00:00Z",
              status: "APPROVED",
              checkin_status: "PENDING",
            },
            events: [
              { id: "EV01", name: "RoboWars", category: "Flagship", venue: "Gymnasium Hall", registered_at: "2026-10-29T10:00:00Z" },
            ],
            accommodation: {
              allocated: true,
              hall_name: "Hostel 4",
              room_number: "204",
              bed_label: "Bed B",
              special_requests: "None",
            },
            merchandise: {
              kit_status: "COLLECTED",
              tshirt_size: "L",
              collected_at: "2026-10-30T09:00:00Z",
              collected_by: "Aarav Sharma",
            },
            transport: {
              mode: "FLIGHT",
              pnr: "6E-481",
              pickup_requested: true,
              pickup_time: "2026-10-31T07:15:00Z",
              drop_requested: true,
            },
            history: [
              { timestamp: "2026-10-30T10:00:00Z", action: "PROFILE_UPDATED", actor: "System Ingest", details: "Initial import" },
            ],
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    if (url.includes("/unmask")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            unmasked_fields: {
              phone: "+91 98765 43210",
              email: "aarav.sharma@iitb.ac.in",
            },
            audit_id: "aud_breakglass_789",
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: [
          {
            id: "P0102",
            name: "Aarav Sharma",
            contingent_id: "C05",
            college_name: "IIT Bombay",
            email: "a***@iitb.ac.in",
            phone: "+91 98**** 1234",
            gender: "MALE",
            diet: "UNKNOWN",
            accommodation_requested: true,
            is_contingent_leader: true,
            is_faculty_escort: false,
            arrival_at: "2026-10-31T08:30:00Z",
            departure_at: "2026-11-03T18:00:00Z",
            status: "APPROVED",
            checkin_status: "PENDING",
          },
          {
            id: "P0103",
            name: "Rhea Sen",
            contingent_id: "C05",
            college_name: "IIT Bombay",
            email: "r***@iitb.ac.in",
            phone: "+91 98**** 5678",
            gender: "FEMALE",
            diet: "VEG",
            accommodation_requested: false,
            is_contingent_leader: false,
            is_faculty_escort: false,
            arrival_at: "2026-10-31T09:00:00Z",
            departure_at: "2026-11-03T20:00:00Z",
            status: "APPROVED",
            checkin_status: "PENDING",
          },
        ],
        meta: { total: 2836, page: 1, size: 25 },
        warnings: [],
      }),
    });
  });

  await page.route("**/api/v1/contingents*", async (route) => {
    const url = route.request().url();
    if (url.includes("/C05/details") || url.includes("/C05")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            id: "C05",
            college_code: "IITB",
            college_name: "IIT Bombay",
            city: "Mumbai",
            state: "Maharashtra",
            declared_strength: 80,
            actual_headcount: 72,
            delta: -8,
            primary_contact_name: "Aarav Sharma",
            primary_contact_phone: "+91 98765 43210",
            primary_contact_email: "leader@iitb.ac.in",
            faculty_escort_name: "Prof. S. Ranganathan",
            faculty_escort_phone: "+91 98111 22334",
            has_missing_leader: false,
            has_missing_escort: false,
            has_strength_mismatch: true,
            status: "CONFIRMED",
            accommodation_breakdown: {
              hostel_4_boys: 45,
              hostel_2_girls: 27,
              split_rationale: "Separated by gender according to institutional guidelines; all housed within Sector 2.",
            },
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: [
          {
            id: "C05",
            college_code: "IITB",
            college_name: "IIT Bombay",
            city: "Mumbai",
            state: "Maharashtra",
            declared_strength: 80,
            actual_headcount: 72,
            delta: -8,
            primary_contact_name: "Aarav Sharma",
            primary_contact_phone: "+91 98765 43210",
            primary_contact_email: "leader@iitb.ac.in",
            faculty_escort_name: "Prof. S. Ranganathan",
            faculty_escort_phone: "+91 98111 22334",
            has_missing_leader: false,
            has_missing_escort: false,
            has_strength_mismatch: true,
            status: "CONFIRMED",
          },
          {
            id: "C01",
            college_code: "IIMB",
            college_name: "IIM Bangalore",
            city: "Bengaluru",
            state: "Karnataka",
            declared_strength: 40,
            actual_headcount: 40,
            delta: 0,
            primary_contact_name: "Karan Gupta",
            primary_contact_phone: "+91 98222 33445",
            primary_contact_email: "karan@iimb.ac.in",
            faculty_escort_name: null,
            faculty_escort_phone: null,
            has_missing_leader: false,
            has_missing_escort: true,
            has_strength_mismatch: false,
            status: "CONFIRMED",
          },
        ],
        meta: { total: 38 },
        warnings: [],
      }),
    });
  });

  await page.route("**/api/v1/reconciliation*", async (route) => {
    const url = route.request().url();
    if (url.includes("/merge")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            merge_id: "mrg_abc12345",
            surviving_id: "P0102",
            absorbed_id: "P0102_DUP",
            merged_at: "2026-10-30T12:00:00Z",
            authorized_by: "Dr. Devashish Roy",
            rationale: "Verified same participant with identical phone",
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    if (url.includes("/waterfall")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            raw_file_count: 2836,
            declared_headcount: 2842,
            narrative_claim: 2400,
            unexplained_remainder: 426,
            resolved_duplicates: 12,
            quarantined_count: 3,
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: [
          {
            id: "dup_0102a",
            confidence_score: 0.94,
            signals: ["IDENTICAL_PHONE", "FUZZY_NAME_MATCH", "SAME_CONTINGENT"],
            candidate_a: {
              id: "P0102",
              name: "Aditya Verma",
              email: "adi.v@iitb.ac.in",
              phone: "+91 98765 43210",
              contingent: "IIT Bombay (C05)",
              registered_events: ["RoboWars", "Hackathon"],
              diet: "VEG",
              accommodation: "YES",
            },
            candidate_b: {
              id: "P0102_DUP",
              name: "A. Verma",
              email: "aditya.verma@gmail.com",
              phone: "+91 98765 43210",
              contingent: "IIT Bombay (C05)",
              registered_events: ["RoboWars"],
              diet: "UNKNOWN",
              accommodation: "YES",
            },
          },
        ],
        meta: { total: 1 },
        warnings: [],
      }),
    });
  });

  await page.route("**/api/v1/unknowns*", async (route) => {
    const url = route.request().url();
    if (url.includes("/verify")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            field: "diet",
            verified_value: "VEG",
            participant_id: "P0001",
            source: "DIRECT_CALL",
            timestamp: "2026-10-30T12:00:00Z",
            operator: "Dr. Devashish Roy",
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    if (url.includes("/token")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            token: "tok_lead_987654321",
            expires_at: "2026-10-31T12:00:00Z",
            contingent_id: "C05",
            contingent_name: "IIT Bombay",
            portal_url: "https://festos.aarohan.org/verify?token=tok_lead_987654321",
          },
          meta: {},
          warnings: [],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: [
          {
            field: "accommodation_requested",
            owner_role: "ACCOMMODATION_LEAD",
            unknown_count: 418,
            criticality_weight: 5,
            impact_score: 2090,
            operational_impact: "Hostel inventory cannot be finalized; risks room double-booking.",
            sample_affected: ["P0002", "P0007"],
          },
          {
            field: "diet",
            owner_role: "FOOD_OPS_MANAGER",
            unknown_count: 512,
            criticality_weight: 4,
            impact_score: 2048,
            operational_impact: "Catering procurement buffer cannot be placed; buffet waste risk.",
            sample_affected: ["P0001", "P0003"],
          },
        ],
        meta: { total: 2 },
        warnings: [],
      }),
    });
  });
}

// Reusable login helper
async function loginAsDirector(page: Page) {
  await page.goto("/login");
  await page.waitForSelector('[data-testid="login-submit"]');
  await page.click('[data-testid="login-submit"]');
  // Wait for redirect to complete
  await page.waitForURL((url) => !url.pathname.includes("/login"));
}

test.describe("FestOS Data Reconciliation & Governance E2E Smoke Tests", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  // Feature 1: Imports & Data Quality
  test("1. Imports & Data Quality Smoke: 5-step wizard and quarantine review", async ({ page }) => {
    await loginAsDirector(page);
    await page.goto("/imports");

    // Header check
    await expect(page.locator("h1")).toContainText("Import & Data Quality Management");

    // Step 1 -> Step 2
    await expect(page.getByText("Step 1: Ingest Aarohan Fest Data Pack")).toBeVisible();
    await page.click("text=Continue to Mapping");

    // Step 2 -> Step 3
    await expect(page.getByText("Step 2: Auto-Detected Column Mapping")).toBeVisible();
    await page.click("text=Run Validation Check");

    // Step 3 -> Step 4
    await expect(page.getByText("Step 3: Ingestion Validation Summary")).toBeVisible();
    await page.click("text=Review Quarantine Rows");

    // Step 4 Quarantine Review & Promote Modal
    await expect(page.getByText("Step 4: Quarantine Review")).toBeVisible();
    await page.click("text=Promote Valid Records (2,833) with Reason");

    // Confirm modal opens
    await expect(page.getByText("Promote Ingestion Batch to Canonical State")).toBeVisible();
  });

  // Feature 2: Assumptions Register
  test("2. Assumptions Register Smoke: banner, 3 open decisions, inline edit with reason", async ({ page }) => {
    await loginAsDirector(page);
    await page.goto("/assumptions");

    // Header and banner
    await expect(page.locator("h1")).toContainText("Operational Assumptions Register");
    await expect(page.locator('[data-testid="unverified-assumptions-banner"]')).toBeVisible();

    // 3 Open Decisions
    await expect(page.getByText("external_budget_inr").first()).toBeVisible();
    await expect(page.getByText("late_arrival_policy").first()).toBeVisible();
    await expect(page.getByText("shuttle_capacity_seats").first()).toBeVisible();

    // Inline edit cleaning_buffer_minutes
    await page.click('[data-testid="edit-assumption-cleaning_buffer_minutes"]');
    await expect(page.getByText("Modify Assumption: cleaning_buffer_minutes")).toBeVisible();

    // Input new value and reason
    await page.fill('[data-testid="input-edit-assumption-value"]', "120");
    await page.fill('[data-testid="reason-input"]', "Housekeeping expedited turnover protocol approved");
    await page.click("text=Save & Record Audit Log");

    // Modal closes
    await expect(page.locator('[data-testid="reason-input"]')).not.toBeVisible();
  });

  // Feature 3: Participants Directory & 360 Profile
  test("3. Participants Directory Smoke: search, tri-state badges, 360 drawer, break-glass unmasking", async ({ page }) => {
    await loginAsDirector(page);
    await page.goto("/participants");

    // Header & list
    await expect(page.locator("h1")).toContainText("Participant Master Directory");
    await expect(page.getByText("Aarav Sharma")).toBeVisible();

    // Tri-state & UNKNOWN badges
    await expect(page.locator('[data-testid="badge-tri-yes"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="badge-tri-unknown"]').first()).toBeVisible();

    // Open 360 Drawer
    await page.click('[data-testid="btn-view-360-P0102"]');
    await expect(page.getByText("Participant 360")).toBeVisible();

    // Check tabs
    await expect(page.getByText("Profile & Identity")).toBeVisible();

    // Trigger Break-Glass Unmasking
    const breakGlassBtn = page.locator('[data-testid="break-glass-trigger"]').first();
    await breakGlassBtn.click();
    await expect(page.getByText("Emergency Break-Glass Unmasking")).toBeVisible();
  });

  // Feature 4: Contingents Master
  test("4. Contingents Master Smoke: 38 colleges grid, delta pills, detail drawer", async ({ page }) => {
    await loginAsDirector(page);
    await page.goto("/contingents");

    // Header & grid
    await expect(page.locator("h1")).toContainText("Institutional Contingents Master");
    await expect(page.getByText("38 Active Colleges")).toBeVisible();

    // Inspect C05 IIT Bombay card
    const c05Card = page.locator('[data-testid="contingent-card-C05"]');
    await expect(c05Card).toBeVisible();
    await expect(c05Card).toContainText("IIT Bombay");
    await expect(c05Card).toContainText("-8");

    // Open detail drawer
    await c05Card.click();
    await expect(page.getByText("Contingent Governance")).toBeVisible();
    await expect(page.getByText("Declared vs Actual Strength")).toBeVisible();
    await expect(page.getByText("Accommodation Distribution")).toBeVisible();
  });

  // Feature 5: Reconciliation Workbench
  test("5. Reconciliation Workbench Smoke: counts waterfall showing 426 remainder, duplicate compare, merge with reason", async ({ page }) => {
    await loginAsDirector(page);
    await page.goto("/reconciliation");

    // Header and waterfall remainder 426
    await expect(page.locator("h1")).toContainText("Data Reconciliation & Deduplication Workbench");
    await expect(page.getByText("Unexplained Remainder")).toBeVisible();
    await expect(page.getByText("426 Excess")).toBeVisible();

    // Duplicate queue tab
    await page.click("text=Duplicate Queue");
    await expect(page.getByText("Aditya Verma").first()).toBeVisible();

    // Side-by-side compare
    await page.click('[data-testid="btn-compare-dup_0102a"]');
    await expect(page.getByText("Side-by-Side Duplicate Comparison")).toBeVisible();

    // Proceed to merge
    await page.click('[data-testid="btn-confirm-merge-modal"]');
    await expect(page.getByText("Authorize Participant Deduplication Merge")).toBeVisible();

    // Enter mandatory reason
    await page.fill('[data-testid="reason-input"]', "Same student registered with both college and personal email");
    await page.click("text=Merge Records & Record Rationale");

    // Modal closes
    await expect(page.locator('[data-testid="reason-input"]')).not.toBeVisible();
  });

  // Feature 6: Unknowns Burn-Down Queue
  test("6. Unknowns Burn-Down Smoke: ranked queue, inline verification, leader token generator", async ({ page }) => {
    await loginAsDirector(page);
    await page.goto("/unknowns");

    // Header
    await expect(page.locator("h1")).toContainText("Unknowns Burn-Down Queue");
    await expect(page.getByText("FestOS Rule #4: UNKNOWN is First-Class")).toBeVisible();

    // Inline verify item
    await page.click('[data-testid="btn-verify-P0001"]');
    await expect(page.getByText("Verify UNKNOWN Field: diet")).toBeVisible();

    // Fill verification
    await page.selectOption('[data-testid="select-verified-value"]', "VEG");
    await page.fill('[data-testid="textarea-verify-reason"]', "Verified via telephone with contingent escort");
    await page.click('[data-testid="btn-submit-verify"]');

    // Dialog closes
    await expect(page.locator('[data-testid="select-verified-value"]')).not.toBeVisible();

    // Generate leader confirmation token
    await page.click('[data-testid="btn-token-P0001"]');
    await expect(page.getByText("Leader Field Confirmation Link")).toBeVisible();
    await expect(page.locator('[data-testid="btn-copy-token-link"]')).toBeVisible();
  });
});
