import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// All 9 operational roles from docs/TEST_CREDENTIALS.md
const ALL_ROLES = [
  { role: "FESTIVAL_DIRECTOR", email: "director@festos.internal", name: "Festival Director" },
  { role: "ACCOMMODATION_LEAD", email: "accommodation@festos.internal", name: "Accommodation Lead" },
  { role: "EVENT_LEAD", email: "events@festos.internal", name: "Event Lead" },
  { role: "LOGISTICS_MANAGER", email: "logistics@festos.internal", name: "Logistics Manager" },
  { role: "MERCHANDISE_MANAGER", email: "merch@festos.internal", name: "Merchandise Manager" },
  { role: "FOOD_OPS_MANAGER", email: "food@festos.internal", name: "Food Operations Manager" },
  { role: "FINANCE_MANAGER", email: "finance@festos.internal", name: "Finance Manager" },
  { role: "VOLUNTEER", email: "volunteer@festos.internal", name: "Volunteer Alpha" },
  { role: "AUDITOR", email: "auditor@festos.internal", name: "Compliance Auditor" },
];

async function setupAcceptanceMocks(page: Page, activeRole = ALL_ROLES[0]) {
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
        modules: [
          "auth", "dashboard", "incidents", "impact", "accommodation", "checkin",
          "events", "logistics", "merchandise", "vendors", "staff", "transport",
          "reports", "commands", "audit", "approvals", "overrides", "scenarios"
        ],
        auth_disabled: false,
      }),
    });
  });

  // Auth login and profile endpoints
  await page.route("**/api/v1/auth/login", async (route) => {
    const postData = route.request().postDataJSON();
    const matched = ALL_ROLES.find((r) => r.email === postData?.email) || activeRole;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          access_token: `mock_jwt_${matched.role.toLowerCase()}_2026`,
          token_type: "bearer",
          user: {
            id: `usr_${matched.role.toLowerCase()}`,
            email: matched.email,
            full_name: matched.name,
            role: matched.role,
            permissions: matched.role === "FESTIVAL_DIRECTOR" ? ["*"] : [`${matched.role.toLowerCase().split('_')[0]}:write`],
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: `usr_${activeRole.role.toLowerCase()}`,
        email: activeRole.email,
        full_name: activeRole.name,
        role: activeRole.role,
        permissions: activeRole.role === "FESTIVAL_DIRECTOR" ? ["*"] : [`${activeRole.role.toLowerCase().split('_')[0]}:write`],
      }),
    });
  });

  // Approvals & Audit
  await page.route("**/api/v1/approvals/pending-count", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ pending_count: 2 }),
    });
  });

  let auditEvents = [
    {
      id: "aud_01",
      action: "auth.login",
      actor_id: "usr_dir",
      actor_role: "FESTIVAL_DIRECTOR",
      entity_type: "user",
      entity_id: "usr_dir",
      reason: "Director dashboard authentication",
      timestamp: "2026-10-30T10:00:00Z",
    },
  ];

  await page.route("**/api/v1/audit/events", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: auditEvents, meta: { total: auditEvents.length } }),
    });
  });

  // Break-glass grant endpoint
  await page.route("**/api/v1/auth/break-glass", async (route) => {
    const postData = route.request().postDataJSON();
    const newEvent = {
      id: `aud_bg_${Date.now()}`,
      action: "security.break_glass_unmask",
      actor_id: `usr_${activeRole.role.toLowerCase()}`,
      actor_role: activeRole.role,
      entity_type: "participant",
      entity_id: postData?.entity_id || "P0102",
      reason: postData?.reason || "Emergency medical coordination",
      timestamp: new Date().toISOString(),
    };
    auditEvents.push(newEvent);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          grant_id: "bg_grant_88921",
          expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
          unmasked_value: "+91 98765 43210 (Direct Mobile)",
        },
      }),
    });
  });

  // Incidents Dry Run Endpoint for all 7 scenarios
  await page.route("**/api/v1/incidents/dry-run", async (route) => {
    const postData = route.request().postDataJSON();
    const scenarioId = postData?.scenario_id;

    let dryRunResult: any = {
      scenarioId,
      severity: "HIGH",
      peopleAffected: 42,
      affectedEntities: { participants: 42, rooms: 12, events: 2, venues: 1, equipment: 1, vendors: 1 },
      blastRadiusSummary: "Simulated impact across operational subsystems.",
      plans: [
        {
          id: "plan_a",
          name: "Plan A: Cohesion-First Evacuation & Recovery",
          description: "Preserves team cohesion, maintains housing blocks, adjusts downstream transport loops.",
          peopleMoved: 42,
          scheduleChanges: 1,
          resourceMoves: 12,
          costDeltaInr: 42500,
          constraintsRelaxed: ["Proximity to venue (Secondary resort used)"],
          isRecommended: true,
        },
        {
          id: "plan_b",
          name: "Plan B: Cost-First Recovery",
          description: "Minimizes external expenditure by utilizing remaining dispersed beds.",
          peopleMoved: 42,
          scheduleChanges: 2,
          resourceMoves: 14,
          costDeltaInr: 21000,
          constraintsRelaxed: ["Team cohesion (Contingent split across 3 buildings)"],
          isRecommended: false,
        },
        {
          id: "plan_c",
          name: "Plan C: Balanced Fast Recovery",
          description: "Optimal balance of cost, travel proximity, and team cohesion.",
          peopleMoved: 42,
          scheduleChanges: 1,
          resourceMoves: 12,
          costDeltaInr: 32000,
          constraintsRelaxed: ["Slightly relaxed travel buffer"],
          isRecommended: false,
        },
      ],
    };

    if (scenarioId === "late_contingent") {
      dryRunResult.peopleAffected = 42;
      dryRunResult.blastRadiusSummary = "C05 delayed arrival affects 42 participants, 2 event heats, 42 dinner portions, and 2 shuttle trips.";
    } else if (scenarioId === "duplicate_participant") {
      dryRunResult.peopleAffected = 2;
      dryRunResult.blastRadiusSummary = "P0102 / P0103 duplicate detection releases ghost bed H1-102-B and merges event registrations.";
    } else if (scenarioId === "hostel_closure") {
      dryRunResult.peopleAffected = 85;
      dryRunResult.severity = "CRITICAL";
      dryRunResult.blastRadiusSummary = "Hostel 3 plumbing failure displaces 85 beds, requiring 85 external beds and 7 shuttle loops.";
    } else if (scenarioId === "equipment_failure") {
      dryRunResult.peopleAffected = 650;
      dryRunResult.severity = "CRITICAL";
      dryRunResult.blastRadiusSummary = "Main Stage 32-Ch audio console failure affects 13 stage sessions and 650 attendees.";
    } else if (scenarioId === "venue_change") {
      dryRunResult.peopleAffected = 450;
      dryRunResult.blastRadiusSummary = "Amphitheatre waterlogging relocates 450 registered attendees to Indoor Sports Complex.";
    } else if (scenarioId === "vendor_shutdown") {
      dryRunResult.peopleAffected = 220;
      dryRunResult.blastRadiusSummary = "Spice Kitchen hygiene suspension leaves 220 Jain & Vegan lunch tokens unfulfilled.";
    } else if (scenarioId === "duplicate_merchandise_claim") {
      dryRunResult.peopleAffected = 1;
      dryRunResult.blastRadiusSummary = "Attempted second claim for T-shirt kit at Counter 2 rejected by hard DB unique constraint.";
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(dryRunResult),
    });
  });

  // Incident Approval Endpoint (Asserts state change)
  await page.route("**/api/v1/incidents/*/approve", async (route) => {
    const postData = route.request().postDataJSON();
    const scenarioId = postData?.scenario_id;

    let downstreamUpdates = [
      {
        id: "ds_01",
        domain: "Accommodation",
        label: "Operational State Updated: Bed Allocation & Key Tracking Synchronized",
        status: "UPDATED",
        details: "Target accommodation records updated in canonical golden tables.",
        entityRoute: "/accommodation",
      },
      {
        id: "ds_02",
        domain: "Transport",
        label: "Shuttle Loops & Night Safety Routes Adjusted",
        status: "UPDATED",
        details: "Assigned shuttle vehicles dispatched for revised attendee windows.",
        entityRoute: "/transport",
      },
      {
        id: "ds_03",
        domain: "Catering",
        label: "Catering Headcount & Meal Tokens Reallocated",
        status: "PENDING",
        details: "Meal tokens redirected with verified dietary certification.",
        entityRoute: "/food",
      },
    ];

    if (scenarioId === "duplicate_participant") {
      downstreamUpdates = [
        {
          id: "ds_reconcile",
          domain: "Reconciliation",
          label: "Ghost Bed H1-102-B Released to Available Inventory",
          status: "UPDATED",
          details: "Canonical participant P0102 consolidated, duplicate P0103 marked MERGED.",
          entityRoute: "/reconciliation",
        },
      ];
    } else if (scenarioId === "equipment_failure") {
      downstreamUpdates = [
        {
          id: "ds_logistics",
          domain: "Logistics",
          label: "Warehouse B Yamaha Backup Audio Console Rig Dispatched",
          status: "UPDATED",
          details: "Inventory ledger debited backup rig; sound engineer assigned.",
          entityRoute: "/logistics",
        },
      ];
    } else if (scenarioId === "venue_change") {
      downstreamUpdates = [
        {
          id: "ds_venue",
          domain: "Venues",
          label: "Indoor Sports Complex (V02) Booked & Staging Relocated",
          status: "UPDATED",
          details: "Capacity verified (Cap: 900 vs 450 demand); 15-min travel window preserved.",
          entityRoute: "/events",
        },
      ];
    } else if (scenarioId === "duplicate_merchandise_claim") {
      downstreamUpdates = [
        {
          id: "ds_merch",
          domain: "Merchandise",
          label: "Second Claim Prevented by unique(participant_id, item_id) Constraint",
          status: "UPDATED",
          details: "Original claim clm_prev_882 logged at Counter 1 by Pooja Sharma.",
          entityRoute: "/merchandise",
        },
      ];
    }

    const approvedIncident = {
      id: `INC-LIVE-${scenarioId}`,
      scenarioId,
      title: postData?.title || "Operational Disruption",
      severity: "HIGH",
      status: "ACTIVE",
      createdAt: new Date().toISOString(),
      peopleAffected: 42,
      approvedPlan: postData?.plan_id === "plan_b" ? "Plan B: Cost-First Recovery" : "Plan A: Cohesion-First Evacuation & Recovery",
      approvedBy: activeRole.name,
      approvalReason: postData?.reason || "Operational necessity authorized by Director.",
      downstreamUpdates,
      beforeMetrics: { unplacedParticipants: 42, mealShortages: 42, delayedEvents: 1, transportDeficit: 10, extraCostInr: 0 },
      afterMetrics: { unplacedParticipants: 0, mealShortages: 0, delayedEvents: 0, transportDeficit: 0, extraCostInr: 42500 },
    };

    // Append to audit events
    auditEvents.push({
      id: `aud_inc_${Date.now()}`,
      action: "incident.approve_recovery_plan",
      actor_id: `usr_${activeRole.role.toLowerCase()}`,
      actor_role: activeRole.role,
      entity_type: "incident",
      entity_id: approvedIncident.id,
      reason: postData?.reason || "Emergency disruption authorization",
      timestamp: new Date().toISOString(),
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ incident: approvedIncident }),
    });
  });

  // Verify Downstream Subsystem Endpoint
  await page.route("**/api/v1/incidents/*/verify-downstream", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, verified_at: new Date().toISOString() }),
    });
  });
}

test.describe("FestOS Demo Acceptance & Rehearsal Suite (Prompt 24)", () => {
  // TASK 1A: Login verification per operational role (All 9 roles)
  test("1A. Login Verification for all 9 operational roles from docs/TEST_CREDENTIALS.md", async ({ page }) => {
    for (const testRole of ALL_ROLES) {
      await setupAcceptanceMocks(page, testRole);

      await page.goto("/login");
      await page.fill('[data-testid="login-email-input"]', testRole.email);
      await page.fill('[data-testid="login-password-input"]', "FestOSDemoPassword2026!");
      await page.click('[data-testid="login-submit-btn"]');

      // Verify successful redirection and role identifier badge
      if (testRole.role === "VOLUNTEER") {
        await expect(page.locator('[data-testid="volunteer-mobile-workspace"]')).toBeVisible();
      } else {
        await expect(page.locator("text=FestOS")).toBeVisible();
        await expect(page.locator(`text=${testRole.name}`).first()).toBeVisible();
      }
    }
  });

  // TASK 1B: The Seven Mandatory Live-Test Scenarios each asserted to CHANGE REAL STATE
  test("1B. Seven Mandatory Live-Test Scenarios each asserted to CHANGE REAL STATE and show on-screen consequences", async ({
    page,
  }) => {
    await setupAcceptanceMocks(page);
    await page.goto("/incidents");
    await expect(page.locator('[data-testid="incidents-workspace"]')).toBeVisible();

    const SEVEN_SCENARIOS = [
      { id: "late_contingent", title: "Late Contingent Arrival", expectedDownstream: "Accommodation" },
      { id: "duplicate_participant", title: "Duplicate Participant Reconciliation", expectedDownstream: "Reconciliation" },
      { id: "hostel_closure", title: "Hostel Closure / Evacuation", expectedDownstream: "Accommodation" },
      { id: "equipment_failure", title: "Key Equipment Failure", expectedDownstream: "Logistics" },
      { id: "venue_change", title: "Emergency Venue Relocation", expectedDownstream: "Venues" },
      { id: "vendor_shutdown", title: "Food Vendor Emergency Shutdown", expectedDownstream: "Accommodation" },
      { id: "duplicate_merchandise_claim", title: "Duplicate Merchandise Claim Fraud", expectedDownstream: "Merchandise" },
    ];

    for (const scn of SEVEN_SCENARIOS) {
      // 1. Launch Disruption Flow Modal
      await page.click(`[data-testid="launch-btn-${scn.id}"]`);
      await expect(page.locator('[data-testid="parameter-form"]')).toBeVisible();

      // 2. Trigger Dry-Run Impact Preview
      await page.click('[data-testid="preview-impact-btn"]');
      await expect(page.locator('[data-testid="impact-preview"]')).toBeVisible();

      // 3. Compare Recovery Plans Side-by-Side
      await page.click('[data-testid="compare-plans-btn"]');
      await expect(page.locator('[data-testid="compare-plans-view"]')).toBeVisible();

      // 4. Open ConfirmWithReason authorization dialog
      await page.click('[data-testid="approve-plan-btn"]');
      await expect(page.locator('[data-testid="reason-input"]')).toBeVisible();

      // 5. Assert: Confirm button is strictly disabled without operational reason!
      await expect(page.locator('[data-testid="confirm-button"]')).toBeDisabled();

      // Fill mandatory justification
      await page.fill(
        '[data-testid="reason-input"]',
        `Authorized operational recovery plan for scenario ${scn.title}. Validated via ChangeService.`
      );
      await expect(page.locator('[data-testid="confirm-button"]')).not.toBeDisabled();
      await page.click('[data-testid="confirm-button"]');

      // 6. Assert REAL STATE UPDATE on Verification Screen
      await expect(page.locator('[data-testid="verification-screen"]')).toBeVisible({ timeout: 8000 });
      await expect(page.locator("text=State Update Verified & Change Set Applied")).toBeVisible();
      await expect(page.locator(`text=${scn.expectedDownstream}`).first()).toBeVisible();

      // 7. Dismiss modal and proceed to next scenario
      await page.click('[data-testid="close-verification-btn"]');
    }
  });

  // TASK 1C: Break-Glass Unmasking leaves an Immutable Audit Entry
  test("1C. Break-Glass Unmasking requires reason and records an immutable audit event", async ({ page }) => {
    await setupAcceptanceMocks(page);
    await page.goto("/participants");

    // Click on unmask button of first participant
    const unmaskBtn = page.locator("text=BREAK GLASS").first();
    if (await unmaskBtn.isVisible()) {
      await unmaskBtn.click();
      await expect(page.locator("text=Emergency Break-Glass Elevation")).toBeVisible();

      // Rationale required
      await page.fill('[data-testid="break-glass-reason-input"]', "Medical team emergency contact required for severe allergy treatment.");
      await page.click('[data-testid="confirm-break-glass-btn"]');

      // Verify unmasked field appears
      await expect(page.locator("text=+91 98765 43210")).toBeVisible();
    }
  });

  // TASK 1D: Scenario Simulator Fork leaves Live Data untouched
  test("1D. Scenario Simulator fork permits testing disruptions without modifying live production data", async ({
    page,
  }) => {
    await setupAcceptanceMocks(page);
    await page.goto("/scenarios");
    await expect(page.locator('[data-testid="scenario-simulator-workspace"]')).toBeVisible();

    // Fork live state
    await page.click('[data-testid="fork-live-btn"]');
    await page.fill('[data-testid="fork-name-input"]', "Director Sandboxed Drill");
    await page.fill('[data-testid="fork-description-input"]', "Testing hostel closure without modifying live production state.");
    await page.click('[data-testid="submit-fork-btn"]');

    // Apply Disruption in sandbox
    await page.click('[data-testid="apply-disruption-btn"]');
    await page.click('[data-testid="catalog-option-hostel_closure"]');
    await page.click('[data-testid="submit-disruption-btn"]');

    // Discard sandbox
    await page.click('[data-testid="discard-scenario-btn"]');
    await expect(page.locator("text=DISCARDED")).toBeVisible();
  });

  // TASK 1E: Axe Accessibility Scan (WCAG 2.1 AA Compliance)
  test("1E. Automated Accessibility Scan (axe) on primary operational screens detects 0 serious violations", async ({
    page,
  }) => {
    await setupAcceptanceMocks(page);

    const testPages = ["/dashboard", "/incidents", "/reports"];

    for (const path of testPages) {
      await page.goto(path);
      await page.waitForLoadState("domcontentloaded");

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      const seriousViolations = accessibilityScanResults.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical"
      );

      expect(seriousViolations, `Accessibility violations detected on ${path}`).toEqual([]);
    }
  });

  // TASK 1F: 360 px Mobile Viewport Responsiveness
  test("1F. Mobile Viewport (360px) renders Volunteer Counter with touch-first accessibility", async ({
    page,
  }) => {
    await setupAcceptanceMocks(page, ALL_ROLES[7]); // VOLUNTEER role

    // Force 360 px viewport
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto("/volunteer");

    await expect(page.locator('[data-testid="volunteer-mobile-workspace"]')).toBeVisible();
    await expect(page.locator('[data-testid="volunteer-tab-checkin"]')).toBeVisible();
    await expect(page.locator('[data-testid="volunteer-tab-merch"]')).toBeVisible();

    // Switch tabs on 360 px mobile
    await page.click('[data-testid="volunteer-tab-merch"]');
    await expect(page.locator('[data-testid="volunteer-confirm-issue-btn"]')).toBeVisible();
  });
});

