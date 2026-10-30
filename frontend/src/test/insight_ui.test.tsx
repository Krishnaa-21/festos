import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";
import { AuthContext } from "../features/auth/AuthContext";

// Workspaces
import ExecutiveOverview from "../features/dashboard/ExecutiveOverview";
import ScenarioSimulatorWorkspace from "../features/scenarios/ScenarioSimulatorWorkspace";
import FestPreMortemWorkspace from "../features/premortem/FestPreMortemWorkspace";
import UnknownsPage from "../features/unknowns/UnknownsPage";
import ForecastingWorkspace from "../features/forecasting/ForecastingWorkspace";
import DecisionLogWorkspace from "../features/decisions/DecisionLogWorkspace";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const mockDirectorUser = {
  id: "usr_dir_001",
  email: "director@festos.internal",
  full_name: "Dr. Devashish Roy",
  role: "FESTIVAL_DIRECTOR",
  permissions: ["*"],
};

const renderWithProviders = (
  ui: React.ReactElement,
  route: string = "/",
  user: any = mockDirectorUser
) => {
  const authValue: any = {
    user,
    token: "mock_jwt_token_2026",
    isAuthenticated: true,
    isLoading: false,
    login: async () => {},
    logout: () => {},
    hasPermission: () => true,
    refetchUser: async () => {},
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthContext.Provider value={authValue}>
          <ToastProvider>{ui}</ToastProvider>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe("FestOS Insight & Strategic Workspaces (Prompt 18)", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  // =========================================================================
  // 1. OVERVIEW & ATTENTION QUEUE RANKING TESTS
  // =========================================================================
  describe("Command Overview & Prioritised Attention Queue", () => {
    it("renders all spec KPI metric tiles and clickable links into modules", async () => {
      renderWithProviders(<ExecutiveOverview />);

      // Verify spec KPI tiles load
      expect(await screen.findByTestId("kpi-tile-kpi_participants")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_accommodation")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_schedule")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_logistics")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_merchandise")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_food")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_staff")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-tile-kpi_governance")).toBeInTheDocument();

      // Check specific values
      expect(screen.getByTestId("kpi-tile-kpi_participants")).toHaveTextContent(/2,836/);
      expect(screen.getByTestId("kpi-tile-kpi_food")).toHaveTextContent("DEGRADED");
    });

    it("ranks attention items strictly by Severity x Urgency x max(people_affected, 1)", async () => {
      renderWithProviders(<ExecutiveOverview />);

      const attentionSection = await screen.findByTestId("attention-queue-section");
      expect(attentionSection).toBeInTheDocument();

      // Dietary shortage item (Score: 3520) should rank #1
      const item02 = await screen.findByTestId("attention-item-att_02");
      expect(item02).toBeInTheDocument();
      expect(item02).toHaveTextContent(/#1/);
      expect(item02).toHaveTextContent(/220 Jain & Vegan lunch meals/i);

      // Bed shortage item (Score: 1360) should rank #2
      const item03 = await screen.findByTestId("attention-item-att_03");
      expect(item03).toBeInTheDocument();
      expect(item03).toHaveTextContent(/85 Participants stranded in Hostel 3/i);

      // Verify direct action button
      const actionBtn = screen.getByTestId("action-btn-att_02");
      expect(actionBtn).toHaveTextContent("Reallocate to Annapurna →");
    });

    it("enforces mandatory operational rationale to snooze or acknowledge an alert", async () => {
      renderWithProviders(<ExecutiveOverview />);

      const snoozeBtn = await screen.findByTestId("snooze-btn-att_01");
      fireEvent.click(snoozeBtn);

      // Modal opens
      const modal = await screen.findByTestId("snooze-modal");
      expect(modal).toBeInTheDocument();

      const confirmBtn = screen.getByTestId("confirm-snooze-btn");
      expect(confirmBtn).toBeDisabled();

      // Enter rationale
      const reasonInput = screen.getByTestId("snooze-reason-input");
      fireEvent.change(reasonInput, {
        target: { value: "Floor warden contacted. Ground floor rooms 101-103 reserved." },
      });
      expect(confirmBtn).not.toBeDisabled();

      fireEvent.click(confirmBtn);
      await waitFor(() => {
        expect(screen.queryByTestId("snooze-modal")).not.toBeInTheDocument();
      });
    });

    it("renders Volunteer mobile home variant with no sensitive governance or masked data", async () => {
      renderWithProviders(<ExecutiveOverview />);

      const volunteerTab = await screen.findByTestId("role-tab-VOLUNTEER");
      fireEvent.click(volunteerTab);

      // Volunteer mobile view rendered
      const volView = await screen.findByTestId("volunteer-mobile-view");
      expect(volView).toBeInTheDocument();
      expect(volView).toHaveTextContent(/Registration Concourse Desk/i);
      expect(volView).toHaveTextContent(/Aarav Sharma/i);

      // Governance KPI tiles should be hidden
      expect(screen.queryByTestId("kpi-tiles-grid")).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 2. RISK HEATMAP & DRILLDOWN TESTS
  // =========================================================================
  describe("Risk Heatmap (Severity x Time-to-Impact)", () => {
    it("renders 2D heatmap matrix and opens drill-down drawer upon clicking cell", async () => {
      renderWithProviders(<ExecutiveOverview />);

      // Cell for CRITICAL x 1-4h should contain active items
      await waitFor(() => {
        expect(screen.getByTestId("heatmap-cell-CRITICAL-1-4h")).toHaveTextContent("3");
      });

      // Click cell to drill down
      const cell = screen.getByTestId("heatmap-cell-CRITICAL-1-4h");
      fireEvent.click(cell);

      const drawer = await screen.findByTestId("drilldown-drawer");
      expect(drawer).toBeInTheDocument();
      expect(drawer).toHaveTextContent(/220 Jain & Vegan lunch meals/i);
      expect(drawer).toHaveTextContent(/85 Participants stranded in Hostel 3/i);
    });
  });

  // =========================================================================
  // 3. SCENARIO SIMULATOR TESTS
  // =========================================================================
  describe("Scenario Simulator Workspace", () => {
    it("renders side-by-side metric comparison between live production and sandbox", async () => {
      renderWithProviders(<ScenarioSimulatorWorkspace />);

      const scenName = await screen.findByTestId("current-scenario-name");
      expect(scenName).toBeInTheDocument();
      expect(scenName).toHaveTextContent("Hostel 3 Emergency Evacuation Sandbox");

      const comparisonTable = screen.getByTestId("metrics-comparison-table");
      expect(comparisonTable).toBeInTheDocument();
      expect(comparisonTable).toHaveTextContent("Unplaced Participants");
      expect(comparisonTable).toHaveTextContent("-85"); // delta
      expect(comparisonTable).toHaveTextContent("+₹42,500");

      // Verify candidate recovery plan
      const planA = screen.getByTestId("plan-card-plan_a");
      expect(planA).toBeInTheDocument();
      expect(planA).toHaveTextContent("Plan A: Cohesion-First Evacuation");
      expect(planA).toHaveTextContent("RECOMMENDED");
    });

    it("displays stale-fork warning when live state has mutated since fork", async () => {
      renderWithProviders(<ScenarioSimulatorWorkspace />);

      // Open drawer to select stale demo scenario
      const drawerBtn = await screen.findByTestId("parallel-scenarios-btn");
      fireEvent.click(drawerBtn);

      const staleItem = await screen.findByTestId("scenario-list-item-scen_stale_demo");
      fireEvent.click(staleItem);

      // Stale fork warning banner visible
      const warning = await screen.findByTestId("stale-fork-warning");
      expect(warning).toBeInTheDocument();
      expect(warning).toHaveTextContent(/Live Database Has Mutated Since Fork Creation/i);
      expect(warning).toHaveTextContent(/4 mutations/i);
    });

    it("allows discarding a scenario sandbox without touching live data", async () => {
      renderWithProviders(<ScenarioSimulatorWorkspace />);

      const discardBtn = await screen.findByTestId("discard-scenario-btn");
      expect(discardBtn).toBeInTheDocument();
      fireEvent.click(discardBtn);

      // Verify toast feedback
      await waitFor(() => {
        expect(screen.getByText(/Scenario Discarded/i)).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 4. FEST PRE-MORTEM & TIMELINE SCRUBBER TESTS
  // =========================================================================
  describe("Fest Pre-Mortem Timeline Scrubber", () => {
    it("advancing the scrubber slider to a critical hour reveals emerging risks in advance", async () => {
      renderWithProviders(<FestPreMortemWorkspace />);

      // Initial hour: no critical risks at hour 0
      const initialTime = await screen.findByTestId("scrubbed-time-label");
      expect(initialTime).toHaveTextContent(/10-30 06:00/);
      expect(screen.getByTestId("no-risks-banner")).toBeInTheDocument();

      // Drag scrubber to Hour 30 (Day 2 Lunch - index 30)
      const slider = screen.getByTestId("timeline-slider");
      fireEvent.change(slider, { target: { value: "30" } });

      // Verify scrubbed time updated
      expect(screen.getByTestId("scrubbed-time-label")).toHaveTextContent(/10-31 12:00/);

      // Verify critical risks revealed dynamically
      expect(await screen.findByTestId("active-risk-risk_h30_food_spof")).toBeInTheDocument();
      expect(screen.getByTestId("active-risk-risk_h30_generator")).toBeInTheDocument();
      expect(screen.getByText(/Spice Kitchen shutdown creates 220 Jain meal gap/i)).toBeInTheDocument();
      expect(screen.getByText(/Main Auditorium Generator G01 thermal trip risk/i)).toBeInTheDocument();

      // Verify dynamic reactive operational panels update
      const foodPanel = screen.getByTestId("panel-food-demand");
      expect(foodPanel).toHaveTextContent("Dietary Gap: 220 Jain/Vegan packs unassigned!");
      const powerPanel = screen.getByTestId("panel-equipment-demand");
      expect(powerPanel).toHaveTextContent("SHORTAGE");
    });

    it("renders SPOF list with vulnerability analysis and mitigation links", async () => {
      renderWithProviders(<FestPreMortemWorkspace />);

      const spofTab = await screen.findByTestId("tab-spof");
      fireEvent.click(spofTab);

      const spofView = await screen.findByTestId("spof-list-view");
      expect(spofView).toBeInTheDocument();
      expect(screen.getByTestId("spof-card-spof_01")).toHaveTextContent("Main Auditorium Master Generator G01");
      expect(screen.getByTestId("spof-card-spof_02")).toHaveTextContent("Spice Kitchen (VND04) - West Campus");
      expect(screen.getByTestId("spof-card-spof_01")).toHaveTextContent("850 People At Risk");
    });

    it("displays Fest Resilience score and methodology modal", async () => {
      renderWithProviders(<FestPreMortemWorkspace />);

      const resiliencePill = await screen.findByTestId("resilience-score-pill");
      expect(resiliencePill).toBeInTheDocument();
      expect(resiliencePill).toHaveTextContent("78");
      expect(resiliencePill).toHaveTextContent("MODERATE RESILIENCE");

      // Click to open methodology modal
      fireEvent.click(resiliencePill);
      const modal = await screen.findByTestId("methodology-modal");
      expect(modal).toBeInTheDocument();
      expect(screen.getByText(/FestOS Weighted Resilience Scoring/i)).toBeInTheDocument();
      expect(modal).toHaveTextContent(/Constraint Ladder Rule/i);
    });
  });

  // =========================================================================
  // 5. UNKNOWNS BURN-DOWN & WHY-NOT? TESTS
  // =========================================================================
  describe("Unknowns Burn-down & Why-Not? Deep-Link", () => {
    it("renders ranked unknown queue with computed gains and method labels", async () => {
      renderWithProviders(<UnknownsPage />);

      const accomCard = await screen.findByTestId("queue-card-accommodation_requested");
      expect(accomCard).toBeInTheDocument();
      expect(accomCard).toHaveTextContent("DIRECT_LEADER_SMS");
      expect(accomCard).toHaveTextContent("+418 beds de-risked");

      const dietCard = await screen.findByTestId("queue-card-diet");
      expect(dietCard).toBeInTheDocument();
      expect(dietCard).toHaveTextContent("WHATSAPP_LINK");
      expect(dietCard).toHaveTextContent("+394 dietary clearances");

      // Before/after burn-down panel
      const beforeAfter = screen.getByTestId("before-after-panel");
      expect(beforeAfter).toBeInTheDocument();
      expect(beforeAfter).toHaveTextContent("Burn-Down Certainty Index: 78%");
    });

    it("displays Why-not? deep-link analysis for unplaced participants", async () => {
      renderWithProviders(<UnknownsPage />, "/unknowns?why_not=unplaced&participant_id=P0102");

      const whyNotPanel = await screen.findByTestId("why-not-panel");
      expect(whyNotPanel).toBeInTheDocument();
      expect(whyNotPanel).toHaveTextContent(/Root Cause Analysis for Unplaced Participants/i);
      expect(whyNotPanel).toHaveTextContent(/accommodation_requested = UNKNOWN/);
      expect(whyNotPanel).toHaveTextContent(/gender = UNKNOWN/);
      expect(whyNotPanel).toHaveTextContent(/Gender Corridor Safety Barrier/);
    });
  });

  // =========================================================================
  // 6. FORECASTING & DECISION LOG TESTS
  // =========================================================================
  describe("Forecasting & Decision Log Workspaces", () => {
    it("renders forecasting charts with PROJECTION vs ASSUMPTION legend and editable assumption pill", async () => {
      renderWithProviders(<ForecastingWorkspace />);

      const legend = await screen.findByTestId("projection-vs-assumption-legend");
      expect(legend).toBeInTheDocument();
      expect(legend).toHaveTextContent("PROJECTION");
      expect(legend).toHaveTextContent("ASSUMPTION");

      // Editable assumption pill
      const editPill = await screen.findByTestId("edit-assumption-pill-cleaning_buffer_minutes");
      expect(editPill).toBeInTheDocument();
      expect(editPill).toHaveTextContent("cleaning_buffer_minutes=180min");

      // Click pill to open assumption edit modal
      fireEvent.click(editPill);
      const editModal = await screen.findByTestId("edit-assumption-modal");
      expect(editModal).toBeInTheDocument();
      expect(screen.getByTestId("assumption-value-input")).toHaveValue("180");
    });

    it("renders decision log with approver and cost columns, opening Why Card drawer", async () => {
      renderWithProviders(<DecisionLogWorkspace />);

      const table = await screen.findByTestId("decisions-table");
      expect(table).toBeInTheDocument();

      // Check rows
      const row01 = screen.getByTestId("decision-row-DEC-2026-001");
      expect(row01).toHaveTextContent("Dr. Devashish Roy");
      expect(row01).toHaveTextContent("₹42,500");
      expect(row01).toHaveTextContent("85p");

      // Click Why button
      const whyBtn = screen.getByTestId("why-card-btn-DEC-2026-001");
      fireEvent.click(whyBtn);

      const drawer = await screen.findByTestId("why-card-drawer");
      expect(drawer).toBeInTheDocument();
      expect(drawer).toHaveTextContent(/Hard Constraints Satisfied/i);
      expect(drawer).toHaveTextContent(/Gender-separated corridors enforced/i);
      expect(drawer).toHaveTextContent(/Soft Constraints Relaxed/i);
      expect(drawer).toHaveTextContent(/Proximity ladder: Campus vs External/i);
      expect(drawer).toHaveTextContent(/Alternatives Rejected/i);
      expect(drawer).toHaveTextContent(/Plan B: Cost-First Dispersal/i);
    });
  });
});
