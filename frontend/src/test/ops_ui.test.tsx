import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";
import { AuthContext } from "../features/auth/AuthContext";

// Components to test
import EventsVenuesWorkspace from "../features/events/EventsVenuesWorkspace";
import LogisticsWorkspace from "../features/logistics/LogisticsWorkspace";
import MerchandiseWorkspace from "../features/merchandise/MerchandiseWorkspace";
import FoodVendorsWorkspace from "../features/food/FoodVendorsWorkspace";
import FinanceWorkspace from "../features/finance/FinanceWorkspace";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const mockEventLeadUser = {
  id: "usr_event_lead",
  email: "event.lead@festos.internal",
  full_name: "Rohan Verma",
  role: "EVENT_LEAD",
  permissions: ["events:read", "events:write", "schedule:write"],
};

const mockVolunteerUser = {
  id: "usr_vol_01",
  email: "volunteer@festos.internal",
  full_name: "Pooja Sharma",
  role: "VOLUNTEER",
  permissions: ["merchandise:read", "merchandise:write"],
};

const mockFoodOpsUser = {
  id: "usr_food_ops",
  email: "food.ops@festos.internal",
  full_name: "Chef Rajesh",
  role: "FOOD_OPS_MANAGER",
  permissions: ["food:read", "food:write", "vendors:read", "vendors:write"],
};

const renderWithProviders = (ui: React.ReactElement, user: any = mockEventLeadUser) => {
  const authValue: any = {
    user,
    token: "mock_jwt_token",
    isAuthenticated: true,
    isLoading: false,
    login: async () => {},
    logout: () => {},
    hasPermission: (perm: string) => user.role === "FESTIVAL_DIRECTOR" || user.permissions?.includes(perm),
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

describe("Operations UI Workspaces (Prompt 12)", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  // =========================================================================
  // 1. CONFLICT PANEL & SCHEDULE WORKSPACE TESTS
  // =========================================================================
  describe("Events & Venues: Conflict Panel & Schedule Workspace", () => {
    it("renders Gantt timeline with ASSUMED badge and judge-gap indicators", async () => {
      renderWithProviders(<EventsVenuesWorkspace />, mockEventLeadUser);

      // Verify ASSUMED badge is prominently visible
      expect(await screen.findByText("ASSUMED SCHEDULE")).toBeInTheDocument();
      expect(screen.getByText("ASSUMED DRAFT")).toBeInTheDocument();

      // Verify timeline venues and sessions
      expect(await screen.findByText("Main Auditorium")).toBeInTheDocument();
      expect(screen.getByText("Aarohan Vocals Solo")).toBeInTheDocument();

      // Verify judge gap indicator
      expect(screen.getByText(/Judge Gap: 1\/2 assigned/i)).toBeInTheDocument();
    });

    it("renders conflict panel grouped by the ten conflict types with severity and affected people", async () => {
      renderWithProviders(<EventsVenuesWorkspace />, mockEventLeadUser);

      // Switch to Conflict Panel tab
      const conflictTab = await screen.findByRole("button", { name: /Conflict Panel/i });
      fireEvent.click(conflictTab);

      // Check conflict panel header
      expect(await screen.findByText(/Schedule Conflicts Engine \(10 Types Monitored\)/i)).toBeInTheDocument();

      // Verify presence of conflict types (Participant Clash, Venue Double Booking, Judge Double Booking, etc.)
      expect(screen.getAllByText(/Participant Clash/i)[0]).toBeInTheDocument();
      expect(screen.getByText(/Main Auditorium \(V01\) assigned to two concurrent sessions/i)).toBeInTheDocument();
      expect(screen.getByText(/59 people affected/i)).toBeInTheDocument();

      // Filter by type
      const typeSelect = screen.getByLabelText("Filter by conflict type");
      fireEvent.change(typeSelect, { target: { value: "PARTICIPANT_CLASH" } });

      expect(screen.getByText(/Participant P0042 \(Aarav Sharma\) double-booked/i)).toBeInTheDocument();
    });

    it("displays ranked resolution candidates and applies resolution with recorded reason", async () => {
      renderWithProviders(<EventsVenuesWorkspace />, mockEventLeadUser);

      // Switch to Conflict Panel tab
      const conflictTab = await screen.findByRole("button", { name: /Conflict Panel/i });
      fireEvent.click(conflictTab);

      // Click "Ranked Resolutions" on first conflict
      const rankedBtns = await screen.findAllByRole("button", { name: /Ranked Resolutions/i });
      fireEvent.click(rankedBtns[0]);

      // Check resolutions drawer opens with ranked candidates
      expect(await screen.findByText(/Ranked Candidates \(Evaluated by Engine\)/i)).toBeInTheDocument();
      expect(await screen.findByText(/#1/i)).toBeInTheDocument();
      expect(screen.getByText(/\+2 resolved/i)).toBeInTheDocument();
      expect(screen.getAllByText(/24 attendees affected/i).length).toBe(2);

      // Click "Apply Candidate"
      const applyBtn = screen.getAllByRole("button", { name: /Apply Candidate/i })[0];
      fireEvent.click(applyBtn);

      // Confirm with Reason modal appears
      expect(await screen.findByText(/Apply Schedule Resolution/i)).toBeInTheDocument();

      // Enter mandatory justification
      const reasonInput = screen.getByPlaceholderText(/Specify operational rationale/i);
      fireEvent.change(reasonInput, { target: { value: "Resolved clash by shifting session to 11:45" } });

      const confirmBtn = screen.getByRole("button", { name: /Apply via ChangeService/i });
      fireEvent.click(confirmBtn);

      // Toast feedback appears
      await waitFor(() => {
        expect(screen.queryByText(/Apply Schedule Resolution/i)).not.toBeInTheDocument();
      });
    });

    it("renders unscheduled entrants table with 987 count, failure reasons, and alternatives", async () => {
      renderWithProviders(<EventsVenuesWorkspace />, mockEventLeadUser);

      const unscheduledTab = await screen.findByRole("button", { name: /Unscheduled Entrants/i });
      fireEvent.click(unscheduledTab);

      expect(await screen.findByText(/Unscheduled Entrants Report \(987 Tracked Transparently\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Karan Patel/i)).toBeInTheDocument();
      expect(screen.getByText(/NOT ON SITE LONG ENOUGH/i)).toBeInTheDocument();
      expect(screen.getByText(/Schedule in Late-Arrival Wave L1/i)).toBeInTheDocument();
    });

    it("renders schedule versions with restore capability", async () => {
      renderWithProviders(<EventsVenuesWorkspace />, mockEventLeadUser);

      const versionsTab = await screen.findByRole("button", { name: /Versions & Diff/i });
      fireEvent.click(versionsTab);

      expect(await screen.findByText(/Plan Alpha \(Greedy Graph Clustered\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan Baseline \(Sequential Heuristic\)/i)).toBeInTheDocument();

      // Restore button on archived version
      const restoreBtn = screen.getByRole("button", { name: /Restore This Version/i });
      expect(restoreBtn).toBeInTheDocument();
    });

    it("renders late-wave and wildcard fairness decisions requiring Director approval", async () => {
      renderWithProviders(<EventsVenuesWorkspace />, mockEventLeadUser);

      const decisionsTab = await screen.findByRole("button", { name: /Fairness Decisions/i });
      fireEvent.click(decisionsTab);

      expect(await screen.findByText(/Late Arrival Wave on Nov 1 Morning/i)).toBeInTheDocument();
      expect(screen.getByText(/Wildcard Slot in Aarohan Vocals Finals/i)).toBeInTheDocument();
      expect(screen.getAllByText(/APPROVAL REQUIRED/i).length).toBeGreaterThan(0);
    });
  });

  // =========================================================================
  // 2. COUNTER MODE & MERCHANDISE TESTS
  // =========================================================================
  describe("Merchandise: Volunteer Counter Mode & Result States", () => {
    it("renders admin catalog with size-wise demand vs stock and policy note", async () => {
      renderWithProviders(<MerchandiseWorkspace />, mockEventLeadUser);

      // Verify Admin Catalog
      expect(await screen.findByText(/Festival T-shirt \(Size S\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Festival T-shirt \(Size XL\)/i)).toBeInTheDocument();

      // Check sizing tab and policy note
      const sizingTab = screen.getByRole("button", { name: /Demand vs Stock/i });
      fireEvent.click(sizingTab);

      expect(await screen.findByText(/Entitlement Policy & Shortage Calculation/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Shortages depend strictly on the entitlement policy/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Size M/i)).toBeInTheDocument();
      expect(screen.getAllByText(/DEFICIT/i).length).toBeGreaterThan(0);
    });

    it("volunteer counter mode: minimal fields only and camera scan / manual ID fallback", async () => {
      renderWithProviders(<MerchandiseWorkspace />, mockVolunteerUser);

      // Click to open Volunteer Counter Mode
      const counterBtn = await screen.findByRole("button", { name: /Open Volunteer Counter Mode/i });
      fireEvent.click(counterBtn);

      expect(await screen.findByText(/VOLUNTEER COUNTER MODE/i)).toBeInTheDocument();
      expect(screen.getByText(/Privacy Filter Active \(Volunteer Role\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Camera QR Scanner/i)).toBeInTheDocument();
      expect(screen.getByText(/Manual Participant ID \/ Token/i)).toBeInTheDocument();
    });

    it("volunteer counter mode: first scan displays green ISSUED result panel", async () => {
      renderWithProviders(<MerchandiseWorkspace />, mockVolunteerUser);

      const counterBtn = await screen.findByRole("button", { name: /Open Volunteer Counter Mode/i });
      fireEvent.click(counterBtn);

      // Enter manual participant ID P9901 (first issue)
      const input = screen.getByPlaceholderText(/Type ID and press Enter/i);
      fireEvent.change(input, { target: { value: "P9901" } });

      const issueBtn = screen.getByRole("button", { name: /Verify & Issue Kit/i });
      fireEvent.click(issueBtn);

      // Huge GREEN ISSUED panel is rendered
      expect(await screen.findByText("ISSUED")).toBeInTheDocument();
      expect(screen.getByText(/Item successfully handed over to attendee/i)).toBeInTheDocument();
      expect(screen.getByText("P9901")).toBeInTheDocument();
      expect(screen.getByText("counter_north_01")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Next Scan \/ Enter/i })).toBeInTheDocument();
    });

    it("volunteer counter mode: repeat scan displays red ALREADY ISSUED result panel with original timestamp, counter, and staff member", async () => {
      renderWithProviders(<MerchandiseWorkspace />, mockVolunteerUser);

      const counterBtn = await screen.findByRole("button", { name: /Open Volunteer Counter Mode/i });
      fireEvent.click(counterBtn);

      // First scan: P8801
      const input = screen.getByPlaceholderText(/Type ID and press Enter/i);
      fireEvent.change(input, { target: { value: "P8801" } });
      const issueBtn = screen.getByRole("button", { name: /Verify & Issue Kit/i });
      fireEvent.click(issueBtn);

      expect(await screen.findByText("ISSUED")).toBeInTheDocument();

      // Reset to scan next
      const nextBtn = screen.getByRole("button", { name: /Next Scan \/ Enter/i });
      fireEvent.click(nextBtn);

      // Second scan of SAME ID P8801 -> returns 409 ALREADY_ISSUED
      const input2 = screen.getByPlaceholderText(/Type ID and press Enter/i);
      fireEvent.change(input2, { target: { value: "P8801" } });
      const issueBtn2 = screen.getByRole("button", { name: /Verify & Issue Kit/i });
      fireEvent.click(issueBtn2);

      // Huge RED ALREADY ISSUED panel is rendered
      expect(await screen.findByText("ALREADY ISSUED")).toBeInTheDocument();
      expect(screen.getByText(/Duplicate scan rejected! This item was previously claimed/i)).toBeInTheDocument();
      expect(screen.getByText("counter_north_01")).toBeInTheDocument();
      expect(screen.getByText(/usr_vol_01/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Request Manager Void \/ Override/i })).toBeInTheDocument();
    });
  });

  // =========================================================================
  // 3. DIETARY COVERAGE GRID & VENDOR SHUTDOWN TESTS
  // =========================================================================
  describe("Vendors & Food: Coverage Grid & Emergency Shutdown", () => {
    it("renders dietary coverage matrix heat grid with zero-coverage cells highlighted and direct action buttons", async () => {
      renderWithProviders(<FoodVendorsWorkspace />, mockFoodOpsUser);

      expect(await screen.findByText(/Dietary Coverage Matrix \(Category x Meal Slot x Venue\)/i)).toBeInTheDocument();

      // Check zero coverage for JAIN in Amphitheatre
      expect(await screen.findByText(/ZERO COVERAGE \(Deficit: 45\)/i)).toBeInTheDocument();
      expect(screen.getAllByRole("button", { name: /Assign Vendor Immediately/i })[0]).toBeInTheDocument();

      // Check full coverage for VEG
      expect(screen.getAllByText(/FULL COVERAGE/i)[0]).toBeInTheDocument();
    });

    it("renders compliance table with expiry timeline and menu-label mismatches", async () => {
      renderWithProviders(<FoodVendorsWorkspace />, mockFoodOpsUser);

      const compTab = screen.getByRole("button", { name: /Certificates & Mismatches/i });
      fireEvent.click(compTab);

      // Menu mismatch flag
      expect(await screen.findByText(/Menu-Label Mismatch Flags/i)).toBeInTheDocument();
      expect(screen.getByText(/Declared 'Jain-Friendly' but recipe contains onion puree/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Audit \/ Fix Menu Label/i })).toBeInTheDocument();

      // Certificate expiry timeline
      expect(screen.getByText(/FSSAI Food Hygiene/i)).toBeInTheDocument();
      expect(screen.getByText("CRITICAL EXPIRING")).toBeInTheDocument();
    });

    it("executes vendor emergency shutdown with lost capacity, ranked replacements, cost delta, and notification drafts", async () => {
      renderWithProviders(<FoodVendorsWorkspace />, mockFoodOpsUser);

      const vendorsTab = screen.getByRole("button", { name: /Vendors & Commercial Rates/i });
      fireEvent.click(vendorsTab);

      expect(await screen.findByText("Annapurna Caterers")).toBeInTheDocument();
      expect(screen.getByText("Spice Junction")).toBeInTheDocument();

      // Click Emergency Shutdown on Spice Junction
      const shutdownBtns = screen.getAllByRole("button", { name: /Emergency Shutdown/i });
      fireEvent.click(shutdownBtns[1]);

      // Verify modal opens with lost capacity, cost delta, ranked replacements, and notification drafts
      expect(await screen.findByText(/Emergency Vendor Shutdown: Spice Junction/i)).toBeInTheDocument();
      expect(await screen.findByText(/-350 meals \/ slot/i)).toBeInTheDocument();
      expect(screen.getByText(/\+7,000 INR/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Royal Feast Caterers/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Approve & Dispatch Notifications/i)).toBeInTheDocument();

      // Fill in mandatory shutdown justification
      const reasonInput = screen.getByPlaceholderText(/Enter reason for shutting down this vendor/i);
      fireEvent.change(reasonInput, { target: { value: "Hygiene violation during food safety spot-check" } });

      const confirmBtn = screen.getByRole("button", { name: /Confirm Shutdown & Reassign/i });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(screen.queryByText(/Emergency Vendor Shutdown: Spice Junction/i)).not.toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 4. LOGISTICS & FINANCE WORKSPACE TESTS
  // =========================================================================
  describe("Logistics & Finance Operations", () => {
    it("logistics: renders stock table with all 7 buckets and reconciliation flags for camera and tables cases", async () => {
      renderWithProviders(<LogisticsWorkspace />, mockEventLeadUser);

      // Check stock table headers for all buckets
      expect(await screen.findByText("On Hand")).toBeInTheDocument();
      expect(screen.getByText("Reserved")).toBeInTheDocument();
      expect(screen.getByText("In Transit")).toBeInTheDocument();
      expect(screen.getByText("Damaged")).toBeInTheDocument();
      expect(screen.getByText("Under Repair")).toBeInTheDocument();
      expect(screen.getByText("Awaiting Return")).toBeInTheDocument();
      expect(screen.getByText("Available")).toBeInTheDocument();

      // Check reconciliation alert flags
      expect(await screen.findByText("CAMERA_ALL_UNDER_REPAIR")).toBeInTheDocument();
      expect(screen.getByText(/All 31 cameras across 4 locations are logged as 'under repair'/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Inspect Cameras \/ Reconcile/i })).toBeInTheDocument();

      expect(screen.getByText("TABLES_NEEDS_CHECK")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Verify Physical Condition/i })).toBeInTheDocument();
    });

    it("finance: renders budget gauge explaining budget-unset state, accommodation spend, and vendor disputes", async () => {
      renderWithProviders(<FinanceWorkspace />, mockEventLeadUser);

      // Check budget-unset state explanation
      expect(await screen.findByText(/Operating in Budget-Unset Mode/i)).toBeInTheDocument();
      expect(screen.getByText(/External accommodation budget is currently UNSET by the Festival Director/i)).toBeInTheDocument();
      expect(screen.getByText(/UNSET \(NULL\)/i)).toBeInTheDocument();

      // Accommodation spend tab
      const accomTab = screen.getByRole("button", { name: /Accommodation Spend/i });
      fireEvent.click(accomTab);

      expect(await screen.findByText("Lemon Tree Hotel")).toBeInTheDocument();
      expect(screen.getByText("Ginger Indore")).toBeInTheDocument();

      // Settlements & Disputes tab
      const settlementsTab = screen.getByRole("button", { name: /Vendor Settlements/i });
      fireEvent.click(settlementsTab);

      expect(await screen.findByText("DISPUTED")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Review Dispute/i })).toBeInTheDocument();
    });
  });
});
