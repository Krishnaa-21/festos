import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";

// Pages
import ImportsPage from "../features/imports/ImportsPage";
import AssumptionsPage from "../features/assumptions/AssumptionsPage";
import ParticipantsPage from "../features/participants/ParticipantsPage";
import ContingentsPage from "../features/contingents/ContingentsPage";
import ReconciliationPage from "../features/reconciliation/ReconciliationPage";
import UnknownsPage from "../features/unknowns/UnknownsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>{ui}</ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe("Data Reconciliation & Governance UI Suite", () => {
  beforeEach(() => {
    queryClient.clear();
    localStorage.clear();
  });

  // Feature 1: Imports & Data Quality
  describe("1. Imports and Data Quality Wizard", () => {
    it("renders 5-step upload wizard, batch history, and quarantine review", async () => {
      renderWithProviders(<ImportsPage />);

      // Top Header
      expect(screen.getByText(/Import & Data Quality Management/i)).toBeInTheDocument();

      // Wizard Step 1: Detect Pack Files
      expect(screen.getByText(/Step 1: Ingest Aarohan Fest Data Pack/i)).toBeInTheDocument();
      expect(screen.getByText("participants.csv")).toBeInTheDocument();

      // Navigate to Step 2: Mapping
      const nextBtn = screen.getByText(/Continue to Mapping/i);
      fireEvent.click(nextBtn);

      expect(await screen.findByText(/Step 2: Auto-Detected Column Mapping/i)).toBeInTheDocument();
      expect(screen.getByText("contingent_id")).toBeInTheDocument();

      // Navigate to Step 3: Validation Summary
      fireEvent.click(screen.getByText(/Run Validation Check/i));
      expect(await screen.findByText(/Step 3: Ingestion Validation Summary/i)).toBeInTheDocument();

      // Navigate to Step 4: Quarantine Review
      fireEvent.click(screen.getByText(/Review Quarantine Rows/i));
      expect(await screen.findByText(/Step 4: Quarantine Review/i)).toBeInTheDocument();

      // Open Promote Modal
      const promoteBtn = screen.getByText(/Promote Valid Records \(2,833\) with Reason/i);
      fireEvent.click(promoteBtn);

      expect(await screen.findByText(/Promote Ingestion Batch to Canonical State/i)).toBeInTheDocument();
    });

    it("displays UNKNOWN heat cards with operational impact text and downloads data quality report", async () => {
      renderWithProviders(<ImportsPage />);

      // Switch to Issues & UNKNOWN Heat tab
      const issuesTab = screen.getByText(/Quality Issues & UNKNOWN Heat/i);
      fireEvent.click(issuesTab);

      // Verify UNKNOWN heat cards
      expect(await screen.findByText(/Field UNKNOWN Heat & Solver Impact/i)).toBeInTheDocument();
      expect(screen.getAllByText(/accommodation_requested/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/CRITICAL/i)[0]).toBeInTheDocument();

      // Download report button
      const downloadBtn = screen.getByTestId("download-quality-report");
      expect(downloadBtn).toBeInTheDocument();
    });
  });

  // Feature 2: Assumptions Register
  describe("2. Assumptions Register Page", () => {
    it("renders assumptions table, unverified heuristics banner, and 3 open decisions", async () => {
      renderWithProviders(<AssumptionsPage />);

      expect(screen.getByText(/Operational Assumptions Register/i)).toBeInTheDocument();
      expect(screen.getByTestId("unverified-assumptions-banner")).toBeInTheDocument();

      // Top Three Open Decisions
      expect(screen.getAllByText("external_budget_inr")[0]).toBeInTheDocument();
      expect(screen.getAllByText("late_arrival_policy")[0]).toBeInTheDocument();
      expect(screen.getAllByText("shuttle_capacity_seats")[0]).toBeInTheDocument();

      // Cleaning buffer 180 min
      expect(screen.getAllByText("cleaning_buffer_minutes")[0]).toBeInTheDocument();
      expect(screen.getByText(/180/i)).toBeInTheDocument();
    });

    it("allows inline editing with mandatory ConfirmWithReason justification", async () => {
      renderWithProviders(<AssumptionsPage />);

      // Click Edit on cleaning_buffer_minutes
      const editBtn = screen.getByTestId("edit-assumption-cleaning_buffer_minutes");
      fireEvent.click(editBtn);

      // Confirm modal opens
      expect(await screen.findByText(/Modify Assumption: cleaning_buffer_minutes/i)).toBeInTheDocument();

      const input = screen.getByTestId("input-edit-assumption-value");
      fireEvent.change(input, { target: { value: "120" } });

      const reasonInput = screen.getByTestId("reason-input");
      fireEvent.change(reasonInput, { target: { value: "Housekeeping team confirmed faster linen rotation" } });

      const saveBtn = screen.getByText(/Save & Record Audit Log/i);
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("reason-input")).not.toBeInTheDocument();
      });
    });
  });

  // Feature 3: Participants Directory & 360 Drawer
  describe("3. Participants Directory & 360 Profile", () => {
    it("renders participants with distinct tri-state and UNKNOWN badges", async () => {
      renderWithProviders(<ParticipantsPage />);

      expect(await screen.findByText(/Participant Master Directory/i)).toBeInTheDocument();
      expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();

      // Tri-state badge for accommodation
      const yesBadge = (await screen.findAllByTestId("badge-tri-yes"))[0];
      expect(yesBadge).toBeInTheDocument();
      expect(yesBadge).toHaveTextContent("YES");

      // UNKNOWN diet badge
      const unknownBadge = (await screen.findAllByTestId("badge-tri-unknown"))[0];
      expect(unknownBadge).toBeInTheDocument();
      expect(unknownBadge).toHaveTextContent("UNKNOWN");
    });

    it("opens Participant 360 drawer with 6 tabs and unmasks sensitive field via break-glass", async () => {
      renderWithProviders(<ParticipantsPage />);

      const view360Btn = await screen.findByTestId("btn-view-360-P0102");
      fireEvent.click(view360Btn);

      // Drawer opens
      expect(await screen.findByText("Participant 360")).toBeInTheDocument();

      // Check tabs
      expect(screen.getByText(/Profile & Identity/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Accommodation/i)[0]).toBeInTheDocument();
      expect(screen.getByText(/Merchandise/i)).toBeInTheDocument();
      expect(screen.getByText(/Transport/i)).toBeInTheDocument();

      // Trigger break-glass on masked phone
      const unmaskBtn = (await screen.findAllByTestId("break-glass-trigger"))[0];
      fireEvent.click(unmaskBtn);

      expect(await screen.findByText(/Emergency Break-Glass Unmasking/i)).toBeInTheDocument();
    });
  });

  // Feature 4: Contingents Matrix
  describe("4. Contingents Master & Status Breakdown", () => {
    it("renders 38 contingents grid with declared vs actual delta pills", async () => {
      renderWithProviders(<ContingentsPage />);

      expect(await screen.findByText(/Institutional Contingents Master/i)).toBeInTheDocument();
      expect(screen.getByText(/38 Active Colleges/i)).toBeInTheDocument();

      // Inspect C05 IIT Bombay card
      const c05Card = await screen.findByTestId("contingent-card-C05");
      expect(c05Card).toBeInTheDocument();
      expect(c05Card).toHaveTextContent("IIT Bombay");
      expect(c05Card).toHaveTextContent("72");
      expect(c05Card).toHaveTextContent("80");
      expect(c05Card).toHaveTextContent("-8");

      // Click card to open detail drawer
      fireEvent.click(c05Card);

      expect(await screen.findByText(/Contingent Governance/i)).toBeInTheDocument();
      expect(screen.getByText(/Declared vs Actual Strength/i)).toBeInTheDocument();
    });
  });

  // Feature 5: Reconciliation Workbench
  describe("5. Data Reconciliation Workbench", () => {
    it("renders counts panel and honest reconciliation waterfall showing 426 remainder", async () => {
      renderWithProviders(<ReconciliationPage />);

      expect(screen.getByText(/Data Reconciliation & Deduplication Workbench/i)).toBeInTheDocument();

      // 426 Unexplained Remainder
      expect(screen.getByText(/Unexplained Remainder/i)).toBeInTheDocument();
      expect(screen.getByText(/426 Excess/i)).toBeInTheDocument();
      expect(screen.getByText(/Shown, not hidden/i)).toBeInTheDocument();

      // Raw, Declared, Narrative
      expect(screen.getAllByText("2,836")[0]).toBeInTheDocument();
      expect(screen.getAllByText("2,842")[0]).toBeInTheDocument();
      expect(screen.getAllByText("2,400")[0]).toBeInTheDocument();
    });

    it("supports side-by-side compare, merge with ConfirmWithReason, and undo merge", async () => {
      renderWithProviders(<ReconciliationPage />);

      // Switch to duplicates tab
      const dupTab = screen.getByText(/Duplicate Queue/i);
      fireEvent.click(dupTab);

      // Check candidate pair
      expect((await screen.findAllByText("Aditya Verma"))[0]).toBeInTheDocument();

      // Click Compare
      const compareBtn = await screen.findByTestId("btn-compare-dup_0102a");
      fireEvent.click(compareBtn);

      expect(await screen.findByText(/Side-by-Side Duplicate Comparison/i)).toBeInTheDocument();

      // Click proceed to merge confirmation
      const proceedMergeBtn = await screen.findByTestId("btn-confirm-merge-modal");
      fireEvent.click(proceedMergeBtn);

      // ConfirmWithReason modal
      expect(await screen.findByText(/Authorize Participant Deduplication Merge/i)).toBeInTheDocument();
      const reasonInput = screen.getByTestId("reason-input");
      fireEvent.change(reasonInput, { target: { value: "Verified same participant with identical phone" } });

      const confirmBtn = screen.getByText(/Merge Records & Record Rationale/i);
      fireEvent.click(confirmBtn);

      // Wait for modal to close
      await waitFor(() => {
        expect(screen.queryByTestId("reason-input")).not.toBeInTheDocument();
      });

      // Switch to history tab and verify undo
      const historyTab = screen.getByText(/Merge History/i);
      fireEvent.click(historyTab);

      expect(await screen.findByText("mrg_abc12345")).toBeInTheDocument();
      const undoBtn = await screen.findByTestId("btn-undo-mrg_abc12345");
      fireEvent.click(undoBtn);

      expect(await screen.findByText(/Undo Merge mrg_abc12345/i)).toBeInTheDocument();
    });
  });

  // Feature 6: Unknowns Queue
  describe("6. Unknowns Burn-Down Queue", () => {
    it("renders queue ranked by count x criticality and allows inline verification", async () => {
      renderWithProviders(<UnknownsPage />);

      expect(screen.getByText(/Unknowns Burn-Down Queue/i)).toBeInTheDocument();
      expect(screen.getByText(/FestOS Rule #4: UNKNOWN is First-Class/i)).toBeInTheDocument();

      // Queue items
      expect(screen.getByText("accommodation_requested")).toBeInTheDocument();
      expect(screen.getByText("diet")).toBeInTheDocument();

      // Inline verify item
      const verifyBtn = await screen.findByTestId("btn-verify-P0001");
      fireEvent.click(verifyBtn);

      expect(await screen.findByText(/Verify UNKNOWN Field: diet/i)).toBeInTheDocument();

      // Select verified value
      const selectVal = screen.getByTestId("select-verified-value");
      fireEvent.change(selectVal, { target: { value: "VEG" } });

      const reasonText = screen.getByTestId("textarea-verify-reason");
      fireEvent.change(reasonText, { target: { value: "Participant confirmed vegetarian in person at desk" } });

      const commitBtn = screen.getByTestId("btn-submit-verify");
      fireEvent.click(commitBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("select-verified-value")).not.toBeInTheDocument();
      });
    });

    it("generates time-limited leader confirmation token and copies link", async () => {
      renderWithProviders(<UnknownsPage />);

      const linkBtn = await screen.findByTestId("btn-token-P0001");
      fireEvent.click(linkBtn);

      expect(await screen.findByText(/Leader Field Confirmation Link/i)).toBeInTheDocument();
      expect(await screen.findByTestId("btn-copy-token-link")).toBeInTheDocument();
    });
  });
});
