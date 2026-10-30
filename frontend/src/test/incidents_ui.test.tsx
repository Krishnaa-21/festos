import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";
import { AuthContext } from "../features/auth/AuthContext";

// Components to test
import IncidentCenterWorkspace from "../features/incidents/IncidentCenterWorkspace";
import ImpactWorkspace from "../features/impact/ImpactWorkspace";
import StaffShiftsWorkspace from "../features/staff/StaffShiftsWorkspace";
import TransportSafetyWorkspace from "../features/transport/TransportSafetyWorkspace";
import NotificationsWorkspace from "../features/notifications/NotificationsWorkspace";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const mockDirectorUser = {
  id: "usr_director_01",
  email: "director@festos.internal",
  full_name: "Dr. Devashish Roy",
  role: "FESTIVAL_DIRECTOR",
  permissions: ["*"],
};

const renderWithProviders = (ui: React.ReactElement, user: any = mockDirectorUser) => {
  const authValue: any = {
    user,
    token: "mock_jwt_token",
    isAuthenticated: true,
    isLoading: false,
    login: async () => {},
    logout: () => {},
    hasPermission: () => true,
    refetchUser: async () => {},
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthContext.Provider value={authValue}>
          <ToastProvider>{ui}</ToastProvider>
        </AuthContext.Provider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe("Incident Management & Disruption Workspaces (Prompt 15)", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  // =========================================================================
  // 1. INCIDENT CENTER & PLAN COMPARISON TESTS
  // =========================================================================
  describe("Incident Center & Disruption Console", () => {
    it("renders all seven mandatory scenario cards plus extras accordion", async () => {
      renderWithProviders(<IncidentCenterWorkspace />);

      // Verify the 7 primary scenario cards exist
      expect(await screen.findByTestId("scenario-card-late_contingent")).toBeInTheDocument();
      expect(screen.getByTestId("scenario-card-duplicate_participant")).toBeInTheDocument();
      expect(screen.getByTestId("scenario-card-hostel_closure")).toBeInTheDocument();
      expect(screen.getByTestId("scenario-card-equipment_failure")).toBeInTheDocument();
      expect(screen.getByTestId("scenario-card-venue_change")).toBeInTheDocument();
      expect(screen.getByTestId("scenario-card-vendor_shutdown")).toBeInTheDocument();
      expect(screen.getByTestId("scenario-card-duplicate_merchandise_claim")).toBeInTheDocument();

      // Verify extras accordion toggle
      const extrasToggle = screen.getByTestId("toggle-extras-btn");
      expect(extrasToggle).toBeInTheDocument();
      fireEvent.click(extrasToggle);
      expect(await screen.findByTestId("scenario-extra-dining_power_outage")).toBeInTheDocument();
    });

    it("displays concurrent-incident warning banner when multiple disruptions active", async () => {
      renderWithProviders(<IncidentCenterWorkspace />);

      const banner = await screen.findByTestId("concurrent-incident-banner");
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveTextContent(/Concurrent Active Disruptions Detected/i);
    });

    it("completes guided flow: parameter form -> impact preview -> compare recovery plans side by side -> approve with ConfirmWithReason -> verification tracker", async () => {
      renderWithProviders(<IncidentCenterWorkspace />);

      // 1. Launch Hostel Closure scenario
      const launchBtn = await screen.findByTestId("launch-btn-hostel_closure");
      fireEvent.click(launchBtn);

      // 2. Parameter Form visible
      const paramForm = await screen.findByTestId("parameter-form");
      expect(paramForm).toBeInTheDocument();
      expect(paramForm).toHaveTextContent(/Hostel 3/i);

      // 3. Trigger Impact Preview (Dry Run)
      const previewBtn = screen.getByTestId("preview-impact-btn");
      fireEvent.click(previewBtn);

      // 4. Impact Preview visible
      const impactPreview = await screen.findByTestId("impact-preview");
      expect(impactPreview).toBeInTheDocument();
      expect(screen.getByTestId("preview-people-affected")).toHaveTextContent("85");

      // 5. Navigate to Recovery Plans Side by Side
      const compareBtn = screen.getByTestId("compare-plans-btn");
      fireEvent.click(compareBtn);

      // 6. Verify Side-by-side recovery plans
      const compareView = await screen.findByTestId("compare-plans-view");
      expect(compareView).toBeInTheDocument();
      expect(screen.getByTestId("plan-card-plan_a")).toBeInTheDocument();
      expect(screen.getByTestId("plan-card-plan_b")).toBeInTheDocument();
      expect(screen.getByTestId("plan-card-plan_c")).toBeInTheDocument();

      // Verify plan metrics: people moved, cost delta, constraints
      expect(screen.getByTestId("plan-card-plan_a")).toHaveTextContent("Plan A: Cohesion-First Evacuation");
      expect(screen.getByTestId("plan-card-plan_a")).toHaveTextContent("₹42,500");
      expect(screen.getByTestId("plan-card-plan_b")).toHaveTextContent("₹21,000");

      // 7. Authorize Plan with ConfirmWithReason modal
      const commitBtn = screen.getByTestId("approve-plan-btn");
      fireEvent.click(commitBtn);

      // ConfirmWithReason modal opens
      const reasonInput = await screen.findByTestId("reason-input");
      expect(reasonInput).toBeInTheDocument();

      // Enter explicit operational rationale
      fireEvent.change(reasonInput, {
        target: { value: "Authorized evacuation of Hostel 3 due to basement waterline burst." },
      });

      const confirmBtn = screen.getByTestId("confirm-button");
      expect(confirmBtn).not.toBeDisabled();
      fireEvent.click(confirmBtn);

      // 8. Verification Screen with Downstream-Update Tracker
      const verificationScreen = await screen.findByTestId("verification-screen", {}, { timeout: 4000 });
      expect(verificationScreen).toBeInTheDocument();
      expect(verificationScreen).toHaveTextContent(/Before vs After Operational State Delta/i);

      // Verify downstream subsystems tracked: Accommodation, Transport, Catering
      expect(screen.getByTestId("downstream-item-accommodation")).toBeInTheDocument();
      expect(screen.getByTestId("downstream-item-transport")).toBeInTheDocument();

      // 9. Mark downstream subsystem verified
      const verifyAccomBtn = screen.getByTestId("verify-btn-accommodation");
      fireEvent.click(verifyAccomBtn);

      await waitFor(() => {
        expect(screen.getByTestId("downstream-item-accommodation")).toHaveTextContent(/Verified/i);
      });
    });

    it("completes food vendor shutdown flow: parameter check -> 220 meals dry run -> compare plans -> approve -> verification tracker", async () => {
      renderWithProviders(<IncidentCenterWorkspace />);

      // 1. Launch Food Vendor Shutdown scenario
      const launchBtn = await screen.findByTestId("launch-btn-vendor_shutdown");
      fireEvent.click(launchBtn);

      // 2. Parameter Form visible with 220 meals
      const paramForm = await screen.findByTestId("parameter-form");
      expect(paramForm).toBeInTheDocument();
      expect(paramForm).toHaveTextContent(/Vendor VND04 \(Spice Kitchen\)/i);

      // 3. Trigger Impact Preview (Dry Run)
      const previewBtn = screen.getByTestId("preview-impact-btn");
      fireEvent.click(previewBtn);

      // 4. Impact Preview displays 220 people affected
      const impactPreview = await screen.findByTestId("impact-preview");
      expect(impactPreview).toBeInTheDocument();
      expect(screen.getByTestId("preview-people-affected")).toHaveTextContent("220");

      // 5. Navigate to Recovery Plans Side by Side
      const compareBtn = screen.getByTestId("compare-plans-btn");
      fireEvent.click(compareBtn);

      // 6. Verify Express Reallocation plan
      const compareView = await screen.findByTestId("compare-plans-view");
      expect(compareView).toBeInTheDocument();
      expect(screen.getByTestId("plan-card-plan_a")).toHaveTextContent(/Express Reallocation to Annapurna/i);
      expect(screen.getByTestId("plan-card-plan_a")).toHaveTextContent("₹35,000");

      // 7. Authorize Plan with ConfirmWithReason
      const commitBtn = screen.getByTestId("approve-plan-btn");
      fireEvent.click(commitBtn);

      const reasonInput = await screen.findByTestId("reason-input");
      fireEvent.change(reasonInput, {
        target: { value: "Authorized emergency catering transfer to Annapurna Caterers under FSSAI compliance clause." },
      });

      const confirmBtn = screen.getByTestId("confirm-button");
      fireEvent.click(confirmBtn);

      // 8. Verification Screen
      const verificationScreen = await screen.findByTestId("verification-screen", {}, { timeout: 4000 });
      expect(verificationScreen).toBeInTheDocument();
      expect(verificationScreen).toHaveTextContent(/Before vs After Operational State Delta/i);
    });
  });

  // =========================================================================
  // 2. IMPACT ANALYSIS & BLAST RADIUS TREE TESTS
  // =========================================================================
  describe("Impact Analysis & Blast Radius", () => {
    it("renders visual impact tree, entity count chips, and before-vs-after comparison", async () => {
      renderWithProviders(<ImpactWorkspace />);

      // Verify KPI count chips for entity types
      const countsBar = await screen.findByTestId("counts-by-type");
      expect(countsBar).toBeInTheDocument();
      expect(countsBar).toHaveTextContent("85"); // Participants
      expect(countsBar).toHaveTextContent("28"); // Rooms
      expect(countsBar).toHaveTextContent("Venues");

      // Verify Tree structure and expand/collapse
      expect(screen.getByTestId("impact-tree-container")).toBeInTheDocument();
      expect(screen.getByTestId("tree-node-grp_participants")).toBeInTheDocument();

      // Verify child leaf nodes
      expect(screen.getByTestId("tree-leaf-P0102")).toBeInTheDocument();
      expect(screen.getByTestId("tree-leaf-P0482")).toBeInTheDocument();

      // Verify Before vs After comparison
      const beforeAfter = screen.getByTestId("before-after-comparison");
      expect(beforeAfter).toBeInTheDocument();
      expect(beforeAfter).toHaveTextContent("Unplaced Participants");
      expect(beforeAfter).toHaveTextContent("-85");

      // Verify Collapse All and Expand All buttons
      const collapseBtn = screen.getByTestId("collapse-all-btn");
      fireEvent.click(collapseBtn);
      expect(screen.queryByTestId("tree-leaf-P0102")).not.toBeInTheDocument();

      const expandBtn = screen.getByTestId("expand-all-btn");
      fireEvent.click(expandBtn);
      expect(await screen.findByTestId("tree-leaf-P0102")).toBeInTheDocument();
    });

    it("clicking leaf node opens entity inspection drawer with allocation details", async () => {
      renderWithProviders(<ImpactWorkspace />);

      const leaf = await screen.findByTestId("tree-leaf-P0102");
      fireEvent.click(leaf);

      // Verify Drawer content
      expect(await screen.findByText(/Lakeview Resort Room 304/i)).toBeInTheDocument();
      expect(screen.getByText(/Shuttle Run S-02 Assigned/i)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // 3. STAFF & SHIFTS WORKSPACE TESTS
  // =========================================================================
  describe("Staff & Shifts Workspace", () => {
    it("renders roster grid by hour and venue with coverage heat strip and overload flags", async () => {
      renderWithProviders(<StaffShiftsWorkspace />);

      // Verify coverage heat strip slot after query resolves
      const heatSlot = await screen.findByTestId("heat-strip-slot-12:00");
      expect(heatSlot).toBeInTheDocument();
      expect(heatSlot).toHaveTextContent("GAP");

      // Verify shift cells in grid
      expect(await screen.findByTestId("shift-cell-SH-08-AUD")).toBeInTheDocument();
      expect(await screen.findByTestId("shift-cell-SH-12-REG")).toBeInTheDocument();

      // Verify overload and overlap flags
      const overloadFlags = await screen.findAllByTestId("overload-flag");
      expect(overloadFlags.length).toBeGreaterThan(0);
      const overlapFlags = await screen.findAllByTestId("overlap-flag");
      expect(overlapFlags.length).toBeGreaterThan(0);

      // Verify Missing Handover warning
      expect(await screen.findByTestId("missing-handover-banner")).toBeInTheDocument();
    });

    it("opens emergency replace modal with ranked candidates and enforces handover note", async () => {
      renderWithProviders(<StaffShiftsWorkspace />);

      // Click overloaded shift
      const shiftCell = await screen.findByTestId("shift-cell-SH-12-REG");
      fireEvent.click(shiftCell);

      // Verify modal opens with ranked candidates
      const modal = await screen.findByTestId("emergency-replace-modal");
      expect(modal).toBeInTheDocument();
      const candOption = await screen.findByTestId("candidate-option-STF06");
      expect(candOption).toHaveTextContent("Sunita Reddy");
      expect(candOption).toHaveTextContent("94%");

      // Attempt submit without handover note: button is disabled
      const confirmBtn = screen.getByTestId("confirm-replace-btn");
      expect(confirmBtn).toBeDisabled();

      // Enter mandatory handover note
      const handoverInput = screen.getByTestId("handover-note-input");
      fireEvent.change(handoverInput, { target: { value: "Replacement volunteer oriented on scanner." } });
      expect(confirmBtn).not.toBeDisabled();

      // Click replace
      fireEvent.click(confirmBtn);
      await waitFor(() => {
        expect(screen.queryByTestId("emergency-replace-modal")).not.toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 4. TRANSPORTATION & SAFETY WORKSPACE TESTS
  // =========================================================================
  describe("Transportation & Safety Workspace", () => {
    it("renders ASSUMED parameter banner, shuttle demand table, and plain-language alerts", async () => {
      renderWithProviders(<TransportSafetyWorkspace />);

      // Verify ASSUMED parameter banner
      const banner = await screen.findByTestId("assumed-parameter-banner");
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveTextContent(/ASSUMED PARAMETERS/i);
      expect(banner).toHaveTextContent(/12 seats/i);

      // Verify safety coverage tiles after query resolves
      const tiles = screen.getByTestId("safety-coverage-tiles");
      expect(tiles).toHaveTextContent("186");
      expect(tiles).toHaveTextContent("168");

      // Verify plain-language transport alert
      const alertItem = await screen.findByTestId("transport-alert-ALT-01");
      expect(alertItem).toHaveTextContent(/14 participants are scheduled to leave Lakeview at midnight/i);

      // Verify shuttle table row
      const shuttleRow = await screen.findByTestId("shuttle-row-SP-01");
      expect(shuttleRow).toHaveTextContent("Lakeview Resort");
      expect(shuttleRow).toHaveTextContent("14 SEATS SHORT");
    });

    it("verifies night safety escorts and guardian queue approvals", async () => {
      renderWithProviders(<TransportSafetyWorkspace />);

      // 1. Switch to Night Safety tab
      const nightTab = await screen.findByTestId("tab-night-safety");
      fireEvent.click(nightTab);

      const nightView = await screen.findByTestId("night-safety-view");
      expect(nightView).toBeInTheDocument();
      expect(await screen.findByTestId("night-roster-row-NR-02")).toHaveTextContent("Isha Malhotra");

      // Toggle verification
      const verifyToggle = screen.getByTestId("toggle-verify-btn-NR-02");
      fireEvent.click(verifyToggle);

      // 2. Switch to Guardian Approvals tab
      const guardianTab = screen.getByTestId("tab-guardians");
      fireEvent.click(guardianTab);

      const guardianView = await screen.findByTestId("guardian-queue-view");
      expect(guardianView).toBeInTheDocument();
      expect(await screen.findByTestId("guardian-row-GQ-01")).toHaveTextContent("Isha Malhotra");
      expect(screen.getByTestId("guardian-row-GQ-01")).toHaveTextContent("Lakeview Resort");
    });
  });

  // =========================================================================
  // 5. NOTIFICATIONS BROADCAST WORKSPACE TESTS
  // =========================================================================
  describe("Notifications Broadcast Workspace", () => {
    it("renders drafts inbox grouped by audience, supports mock-send, and updates delivery log", async () => {
      renderWithProviders(<NotificationsWorkspace />);

      // Verify drafts list loads
      const draftCard01 = await screen.findByTestId("draft-card-ND-01");
      expect(draftCard01).toBeInTheDocument();
      expect(draftCard01).toHaveTextContent("Contingent Leaders");
      expect(screen.getByTestId("draft-card-ND-03")).toHaveTextContent("Food Vendors");

      // Filter by Leaders audience
      const leaderFilter = screen.getByTestId("filter-leaders");
      fireEvent.click(leaderFilter);
      expect(screen.getByTestId("draft-card-ND-01")).toBeInTheDocument();
      expect(screen.queryByTestId("draft-card-ND-03")).not.toBeInTheDocument();

      // Reset to all
      fireEvent.click(screen.getByTestId("filter-all"));

      // Mock-Send draft ND-01
      const mockSendBtn = screen.getByTestId("mock-send-btn-ND-01");
      fireEvent.click(mockSendBtn);

      await waitFor(() => {
        expect(screen.getByTestId("draft-card-ND-01")).toHaveTextContent(/Dispatched/i);
      });

      // Switch to Delivery Log
      const logTab = screen.getByTestId("tab-delivery-log");
      fireEvent.click(logTab);

      const deliveryLog = await screen.findByTestId("delivery-log-view");
      expect(deliveryLog).toBeInTheDocument();
      expect(await screen.findByTestId("log-entry-DL-01")).toHaveTextContent("Accommodation Coordinators");
    });
  });
});
