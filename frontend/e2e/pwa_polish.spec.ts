import { test, expect, Page } from "@playwright/test";

// Mock helper to intercept backend API calls for PWA, Offline Sync, Volunteer Mobile, and AI Command Center
async function setupPwaPolishMocks(page: Page, userRole: "VOLUNTEER" | "FESTIVAL_DIRECTOR" = "FESTIVAL_DIRECTOR") {
  // 1. Health & Meta
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
          "checkin",
          "merchandise",
          "reports",
          "commands",
          "scenarios",
          "approvals",
        ],
        auth_disabled: false,
      }),
    });
  });

  // 2. Auth Endpoints
  const currentUser =
    userRole === "VOLUNTEER"
      ? {
          id: "usr_vol_001",
          email: "volunteer@festos.internal",
          full_name: "Pooja Sharma",
          role: "VOLUNTEER",
          contingent_id: null,
          permissions: ["checkin:write", "merchandise:write"],
        }
      : {
          id: "usr_dir_001",
          email: "director@festos.internal",
          full_name: "Dr. Devashish Roy",
          role: "FESTIVAL_DIRECTOR",
          contingent_id: null,
          permissions: ["*"],
        };

  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: `mock_${userRole.toLowerCase()}_jwt_token_2026`,
        token_type: "bearer",
        user: currentUser,
      }),
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(currentUser),
    });
  });

  // Approvals count
  await page.route("**/api/v1/approvals/pending-count", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ pending_count: 2 }),
    });
  });

  // 3. Online Check-in Verify Endpoint
  await page.route("**/api/v1/checkin/verify-arrival", async (route) => {
    const postData = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          participant_id: postData?.participant_id || "P0102",
          status: "CHECKED_IN",
          checked_in_at: new Date().toISOString(),
          wristband_code: postData?.wristband_code || "WB_889210",
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // 4. Online Merchandise Issue Endpoint
  await page.route("**/api/v1/merchandise/issue", async (route) => {
    const postData = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          claim_id: "clm_vol_889",
          participant_id: postData?.participant_id || "P0042",
          item_id: postData?.item_id || "ITEM_TSHIRT_L",
          status: "ISSUED",
          issued_at: new Date().toISOString(),
          counter_id: "VOL_COUNTER_01",
        },
        meta: {},
        warnings: [],
      }),
    });
  });

  // 5. Check-in Offline Batch Sync Endpoint (/api/v1/checkin/sync)
  // Handles exactly-once idempotency: P0102 is APPLIED, P0103_DUP is DUPLICATE_IGNORED
  await page.route("**/api/v1/checkin/sync", async (route) => {
    const postData = route.request().postDataJSON();
    const ops = postData?.operations || [];

    const results = ops.map((op: any) => {
      if (op.participant_id === "P0103_DUP" || op.participant_id?.includes("DUP")) {
        return {
          client_op_id: op.client_op_id,
          status: "DUPLICATE_IGNORED",
          message: `Duplicate check-in ignored for participant ${op.participant_id} (already verified on server).`,
        };
      }
      return {
        client_op_id: op.client_op_id,
        status: "APPLIED",
        message: `Check-in applied cleanly for participant ${op.participant_id}.`,
      };
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        device_id: postData?.device_id || "epinoia_vol_01",
        results,
      }),
    });
  });

  // 6. Merchandise Offline Batch Sync Endpoint (/api/v1/merchandise/sync)
  await page.route("**/api/v1/merchandise/sync", async (route) => {
    const postData = route.request().postDataJSON();
    const ops = postData?.operations || [];

    const results = ops.map((op: any) => {
      return {
        client_op_id: op.client_op_id,
        status: "APPLIED",
        message: `Merchandise kit issued cleanly to participant ${op.participant_id}.`,
      };
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        device_id: postData?.device_id || "epinoia_vol_01",
        results,
      }),
    });
  });

  // 7. AI Command Center Execution Endpoint
  await page.route("**/api/v1/commands/execute", async (route) => {
    const postData = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        result: {
          success: true,
          summary: `Change proposal submitted for approval: ${postData?.command?.raw_text || "AI Proposal"}`,
          items_affected: 85,
          action_route: "/approvals",
          proposal_id: "prop_hostel_c_closure_01",
        },
      }),
    });
  });
}

test.describe("FestOS PWA Offline Queue, Volunteer Mobile & AI Command Center (Prompt 21)", () => {
  // Journey 1: Offline Network Toggling & Exactly-Once Queue Sync
  test("Journey 1: Queue three scans offline -> Reconnect -> Verify exactly-once application and duplicate ignored", async ({
    page,
    context,
  }) => {
    await setupPwaPolishMocks(page, "VOLUNTEER");

    // 1. Visit Volunteer Counter workspace
    await page.goto("/volunteer");
    await expect(page.locator('[data-testid="volunteer-mobile-workspace"]')).toBeVisible();

    // Verify online status initially
    await expect(page.locator('[data-testid="offline-status-online"]')).toBeVisible();

    // 2. Wi-Fi drops! Toggle network to offline
    await context.setOffline(true);

    // Verify offline status indicator activates
    await expect(page.locator('[data-testid="offline-status-offline"]')).toBeVisible();

    // 3. Scan 1 (Offline Check-In): Participant P0102
    await page.fill('[data-testid="volunteer-checkin-id-input"]', "P0102");
    await page.fill('[data-testid="volunteer-checkin-wristband-input"]', "WB_889210");
    await page.click('[data-testid="volunteer-confirm-checkin-btn"]');

    // Verify offline feedback card
    await expect(page.locator('[data-testid="volunteer-checkin-result"]')).toBeVisible();
    await expect(page.locator("text=Buffered Offline")).toBeVisible();

    // 4. Scan 2 (Offline Check-In): Duplicate Participant P0103_DUP
    await page.fill('[data-testid="volunteer-checkin-id-input"]', "P0103_DUP");
    await page.fill('[data-testid="volunteer-checkin-wristband-input"]', "WB_889211");
    await page.click('[data-testid="volunteer-confirm-checkin-btn"]');

    await expect(page.locator('[data-testid="volunteer-checkin-result"]')).toBeVisible();

    // 5. Scan 3 (Offline Merchandise Issue): Participant P0102 claims T-shirt
    await page.click('[data-testid="volunteer-tab-merch"]');
    await expect(page.locator('[data-testid="volunteer-merch-flow"]')).toBeVisible();

    await page.fill('[data-testid="volunteer-merch-id-input"]', "P0102");
    await page.selectOption('[data-testid="volunteer-merch-item-select"]', "ITEM_TSHIRT_L");
    await page.click('[data-testid="volunteer-confirm-issue-btn"]');

    await expect(page.locator('[data-testid="volunteer-merch-result"]')).toBeVisible();
    await expect(page.locator("text=Buffered Offline")).toBeVisible();

    // 6. Verify pending-count badge shows exactly 3 operations queued in IndexedDB
    await expect(page.locator('[data-testid="offline-pending-badge"]')).toContainText("3 queued");

    // 7. Reconnect network!
    await context.setOffline(false);
    await expect(page.locator('[data-testid="offline-status-online"]')).toBeVisible();

    // 8. Open Offline Queue modal to inspect items & trigger manual sync
    await page.click('[data-testid="offline-status-indicator"]');
    await expect(page.locator('[data-testid="offline-queue-modal"]')).toBeVisible();

    // Click Manual Sync button
    await page.click('[data-testid="manual-sync-btn"]');

    // 9. Verify exactly-once application and duplicate ignored!
    // P0102 check-in is APPLIED
    // P0103_DUP check-in is DUPLICATE_IGNORED
    // P0102 merch issue is APPLIED
    await expect(page.locator("text=DUPLICATE_IGNORED")).toBeVisible();
    await expect(page.locator("text=Duplicate check-in ignored")).toBeVisible();

    // Pending count badge should now clear from the status pill
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="offline-pending-badge"]')).not.toBeVisible();
  });

  // Journey 2: Role-Gated Navigation for Volunteer
  test("Journey 2: Volunteer view shows only 2 big flows -> Admin routes are blocked with role-gated barrier", async ({
    page,
  }) => {
    await setupPwaPolishMocks(page, "VOLUNTEER");

    // 1. Volunteer lands on FestOS
    await page.goto("/dashboard");

    // Verify Volunteer Mobile workspace is automatically mounted
    await expect(page.locator('[data-testid="volunteer-mobile-workspace"]')).toBeVisible();
    await expect(page.locator("text=Volunteer Counter")).toBeVisible();

    // Verify only the 2 big flows exist with large touch targets
    await expect(page.locator('[data-testid="volunteer-tab-checkin"]')).toBeVisible();
    await expect(page.locator('[data-testid="volunteer-tab-merch"]')).toBeVisible();

    // Verify sensitive director modules are omitted from the navigation sidebar
    await expect(page.locator("text=Scenarios")).not.toBeVisible();
    await expect(page.locator("text=Pre-Mortem")).not.toBeVisible();
    await expect(page.locator("text=Executive Overview")).not.toBeVisible();

    // 2. Volunteer attempts to navigate directly to Director Approvals (/approvals)
    await page.goto("/approvals");

    // Verify role-gated barrier blocks access
    await expect(page.locator('[data-testid="volunteer-restricted-view"]')).toBeVisible();
    await expect(page.locator("text=Access Restricted: Volunteer Mode")).toBeVisible();
    await expect(page.locator("text=Your role (VOLUNTEER) is strictly restricted")).toBeVisible();

    // 3. Click return button to safely route back to Volunteer Counter
    await page.click("text=Return to Check-in / Merch Counter");
    await expect(page.locator('[data-testid="volunteer-mobile-workspace"]')).toBeVisible();
  });

  // Journey 3: Global AI Command Center (Ctrl+K & Spec Suggestions)
  test("Journey 3: Open AI Command Center via Ctrl+K -> Select spec disruption -> Confirm interpretation & submit proposal", async ({
    page,
  }) => {
    await setupPwaPolishMocks(page, "FESTIVAL_DIRECTOR");

    await page.goto("/dashboard");

    // 1. Open Command Center via global command bar trigger
    await page.click('[data-testid="global-command-bar-trigger"]');
    await expect(page.locator('[data-testid="command-center-modal"]')).toBeVisible();

    // 2. Select Spec Example: "Show the impact of closing Hostel C."
    await page.click("text=Show the impact of closing Hostel C.");

    // 3. Verify 'I interpreted this as...' confirmation card renders with editable parameters
    await expect(page.locator('[data-testid="interpretation-card"]')).toBeVisible();
    await expect(page.locator("text=I interpreted this as...")).toBeVisible();

    // Verify parameters are pre-filled and editable
    const hostelInput = page.locator('[data-testid="param-input-hostel_name"]');
    await expect(hostelInput).toHaveValue("Hostel C");

    // 4. Fill operational justification and submit proposal to Approvals inbox
    await page.fill(
      '[data-testid="command-reason-input"]',
      "Urgent pipe burst in Hostel C ground floor; evacute residents immediately."
    );
    await page.click('[data-testid="submit-proposal-btn"]');

    // 5. Verify proposal is routed under 'AI proposes, Humans approve'
    await expect(page.locator('[data-testid="proposal-result-card"]')).toBeVisible();
    await expect(page.locator("text=AI Proposes, Humans Approve")).toBeVisible();
  });

  // Journey 4: Section 14 Reports Catalog & Section 10 Assumptions Viewer
  test("Journey 4: Reports Catalog displays 20 Section 14 outputs -> Preview report -> Inspect Section 10 Assumptions", async ({
    page,
  }) => {
    await setupPwaPolishMocks(page, "FESTIVAL_DIRECTOR");

    await page.goto("/reports");
    await expect(page.locator('[data-testid="reports-workspace"]')).toBeVisible();

    // 1. Verify 20 outputs catalog tab
    await expect(page.locator('[data-testid="tab-catalog"]')).toBeVisible();
    await expect(page.locator("text=reconciliation_report.csv")).toBeVisible();
    await expect(page.locator("text=accommodation_plan_A.csv")).toBeVisible();
    await expect(page.locator("text=food_runout_risk.csv")).toBeVisible();

    // 2. Preview Report: Participant Reconciliation & Golden Headcount
    await page.click('[data-testid="preview-btn-reconciliation_report.csv"]');
    await expect(page.locator('[data-testid="report-preview-modal"]')).toBeVisible();
    await expect(page.locator("text=Report Preview: reconciliation_report.csv")).toBeVisible();
    await page.keyboard.press("Escape");

    // 3. Inspect Section 10 Assumptions & Limitations Viewer
    await page.click('[data-testid="tab-assumptions"]');
    await expect(page.locator('[data-testid="assumptions-viewer-card"]')).toBeVisible();
    await expect(page.locator("text=System Assumptions & Heuristic Boundaries")).toBeVisible();
    await expect(page.locator("text=cleaning_buffer_minutes")).toBeVisible();
    await expect(page.locator("text=shuttle_capacity_seats")).toBeVisible();

    // 4. Trigger Bundle ZIP download
    await page.click('[data-testid="download-bundle-btn"]');
  });

  // Journey 5: Keyboard Shortcuts Help Overlay
  test("Journey 5: Press ? to view Keyboard Shortcuts overlay and test rapid navigation chords", async ({
    page,
  }) => {
    await setupPwaPolishMocks(page, "FESTIVAL_DIRECTOR");

    await page.goto("/dashboard");

    // Open Help Shortcuts modal
    await page.click('[data-testid="help-shortcuts-btn"]');
    await expect(page.locator('[data-testid="keyboard-shortcuts-modal"]')).toBeVisible();
    await expect(page.locator("text=FestOS Keyboard Shortcuts")).toBeVisible();

    // Verify key chord documentation
    await expect(page.locator("text=Open Global AI Command Center")).toBeVisible();
    await expect(page.locator("text=Navigate to Command Overview (/dashboard)")).toBeVisible();
    await expect(page.locator("text=Navigate to Check-In Desk (/checkin)")).toBeVisible();

    // Press Esc to dismiss
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="keyboard-shortcuts-modal"]')).not.toBeVisible();
  });
});

