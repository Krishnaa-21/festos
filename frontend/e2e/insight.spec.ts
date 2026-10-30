import { test, expect, Page } from "@playwright/test";

// Mock helper to intercept backend API calls for Insight & Command workspaces
async function setupInsightMocks(page: Page) {
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
          "dashboard",
          "scenarios",
          "premortem",
          "forecasting",
          "decisions",
          "unknowns",
          "accommodation",
          "food",
          "staff",
          "transport",
          "incidents",
        ],
        auth_disabled: false,
      }),
    });
  });

  // Auth routes
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

  // State containers for mutations during tests
  let attentionItems = [
    {
      id: "att_01",
      module: "accommodation",
      kind: "ACCESSIBILITY_ARRIVAL_IMMINENT",
      title: "3 Participants with unconfirmed ground-floor accessibility needs arriving within 2h",
      severity: "CRITICAL",
      severityLevel: 4,
      urgencyLevel: 5,
      hoursToImpact: 1.2,
      peopleAffected: 3,
      uncertainty: 0.05,
      resourceCriticality: 5,
      attentionScore: 4 * 5 * 3,
      action: {
        label: "Assign Accessible Rooms",
        route: "/accommodation",
        api: "/api/v1/accommodation/allocate",
      },
      explanation: "Wheelchair-accessible ground-floor beds in Hostel 1 & 2 are unallocated. Fast-track allocation required.",
      isSnoozed: false,
    },
    {
      id: "att_02",
      module: "food",
      kind: "DIETARY_SHORTAGE_IMMINENT",
      title: "220 Jain & Vegan lunch meals unassigned due to Spice Kitchen (VND04) health pause",
      severity: "CRITICAL",
      severityLevel: 4,
      urgencyLevel: 4,
      hoursToImpact: 2.5,
      peopleAffected: 220,
      uncertainty: 0.1,
      resourceCriticality: 5,
      attentionScore: 4 * 4 * 220,
      action: {
        label: "Reallocate to Annapurna",
        route: "/food",
        api: "/api/v1/food/reallocate",
      },
      explanation: "Spice Kitchen failed sudden safety inspection. Divert dietary vouchers to Annapurna Caterers.",
      isSnoozed: false,
    },
    {
      id: "att_03",
      module: "transport",
      kind: "SHUTTLE_CAPACITY_DEFICIT",
      title: "Lakeview midnight shuttle route exceeds confirmed fleet capacity by 14 seats",
      severity: "HIGH",
      severityLevel: 3,
      urgencyLevel: 3,
      hoursToImpact: 8.0,
      peopleAffected: 14,
      uncertainty: 0.2,
      resourceCriticality: 3,
      attentionScore: 3 * 3 * 14,
      action: {
        label: "Dispatch Extra Shuttle",
        route: "/transport",
        api: "/api/v1/transport/shuttles",
      },
      explanation: "Late-night return surge from Main Auditorium requires an additional 14-seater loop.",
      isSnoozed: false,
    },
  ];

  let scenariosList = [
    {
      id: "scen_live_fork_01",
      name: "Day 2 Flash Flood Contingency Plan",
      description: "Simulation of heavy downpour submerging low-lying food stalls & transit roads",
      createdAt: "2026-10-30T14:00:00Z",
      actorId: "usr_dir_001",
      actorName: "Dr. Devashish Roy",
      status: "ACTIVE",
      isStale: true,
      liveMutationsSinceFork: 14,
      lastSyncedAt: "2026-10-30T14:00:00Z",
      disruptionsApplied: [
        {
          id: "da_01",
          disruptionId: "hostel_closure",
          targetId: "HOSTEL-03",
          appliedAt: "2026-10-30T14:05:00Z",
          summary: "Hostel 3 structural plumbing burst flooding ground floor and electrical ducting.",
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
          key: "cost_delta_inr",
          label: "Additional Cost",
          liveValue: 0,
          scenarioValue: 42500,
          delta: "+₹42,500",
          unit: "INR",
          impactStatus: "DEGRADED",
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
    },
  ];

  // Intercept all API calls
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    // 1. Dashboard Metrics
    if (url.includes("/api/v1/dashboard/metrics")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
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
          },
        }),
      });
    }

    // 2. Attention Queue Snooze
    if (url.includes("/api/v1/dashboard/attention") && url.includes("/snooze") && method === "POST") {
      const body = JSON.parse(route.request().postData() || "{}");
      const match = url.match(/\/attention\/([^/]+)\/snooze/);
      const itemId = match ? match[1] : "";
      const item = attentionItems.find((i) => i.id === itemId);
      if (item) {
        if (body.acknowledged) {
          (item as any).acknowledgedBy = "Dr. Devashish Roy";
        } else {
          item.isSnoozed = true;
          (item as any).snoozeReason = body.reason || "Operational review underway";
          (item as any).snoozedUntil = new Date(Date.now() + (body.minutes || 60) * 60000).toISOString();
        }
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            id: itemId,
            status: body.acknowledged ? "ACKNOWLEDGED" : "SNOOZED",
            reason: body.reason,
          },
        }),
      });
    }

    // 3. Attention Queue List
    if (url.includes("/api/v1/dashboard/attention")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            items: attentionItems,
            total: attentionItems.length,
          },
        }),
      });
    }

    // 4. Heatmap
    if (url.includes("/api/v1/dashboard/heatmap")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            cells: [
              {
                severity: "CRITICAL",
                severityLevel: 4,
                timeWindow: "<=1h",
                timeWindowIndex: 0,
                itemCount: 1,
                totalPeopleAffected: 3,
                avgUncertainty: 0.05,
                items: [attentionItems[0]],
              },
              {
                severity: "CRITICAL",
                severityLevel: 4,
                timeWindow: "1-4h",
                timeWindowIndex: 1,
                itemCount: 1,
                totalPeopleAffected: 220,
                avgUncertainty: 0.1,
                items: [attentionItems[1]],
              },
            ],
            totalRisks: attentionItems.length,
          },
        }),
      });
    }

    // 5. Scenarios Fork
    if (url.endsWith("/api/v1/scenarios") && method === "POST") {
      const body = JSON.parse(route.request().postData() || "{}");
      const newScen = {
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
      scenariosList.unshift(newScen);
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ data: newScen }),
      });
    }

    // 6. Simulate Disruption in Scenario
    if (url.includes("/api/v1/scenarios") && url.includes("/simulate-incident") && method === "POST") {
      const match = url.match(/\/scenarios\/([^/]+)\/simulate-incident/);
      const scenarioId = match ? match[1] : "";
      const body = JSON.parse(route.request().postData() || "{}");
      const scen = scenariosList.find((s) => s.id === scenarioId) || scenariosList[0];

      scen.disruptionsApplied.push({
        id: `da_${Date.now()}`,
        disruptionId: body.incident_type || "hostel_closure",
        targetId: body.target_id || "HOSTEL-03",
        appliedAt: new Date().toISOString(),
        summary: "Hostel 3 structural plumbing burst flooding ground floor and electrical ducting.",
      });

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
          unit: "INR",
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

      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            scenario: scen,
            message: "Disruption applied to sandbox.",
          },
        }),
      });
    }

    // 7. Discard Scenario
    if (url.includes("/api/v1/scenarios") && url.includes("/discard") && method === "POST") {
      const match = url.match(/\/scenarios\/([^/]+)\/discard/);
      const scenarioId = match ? match[1] : "";
      const idx = scenariosList.findIndex((s) => s.id === scenarioId);
      if (idx !== -1) {
        scenariosList[idx].status = "DISCARDED";
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            id: scenarioId,
            status: "DISCARDED",
            message: "Simulation sandbox destroyed. Production database remains untouched.",
          },
        }),
      });
    }

    // 8. Scenarios List
    if (url.includes("/api/v1/scenarios")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            items: scenariosList,
            catalog: [
              {
                id: "hostel_closure",
                name: "Hostel 3 Evacuation (85 Beds)",
                description: "Simulates sudden plumbing failure forcing immediate evacuation.",
                category: "ACCOMMODATION",
                severity: "CRITICAL",
                suggestedPlan: "Cohesion-first relocation to Lakeview Resort",
              },
              {
                id: "vendor_shutdown",
                name: "Spice Kitchen Shutdown (220 Meals)",
                description: "FSSAI health inspection suspension creates instant dietary gap.",
                category: "FOOD",
                severity: "HIGH",
                suggestedPlan: "Emergency diversion to Annapurna Caterers",
              },
            ],
            total: scenariosList.length,
          },
        }),
      });
    }

    // 9. Pre-Mortem 72h Timeline
    if (url.includes("/api/v1/premortem/timeline")) {
      const hours = [];
      const startEpoch = new Date("2026-10-30T06:00:00Z").getTime();
      for (let i = 0; i < 72; i++) {
        const currentMs = startEpoch + i * 3600 * 1000;
        const dt = new Date(currentMs);
        const dayIndex = Math.floor(i / 24);
        const dayLabel = dayIndex === 0 ? "Day 1 (Arrivals)" : dayIndex === 1 ? "Day 2 (Main Events)" : "Day 3 (Finals)";
        const hourOfDay = dt.getUTCHours();
        const timeLabel = `${dt.toISOString().substring(5, 10)} ${String(hourOfDay).padStart(2, "0")}:00`;

        const activeCriticalRisks = [];
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
            id: "risk_h30_genset",
            title: "Gymnasium Genset G01 Overload: 96% continuous load on 500kVA unit",
            severity: "CRITICAL",
            peopleAffected: 1200,
            explanation: "Simultaneous operation of lighting rig, RoboWars arena, and HVAC.",
            preventiveAction: "Stagger arena AC compressors and dispatch secondary 250kVA generator.",
            route: "/logistics",
          });
        }

        hours.push({
          hourIndex: i,
          timestamp: dt.toISOString(),
          timeLabel,
          festDay: dayLabel,
          bedOccupancy: {
            campusOccupied: 700,
            externalOccupied: 400,
            availableBeds: 340,
            occupancyPct: 76.4,
            projectedUnplaced: 0,
          },
          foodDemand: {
            slot: i >= 28 && i <= 32 ? "Lunch" : "Breakfast",
            confirmedDemand: i >= 28 && i <= 32 ? 2200 : 1650,
            vendorCapacity: i >= 28 && i <= 32 ? 1980 : 1800,
            deficit: i >= 28 && i <= 32 ? 220 : 0,
            dietaryGap: i >= 28 && i <= 32 ? 220 : 0,
          },
          venueUtilisation: {
            activeVenues: 6,
            totalVenues: 8,
            bottleneckVenue: "Main Auditorium (98% capacity)",
            turnoverOverlaps: 0,
          },
          equipmentDemand: {
            criticalEquipmentUnits: 42,
            equipmentInUse: 38,
            spofGenerators: i >= 28 && i <= 32 ? 1 : 0,
            highDrainCount: 3,
          },
          volunteerCoverage: {
            requiredVolunteers: 45,
            onShiftVolunteers: 42,
            uncoveredSlots: 3,
            overloadedVolunteers: 1,
          },
          transportStatus: {
            shuttlesInTransit: 7,
            totalFleet: 12,
            passengerDemand: 160,
            seatShortage: 0,
          },
          activeCriticalRisks,
        });
      }

      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            hours,
            totalHours: 72,
            peakRiskHourIndex: 30,
          },
        }),
      });
    }

    // 10. Pre-Mortem SPOF & Preventive & Resilience
    if (url.includes("/api/v1/premortem/spof")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              id: "spof_01",
              title: "West Dining Annex: Single FSSAI Certified Kitchen",
              domain: "FOOD",
              severity: "CRITICAL",
              peopleExposed: 650,
              singlePointFailure: "Vendor VND04 handles 100% of special dietary preparations.",
              mitigationStatus: "RECOMMENDED",
            },
          ],
        }),
      });
    }

    if (url.includes("/api/v1/premortem/preventive")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              id: "prev_01",
              title: "Pre-authorize Annapurna 250 Meal Standby Buffer",
              domain: "FOOD",
              triggerHour: "Hour 24",
              costInr: 15000,
              status: "READY",
            },
          ],
        }),
      });
    }

    if (url.includes("/api/v1/premortem/resilience")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            overallScore: 84,
            benchmarkComparison: "+12% vs Aarohan 2025 baseline",
            dimensions: [
              { name: "Accommodation Redundancy", score: 88, status: "ROBUST" },
              { name: "Catering Resiliency", score: 76, status: "AT_RISK" },
              { name: "Power & Venue Redundancy", score: 82, status: "ACCEPTABLE" },
            ],
            criticalVulnerabilities: 2,
            methodology:
              "Composite harmonic mean across 6 festival dimensions penalizing single points of failure.",
          },
        }),
      });
    }

    // 11. Target screens for navigation from attention items
    if (url.includes("/api/v1/accommodation")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            summary: {
              on_campus_capacity: 710,
              external_capacity: 1434,
              total_capacity: 2144,
              placed_count: 1994,
              unplaced_count: 85,
            },
            plans: [],
            buildings: [],
            unplaced: [],
          },
        }),
      });
    }

    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: {} }),
    });
  });
}

test.describe("FestOS Operational Insight & Command Acceptance Flows (Prompt 18)", () => {
  test.beforeEach(async ({ page }) => {
    await setupInsightMocks(page);

    // Pre-populate authentication in localStorage as Director
    await page.addInitScript(() => {
      localStorage.setItem("festos_token", "mock_director_jwt_token_2026");
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

  // Acceptance Journey 1: Attention Queue Navigation & Resolution
  test("Journey 1: Open Attention Item from Overview -> Land on Fixing Screen & Snooze with Rationale", async ({
    page,
  }) => {
    // 1. Navigate to Executive Overview
    await page.goto("/dashboard");

    // Verify Executive Overview workspace renders
    await expect(page.locator('[data-testid="executive-overview-workspace"]')).toBeVisible();
    await expect(page.locator("text=FestOS Command Overview")).toBeVisible();

    // Verify KPI tiles render
    await expect(page.locator('[data-testid="kpi-tile-kpi_participants"]')).toBeVisible();
    await expect(page.locator('[data-testid="kpi-tile-kpi_beds"]')).toBeVisible();
    await expect(page.locator('[data-testid="kpi-tile-kpi_food"]')).toBeVisible();

    // Verify Prioritised Attention Queue renders
    await expect(page.locator('[data-testid="attention-queue-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="attention-item-att_01"]')).toBeVisible();

    // 2. Click Direct Action button on first attention item (action route: /accommodation)
    await page.click('[data-testid="action-btn-att_01"]');

    // 3. Verify user lands on the fixing screen (/accommodation)
    await page.waitForURL((url) => url.pathname.includes("/accommodation"));
    expect(page.url()).toContain("/accommodation");

    // 4. Return to Overview and test Snooze Flow with mandatory operational reason
    await page.goto("/dashboard");
    await expect(page.locator('[data-testid="attention-item-att_01"]')).toBeVisible();

    // Click Snooze on att_01
    await page.click('[data-testid="snooze-btn-att_01"]');

    // Verify Snooze modal opens
    await expect(page.locator('[data-testid="snooze-modal"]')).toBeVisible();
    await expect(page.locator("text=Snooze Operational Alert")).toBeVisible();

    // Fill operational rationale
    await page.fill(
      '[data-testid="snooze-reason-input"]',
      "Western Railway delayed train ETA confirmation pending; deferring bed assignment by 60m."
    );

    // Submit snooze
    await page.click('[data-testid="submit-snooze-btn"]');

    // Verify toast or updated item state
    await expect(page.locator('[data-testid="snooze-modal"]')).not.toBeVisible();
  });

  // Acceptance Journey 2: Fest Pre-Mortem Timeline Scrubber
  test("Journey 2: Timeline Scrubber -> Drag Slider to Critical Hour -> Reveal Emerging Risks in Advance", async ({
    page,
  }) => {
    // 1. Navigate to Fest Pre-Mortem
    await page.goto("/premortem");

    // Verify Pre-Mortem workspace renders
    await expect(page.locator('[data-testid="premortem-workspace"]')).toBeVisible();
    await expect(page.locator("text=Fest Pre-Mortem Simulator")).toBeVisible();

    // Verify initial timeline scrubber state (Hour 1: 06:00 UTC) has no critical risks
    await expect(page.locator('[data-testid="timeline-scrubber-card"]')).toBeVisible();
    await expect(page.locator('[data-testid="no-risks-banner"]')).toBeVisible();

    // 2. Scrub the timeline slider to Hour 30 (Day 2 Lunch: Oct 31 12:00)
    const slider = page.locator('[data-testid="timeline-slider"]');
    await expect(slider).toBeVisible();

    // Update slider value to hour index 30
    await slider.evaluate((node: HTMLInputElement) => {
      node.value = "30";
      node.dispatchEvent(new Event("change", { bubbles: true }));
    });

    // 3. Verify that scrubbed time label updates to Day 2 peak
    await expect(page.locator('[data-testid="scrubbed-time-label"]')).toContainText("Oct 31 12:00");

    // 4. Verify critical risks emerge in advance!
    await expect(page.locator('[data-testid="critical-risks-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="active-risk-risk_h30_food_spof"]')).toBeVisible();
    await expect(page.locator('[data-testid="active-risk-risk_h30_genset"]')).toBeVisible();

    // 5. Verify reactive operational panels update (Food deficit of 220 meals)
    await expect(page.locator("text=220 Deficit")).toBeVisible();

    // 6. Test Play/Pause control
    const playPauseBtn = page.locator('[data-testid="play-pause-btn"]');
    await expect(playPauseBtn).toContainText("Play Replay");
    await playPauseBtn.click();
    await expect(playPauseBtn).toContainText("Pause");
    await playPauseBtn.click();
    await expect(playPauseBtn).toContainText("Play Replay");

    // 7. Click Fest Resilience Score Pill to inspect methodology modal
    await page.click('[data-testid="resilience-score-pill"]');
    await expect(page.locator('[data-testid="methodology-modal"]')).toBeVisible();
    await expect(page.locator("text=FestOS Composite Resilience Score: 84 / 100")).toBeVisible();
    await expect(page.locator("text=Catering Resiliency")).toBeVisible();
  });

  // Acceptance Journey 3: Scenario Simulator Fork & Discard
  test("Journey 3: Director Forks Live State -> Simulates Disruption -> Compares Side-by-Side -> Discards without Modifying Live Data", async ({
    page,
  }) => {
    // 1. Navigate to Scenario Simulator
    await page.goto("/scenarios");

    // Verify Scenario Simulator workspace renders
    await expect(page.locator('[data-testid="scenario-simulator-workspace"]')).toBeVisible();
    await expect(page.locator("text=Scenario Simulator")).toBeVisible();

    // 2. Click Fork Live Database to create a new sandbox
    await page.click('[data-testid="fork-live-btn"]');
    await expect(page.locator('[data-testid="fork-modal"]')).toBeVisible();

    // Fill scenario name and description
    await page.fill('[data-testid="fork-name-input"]', "Director Emergency Flood & Evacuation Drill");
    await page.fill('[data-testid="fork-description-input"]', "Stress test sandbox for West Campus flooding");

    // Submit fork
    await page.click('[data-testid="submit-fork-btn"]');
    await expect(page.locator('[data-testid="fork-modal"]')).not.toBeVisible();

    // 3. Inject Disruption into Sandbox
    await page.click('[data-testid="apply-disruption-btn"]');
    await expect(page.locator('[data-testid="inject-disruption-modal"]')).toBeVisible();

    // Select Hostel Closure disruption
    await page.click('[data-testid="catalog-option-hostel_closure"]');
    await page.click('[data-testid="submit-disruption-btn"]');
    await expect(page.locator('[data-testid="inject-disruption-modal"]')).not.toBeVisible();

    // 4. Verify Side-by-Side Metric Comparison against Live
    await expect(page.locator('[data-testid="metrics-comparison-table"]')).toBeVisible();
    await expect(page.locator("text=Unplaced Participants")).toBeVisible();
    await expect(page.locator("text=₹42,500")).toBeVisible();

    // 5. Verify Candidate Recovery Plan is generated in sandbox
    await expect(page.locator('[data-testid="candidate-plan-card-plan_a"]')).toBeVisible();
    await expect(page.locator("text=Plan A: Cohesion-First Evacuation")).toBeVisible();

    // 6. Click Discard Scenario to destroy sandbox without touching live data
    await page.click('[data-testid="discard-scenario-btn"]');

    // Verify scenario status changes to DISCARDED
    await expect(page.locator("text=DISCARDED")).toBeVisible();
  });
});
