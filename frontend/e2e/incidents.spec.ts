import { test, expect, Page } from "@playwright/test";

// Helper to mock backend APIs for Incidents & Disruption Console E2E tests
async function setupIncidentsMocks(page: Page) {
  // Health & Meta
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
          "auth",
          "incidents",
          "impact",
          "staff",
          "transport",
          "notifications",
          "accommodation",
          "food",
          "events",
        ],
        auth_disabled: false,
      }),
    });
  });

  let liveIncidents = [
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
      status: "ACTIVE",
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

  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    // 1. Auth routes
    if (url.includes("/api/v1/auth/login")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "mock_jwt_token_2026",
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
    }

    if (url.includes("/api/v1/auth/me")) {
      return route.fulfill({
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
    }

    // 2. Concurrent Incidents Warning
    if (url.includes("/api/v1/incidents/concurrent-warning")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            has_concurrent_incidents: true,
            active_count: 2,
            message:
              "Concurrent Active Disruptions Detected: 2 incidents in progress (Hostel 3 Emergency Plumbing Failure; Spice Kitchen Emergency Health Violation). Cross-resource contention warning.",
            active_incident_ids: ["INC-2026-001", "INC-2026-002"],
          },
        }),
      });
    }

    // 3. Dry-Run Impact Simulation
    if (url.includes("/api/v1/incidents/dry-run") && method === "POST") {
      const body = route.request().postDataJSON();
      const scenarioId = body.scenario_id;

      if (scenarioId === "vendor_shutdown") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              incidentId: "INC-E2E-VND",
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
                "Food cross-contamination threat if stall stays active",
              ],
              plans: [
                {
                  id: "plan_a",
                  name: "Plan A: Express Reallocation to Annapurna (VND01)",
                  strategy: "Divert all 220 special dietary tokens to Annapurna Caterers.",
                  isRecommended: true,
                  peopleMoved: 0,
                  scheduleChanges: 0,
                  resourceMoves: 2,
                  costDeltaInr: 35000,
                  constraintsRelaxed: [
                    {
                      type: "SOFT",
                      constraint: "Vendor budget pre-authorization",
                      rationale: "Emergency food clause invoked.",
                    },
                  ],
                  summary: "Zero meal deficit; Annapurna holds verified FSSAI certification.",
                },
              ],
              simulatedTimeDeltaMin: 30,
            },
          }),
        });
      }

      // Default Hostel Closure Dry Run
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            incidentId: "INC-E2E-HST",
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
                    rationale: "Contingents split across multiple lodges.",
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
                constraintsRelaxed: [],
                summary: "Zero minor travel at night; balanced cost delta.",
              },
            ],
            simulatedTimeDeltaMin: 45,
          },
        }),
      });
    }

    // 4. Approve Incident Recovery Plan
    if (url.includes("/api/v1/incidents") && url.includes("/approve") && method === "POST") {
      const body = route.request().postDataJSON();
      const planId = body.plan_id || "plan_a";
      const reason = body.reason;

      const newInc = {
        id: "INC-E2E-COMMITTED",
        scenarioId: body.scenario_id || "hostel_closure",
        title: body.title || "Emergency Operational Incident",
        severity: "CRITICAL",
        status: "RESOLVED",
        createdAt: new Date().toISOString(),
        resolvedAt: new Date().toISOString(),
        peopleAffected: body.scenario_id === "vendor_shutdown" ? 220 : 85,
        approvedPlan: planId,
        approvedBy: "Devashish Roy (Festival Director)",
        approvalReason: reason,
        downstreamUpdates: [
          {
            id: "ds_01",
            domain: "Accommodation",
            label: "Reallocate participants to Lakeview Resort",
            status: "UPDATED",
            details: "45 beds blocked at Lakeview Resort, 40 beds at Campus Guest House",
            entityRoute: "/accommodation",
          },
          {
            id: "ds_02",
            domain: "Transport",
            label: "Schedule 7 Express Shuttle Runs",
            status: "UPDATED",
            details: "Assigned Vehicles V1 and V3 for hourly loops",
            entityRoute: "/transport",
          },
          {
            id: "ds_03",
            domain: "Catering",
            label: "Shift meal tokens to West Wing Dining Annex",
            status: "UPDATED",
            details: "85 meal rations diverted to Annapurna Caterers",
            entityRoute: "/food",
          },
        ],
        beforeMetrics: {
          unplacedParticipants: body.scenario_id === "vendor_shutdown" ? 0 : 85,
          mealShortages: body.scenario_id === "vendor_shutdown" ? 220 : 85,
          delayedEvents: 2,
          transportDeficit: 38,
          extraCostInr: 0,
        },
        afterMetrics: {
          unplacedParticipants: 0,
          mealShortages: 0,
          delayedEvents: 0,
          transportDeficit: 0,
          extraCostInr: body.scenario_id === "vendor_shutdown" ? 35000 : 42500,
        },
      };

      liveIncidents.unshift(newInc);

      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            change_set_id: "cs_e2e_committed_01",
            status: "APPLIED",
            incident: newInc,
            message: "Recovery plan approved and applied through ChangeService.",
          },
        }),
      });
    }

    // 5. Verify Downstream Status
    if (url.includes("/api/v1/incidents") && url.includes("/verify-downstream") && method === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            status: "VERIFIED",
            downstream_id: "ds_01",
          },
        }),
      });
    }

    // 6. Incidents List
    if (url.includes("/api/v1/incidents")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            items: liveIncidents,
            total: liveIncidents.length,
          },
        }),
      });
    }

    // 7. Impact Tree
    if (url.includes("/api/v1/impact/tree")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            rootChange: {
              id: "INC-2026-001",
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
            ],
          },
        }),
      });
    }

    // 8. Notifications Drafts
    if (url.includes("/api/v1/notifications/drafts")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            items: [
              {
                id: "ND-03",
                audience: "VENDORS",
                audienceLabel: "Food Vendors",
                recipientCount: 14,
                subject: "Capacity Reallocation Notice: Annapurna Caterers & Annex",
                body: "Attn Vendor Leads: Spice Kitchen (VND04) operations are paused. Annapurna Caterers (VND01) will absorb 220 Jain/Vegan lunch packs.",
                priority: "HIGH",
                status: "DRAFT",
                triggerIncidentId: "INC-2026-002",
                triggerEventLabel: "Vendor VND04 Hygiene Suspension",
                createdAt: "2026-10-31T10:00:00Z",
              },
            ],
            total: 1,
          },
        }),
      });
    }

    // Default fallback
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: {} }),
    });
  });
}

test.describe("FestOS Disruption Management Console Acceptance Flows (Prompt 15)", () => {
  test.beforeEach(async ({ page }) => {
    await setupIncidentsMocks(page);

    // Pre-populate authentication in localStorage
    await page.addInitScript(() => {
      localStorage.setItem("festos_token", "mock_jwt_token_2026");
      localStorage.setItem(
        "festos_user",
        JSON.stringify({
          id: "usr_dir_001",
          email: "director@festos.internal",
          full_name: "Dr. Devashish Roy",
          role: "FESTIVAL_DIRECTOR",
          permissions: ["*"],
        })
      );
    });
  });

  // Acceptance 1: Hostel Closure E2E Journey
  test("Journey 1: Hostel Closure Disruption injection -> dry run -> multi-plan compare -> approve with reason -> downstream verification", async ({
    page,
  }) => {
    // 1. Navigate to Incident Center
    await page.goto("/incidents");

    // Verify 7 scenario cards rendered
    await expect(page.locator("text=Seven Live-Test Scenario Cards").first()).toBeVisible();
    await expect(page.locator('[data-testid="scenario-card-hostel_closure"]')).toBeVisible();

    // Verify concurrent incident banner is active
    await expect(page.locator('[data-testid="concurrent-incident-banner"]')).toBeVisible();

    // 2. Click Inject Disruption on Hostel Closure Card
    await page.click('[data-testid="launch-btn-hostel_closure"]');

    // 3. Verify Parameter Form
    await expect(page.locator('[data-testid="parameter-form"]')).toBeVisible();
    await expect(page.locator("text=Hostel 3 structural plumbing failure")).toBeVisible();

    // 4. Click Preview Impact (Dry Run)
    await page.click('[data-testid="preview-impact-btn"]');

    // 5. Verify Impact Preview displays blast radius
    await expect(page.locator('[data-testid="impact-preview"]')).toBeVisible();
    await expect(page.locator('[data-testid="preview-people-affected"]')).toHaveTextContent("85");

    // 6. Click Compare Recovery Plans
    await page.click('[data-testid="compare-plans-btn"]');

    // 7. Verify multi-plan comparison side-by-side
    await expect(page.locator('[data-testid="compare-plans-view"]')).toBeVisible();
    await expect(page.locator('[data-testid="plan-card-plan_a"]')).toBeVisible();
    await expect(page.locator('[data-testid="plan-card-plan_b"]')).toBeVisible();
    await expect(page.locator('[data-testid="plan-card-plan_c"]')).toBeVisible();
    await expect(page.locator("text=₹42,500")).toBeVisible();

    // 8. Click Authorize & Commit Plan to open ConfirmWithReason modal
    await page.click('[data-testid="approve-plan-btn"]');

    // Modal opens
    await expect(page.locator('[data-testid="reason-input"]')).toBeVisible();

    // Enter required operational justification
    await page.fill(
      '[data-testid="reason-input"]',
      "Authorized emergency evacuation of Hostel 3. Reallocating 85 students to Lakeview Resort under Plan A."
    );

    // Confirm button enabled and clicked
    await page.click('[data-testid="confirm-button"]');

    // 9. Watch execution progress and arrive at Verification Screen
    await expect(page.locator('[data-testid="verification-screen"]')).toBeVisible({ timeout: 6000 });
    await expect(page.locator("text=State Update Verified & Change Set Applied")).toBeVisible();

    // Verify Downstream Update Tracker displays Accommodation, Transport, Catering
    await expect(page.locator('[data-testid="downstream-item-accommodation"]')).toBeVisible();
    await expect(page.locator('[data-testid="downstream-item-transport"]')).toBeVisible();

    // 10. Mark Accommodation Verified
    await page.click('[data-testid="verify-btn-accommodation"]');
    await expect(page.locator('[data-testid="downstream-item-accommodation"]')).toContainText("Verified");

    // 11. Click Inspect Impact Tree to view downstream blast radius
    await page.click("button:has-text('Inspect Impact Tree')");
    await page.waitForURL("**/impact");

    // Verify visual impact tree is rendered
    await expect(page.locator('[data-testid="impact-workspace"]')).toBeVisible();
    await expect(page.locator('[data-testid="tree-node-grp_participants"]')).toBeVisible();
    await expect(page.locator('[data-testid="tree-leaf-P0102"]')).toBeVisible();
  });

  // Acceptance 2: Vendor Shutdown E2E Journey
  test("Journey 2: Food Vendor Emergency Shutdown -> dietary gap analysis -> replacement plan -> downstream food & notification update", async ({
    page,
  }) => {
    // 1. Navigate to Incident Center
    await page.goto("/incidents");

    // 2. Click Inject Disruption on Food Vendor Shutdown
    await page.click('[data-testid="launch-btn-vendor_shutdown"]');

    // 3. Verify Parameter Form displays 220 affected meals and Spice Kitchen
    await expect(page.locator('[data-testid="parameter-form"]')).toBeVisible();
    await expect(page.locator("text=Vendor VND04 (Spice Kitchen) fails sudden health inspection")).toBeVisible();

    // 4. Click Preview Impact (Dry Run)
    await page.click('[data-testid="preview-impact-btn"]');

    // 5. Verify blast radius shows 220 people affected
    await expect(page.locator('[data-testid="preview-people-affected"]')).toHaveTextContent("220");

    // 6. Compare Recovery Plans
    await page.click('[data-testid="compare-plans-btn"]');
    await expect(page.locator("text=Express Reallocation to Annapurna (VND01)")).toBeVisible();
    await expect(page.locator("text=₹35,000")).toBeVisible();

    // 7. Authorize with ConfirmWithReason
    await page.click('[data-testid="approve-plan-btn"]');
    await page.fill(
      '[data-testid="reason-input"]',
      "FSSAI compliance breach at VND04 stall. Diverting lunch tokens to Annapurna Caterers."
    );
    await page.click('[data-testid="confirm-button"]');

    // 8. Verification screen verifies zero meal shortages
    await expect(page.locator('[data-testid="verification-screen"]')).toBeVisible({ timeout: 6000 });
    await expect(page.locator("text=Before vs After Operational State Delta")).toBeVisible();

    // Close modal
    await page.click('[data-testid="close-verification-btn"]');

    // 9. Navigate to Notifications workspace to review generated vendor broadcast
    await page.goto("/notifications");
    await expect(page.locator('[data-testid="notifications-workspace"]')).toBeVisible();
    await expect(page.locator('[data-testid="draft-card-ND-03"]')).toBeVisible();
    await expect(
      page.locator("text=Capacity Reallocation Notice: Annapurna Caterers & Annex")
    ).toBeVisible();

    // 10. Mock-Send broadcast
    await page.click('[data-testid="mock-send-btn-ND-03"]');
    await expect(page.locator("text=Dispatched")).toBeVisible();
  });
});

