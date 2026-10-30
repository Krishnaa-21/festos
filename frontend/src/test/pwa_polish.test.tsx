import "fake-indexeddb/auto";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";
import { AuthContext, UserProfile } from "../features/auth/AuthContext";

import { offlineDb } from "../pwa/offlineDb";
import { parseCommandOffline } from "../features/commands/offlineParser";
import { ConflictResolutionModal } from "../components/layout/ConflictResolutionModal";
import { VolunteerMobileView } from "../features/checkin/VolunteerMobileView";
import { ReportsWorkspace, SPEC_REPORTS_20 } from "../features/reports/ReportsWorkspace";
import { CommandCenterModal } from "../features/commands/CommandCenterModal";

describe("FestOS PWA, Offline Queue & Strategic Polish (Prompt 21)", () => {
  let queryClient: QueryClient;

  const mockVolunteerUser: UserProfile = {
    id: "usr_vol_001",
    email: "volunteer@festos.internal",
    full_name: "Pooja Sharma",
    role: "VOLUNTEER",
    permissions: ["checkin:write", "merchandise:write"],
  };

  const mockDirectorUser: UserProfile = {
    id: "usr_dir_001",
    email: "director@festos.internal",
    full_name: "Dr. Devashish Roy",
    role: "FESTIVAL_DIRECTOR",
    permissions: ["*"],
  };

  beforeEach(async () => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    await offlineDb.offline_queue.clear();
    await offlineDb.cached_lookups.clear();
    await offlineDb.sync_meta.clear();
  });

  // 1. OFFLINE QUEUE (DEXIE) SAFETY TESTS
  describe("Offline Queue Safety & IndexedDB Storage", () => {
    it("successfully enqueues safe CHECK_IN operations with client_op_id and device_id", async () => {
      const op = await offlineDb.enqueueSafeOp("CHECK_IN", {
        participant_id: "P0102",
        wristband_code: "WB_889210",
        desk_operator: "Volunteer Terminal 1",
      });

      expect(op.client_op_id).toBeDefined();
      expect(op.device_id).toBeDefined();
      expect(op.op_type).toBe("CHECK_IN");
      expect(op.status).toBe("QUEUED");

      const pendingCount = await offlineDb.getPendingCount();
      expect(pendingCount).toBe(1);

      const pendingOps = await offlineDb.getPendingOps();
      expect(pendingOps[0].payload).toMatchObject({ participant_id: "P0102" });
    });

    it("successfully enqueues safe MERCHANDISE_ISSUE operations", async () => {
      const op = await offlineDb.enqueueSafeOp("MERCHANDISE_ISSUE", {
        participant_id: "P0042",
        item_id: "ITEM_TSHIRT_L",
        counter_id: "VOL_COUNTER_01",
      });

      expect(op.op_type).toBe("MERCHANDISE_ISSUE");
      expect(op.status).toBe("QUEUED");

      const count = await offlineDb.getPendingCount();
      expect(count).toBe(1);
    });

    it("strictly forbids queuing unsafe operations (overrides, allocations, approvals, merges)", async () => {
      // Attempting to queue a forbidden operation MUST throw an error
      await expect(
        offlineDb.enqueueSafeOp("OVERRIDE" as any, {
          entity_id: "HOSTEL-03",
          reason: "Emergency override",
        } as any)
      ).rejects.toThrow(/Security Violation: Only check-in and merchandise scan\/issue may be queued offline/);

      await expect(
        offlineDb.enqueueSafeOp("APPROVAL" as any, {
          approval_id: "app_123",
        } as any)
      ).rejects.toThrow();

      // Ensure nothing was written to the queue
      const count = await offlineDb.getPendingCount();
      expect(count).toBe(0);
    });

    it("handles cached lookups with encryption and wipes data on logout", async () => {
      const mockParticipantData = {
        id: "P0102",
        name: "Aarav Sharma",
        status: "APPROVED",
        room_number: "204",
      };

      await offlineDb.storeLookup("lookup:participant:P0102", mockParticipantData);

      const retrieved = await offlineDb.getLookup("lookup:participant:P0102");
      expect(retrieved.data).toEqual(mockParticipantData);
      expect(retrieved.isStale).toBe(false);

      // Wipe on logout
      await offlineDb.wipeOnLogout();
      const afterLogout = await offlineDb.getLookup("lookup:participant:P0102");
      expect(afterLogout.data).toBeNull();
    });
  });

  // 2. CONFLICT RESOLUTION MODAL TESTS
  describe("Sync Conflict Decision Screen", () => {
    it("renders conflict details with client action and server authoritative state", () => {
      const mockConflictOp: any = {
        client_op_id: "op_conflict_001",
        op_type: "CHECK_IN",
        timestamp: new Date().toISOString(),
        device_id: "dev_vol_01",
        payload: {
          participant_id: "P0102",
          wristband_code: "WB_LOCAL_99",
        },
        status: "CONFLICT",
        server_result: {
          status: "CONFLICT",
          message: "Participant already marked CHECKED_IN from North Desk with wristband WB_REMOTE_12.",
          conflict_details: {
            server_status: "Participant checked in concurrently at North Gate.",
          },
        },
        retry_count: 1,
        created_at: Date.now() - 60000,
      };

      const handleResolve = (_opId: string, _resolution: any, _reason?: string) => {};

      render(
        <ToastProvider>
          <ConflictResolutionModal
            isOpen={true}
            conflict={mockConflictOp}
            onClose={() => {}}
            onResolve={handleResolve}
          />
        </ToastProvider>
      );

      expect(screen.getByTestId("conflict-resolution-modal")).toBeInTheDocument();
      expect(screen.getByText(/Participant already marked CHECKED_IN/i)).toBeInTheDocument();
      expect(screen.getByText("P0102")).toBeInTheDocument();
      expect(screen.getByTestId("resolve-accept-server-btn")).toBeInTheDocument();
      expect(screen.getByTestId("resolve-force-override-btn")).toBeInTheDocument();
    });

    it("supports accepting server state or applying force override with mandatory rationale", async () => {
      let resolvedResolution = "";
      let resolvedReason = "";

      const mockConflictOp: any = {
        client_op_id: "op_conflict_002",
        op_type: "MERCHANDISE_ISSUE",
        timestamp: new Date().toISOString(),
        device_id: "dev_vol_01",
        payload: {
          participant_id: "P0042",
          item_id: "ITEM_TSHIRT_L",
        },
        status: "CONFLICT",
        server_result: {
          status: "CONFLICT",
          message: "Duplicate claim detected on remote desk.",
        },
        retry_count: 1,
        created_at: Date.now(),
      };

      render(
        <ToastProvider>
          <ConflictResolutionModal
            isOpen={true}
            conflict={mockConflictOp}
            onClose={() => {}}
            onResolve={(_opId, res, reason) => {
              resolvedResolution = res;
              resolvedReason = reason || "";
            }}
          />
        </ToastProvider>
      );

      // Select Force Override
      fireEvent.click(screen.getByTestId("resolve-force-override-btn"));
      const reasonInput = screen.getByTestId("conflict-override-reason");
      expect(reasonInput).toBeInTheDocument();

      // Button disabled when reason empty
      const applyBtn = screen.getByTestId("confirm-force-override-btn");
      expect(applyBtn).toBeDisabled();

      // Enter explanation
      fireEvent.change(reasonInput, {
        target: { value: "Replacement kit authorized: original kit damaged in transit" },
      });
      expect(applyBtn).not.toBeDisabled();
      fireEvent.click(applyBtn);

      expect(resolvedResolution).toBe("FORCE_OVERRIDE");
      expect(resolvedReason).toContain("damaged in transit");
    });
  });

  // 3. OFFLINE FALLBACK COMMAND PARSER TESTS
  describe("Natural-Language Command Parser (Offline Fallback)", () => {
    it("parses 'Show the impact of closing Hostel C.'", () => {
      const res = parseCommandOffline("Show the impact of closing Hostel C.");
      expect(res.intent).toBe("show_impact");
      expect(res.parameters.entity_id).toBe("Hostel C");
      expect(res.confidence).toBeGreaterThanOrEqual(0.9);
      expect(res.parser_mode).toBe("OFFLINE_FALLBACK");
      expect(res.simulated_result?.people_affected).toBe(85);
    });

    it("parses 'Find accommodation for the unplaced participants.'", () => {
      const res = parseCommandOffline("Find accommodation for the unplaced participants.");
      expect(res.intent).toBe("find_accommodation_for_unplaced");
      expect(res.parameters.plan_kind).toBe("C");
      expect(res.is_mutating).toBe(true);
    });

    it("parses 'Which events are affected by camera shortages?'", () => {
      const res = parseCommandOffline("Which events are affected by camera shortages?");
      expect(res.intent).toBe("affected_events_by_equipment");
      expect(res.parameters.item).toBe("camera");
      expect(res.simulated_result?.affected_events.length).toBeGreaterThan(0);
    });

    it("parses 'Find alternative vendors for Jain meals.'", () => {
      const res = parseCommandOffline("Find alternative vendors for Jain meals.");
      expect(res.intent).toBe("alternative_vendors_for_diet");
      expect(res.parameters.diet).toBe("Jain");
      expect(res.simulated_result?.primary_replacement).toContain("Annapurna");
    });

    it("parses 'Show the participants arriving after 10 PM.'", () => {
      const res = parseCommandOffline("Show the participants arriving after 10 PM.");
      expect(res.intent).toBe("list_late_arrivals");
      expect(res.parameters.after_time).toBe("22:00");
      expect(res.simulated_result?.total_late_arrivals).toBe(18);
    });
  });

  // 4. VOLUNTEER MOBILE VIEW TESTS
  describe("Volunteer Mobile View (Section 6.9 & Prompt 21)", () => {
    it("renders Check-In and Merchandise counter flows with giant touch targets", () => {
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ToastProvider>
              <AuthContext.Provider
                value={{
                  user: mockVolunteerUser,
                  token: "mock_vol_token",
                  isLoading: false,
                  isAuthenticated: true,
                  login: async () => {},
                  logout: async () => {},
                  hasPermission: () => true,
                  refetchUser: async () => {},
                }}
              >
                <VolunteerMobileView />
              </AuthContext.Provider>
            </ToastProvider>
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByTestId("volunteer-mobile-workspace")).toBeInTheDocument();
      expect(screen.getByTestId("volunteer-tab-checkin")).toBeInTheDocument();
      expect(screen.getByTestId("volunteer-tab-merch")).toBeInTheDocument();

      // Verify Giant Button
      expect(screen.getByTestId("volunteer-confirm-checkin-btn")).toBeInTheDocument();

      // Switch to Merchandise
      fireEvent.click(screen.getByTestId("volunteer-tab-merch"));
      expect(screen.getByTestId("volunteer-merch-flow")).toBeInTheDocument();
      expect(screen.getByTestId("volunteer-confirm-issue-btn")).toBeInTheDocument();
    });

    it("queues check-in operation into IndexedDB when submitted offline", async () => {
      // Simulate offline state
      Object.defineProperty(navigator, "onLine", { value: false, configurable: true });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ToastProvider>
              <VolunteerMobileView />
            </ToastProvider>
          </MemoryRouter>
        </QueryClientProvider>
      );

      const idInput = screen.getByTestId("volunteer-checkin-id-input");
      fireEvent.change(idInput, { target: { value: "P0999" } });

      const confirmBtn = screen.getByTestId("volunteer-confirm-checkin-btn");
      fireEvent.click(confirmBtn);

      await waitFor(async () => {
        const count = await offlineDb.getPendingCount();
        expect(count).toBe(1);
      });

      const pending = await offlineDb.getPendingOps();
      expect(pending[0].op_type).toBe("CHECK_IN");
      expect((pending[0].payload as any).participant_id).toBe("P0999");
    });
  });

  // 5. REPORTS CATALOG & SPEC SECTION 14 OUTPUTS
  describe("Section 14 Reports & Exports Catalog", () => {
    it("contains all 20 spec Section 14 outputs with descriptions and permissions", () => {
      expect(SPEC_REPORTS_20).toHaveLength(20);

      const expectedNames = [
        "reconciliation_report.csv",
        "data_quality_report.csv",
        "accommodation_plan_A.csv",
        "accommodation_plan_B.csv",
        "accommodation_plan_C.csv",
        "shortage_report.csv",
        "accommodation_summary.csv",
        "schedule_plan.csv",
        "conflicts_report.csv",
        "unscheduled_entrants.csv",
        "inventory_plan.csv",
        "equipment_gap.csv",
        "vendor_coverage.csv",
        "vendor_compliance.csv",
        "staff_coverage.csv",
        "bed_demand_timeline.csv",
        "resource_load_timeline.csv",
        "assumptions.md",
        "incident_report.csv",
        "audit_report.csv",
      ];

      for (const expectedName of expectedNames) {
        const found = SPEC_REPORTS_20.find((r) => r.name === expectedName);
        expect(found, `Expected ${expectedName} to exist in Section 14 catalog`).toBeDefined();
        expect(found?.required_permission).toBeDefined();
      }
    });

    it("renders the Reports workspace and opens preview modal with sample rows", async () => {
      const mockAuthValue: any = {
        user: mockDirectorUser,
        token: "mock_token",
        isAuthenticated: true,
        isLoading: false,
        hasPermission: () => true,
      };

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AuthContext.Provider value={mockAuthValue}>
              <ToastProvider>
                <ReportsWorkspace />
              </ToastProvider>
            </AuthContext.Provider>
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByTestId("reports-workspace")).toBeInTheDocument();
      expect(screen.getByTestId("download-bundle-btn")).toBeInTheDocument();
      expect(screen.getByTestId("report-row-reconciliation_report.csv")).toBeInTheDocument();

      // Open preview
      const previewBtn = screen.getByTestId("preview-btn-reconciliation_report.csv");
      fireEvent.click(previewBtn);

      await waitFor(() => {
        expect(screen.getByTestId("report-preview-modal")).toBeInTheDocument();
        expect(screen.getAllByText(/Participant Reconciliation & Golden Headcount/i).length).toBeGreaterThanOrEqual(1);
      });
    });

    it("renders Post-Festival Summary and Assumptions & Limitations viewer tabs", () => {
      const mockAuthValue: any = {
        user: mockDirectorUser,
        token: "mock_token",
        isAuthenticated: true,
        isLoading: false,
        hasPermission: () => true,
      };

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AuthContext.Provider value={mockAuthValue}>
              <ToastProvider>
                <ReportsWorkspace />
              </ToastProvider>
            </AuthContext.Provider>
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Switch to Post-Festival tab
      fireEvent.click(screen.getByTestId("tab-post-fest"));
      expect(screen.getByTestId("post-festival-summary-card")).toBeInTheDocument();
      expect(screen.getByText("Post-Festival Operational Summary (Spec Section 6.16)")).toBeInTheDocument();

      // Switch to Assumptions Viewer tab
      fireEvent.click(screen.getByTestId("tab-assumptions"));
      expect(screen.getByTestId("assumptions-viewer-card")).toBeInTheDocument();
      expect(screen.getByText("cleaning_buffer_minutes")).toBeInTheDocument();
      expect(screen.getByText("expected_participants_narrative")).toBeInTheDocument();
    });
  });

  // 6. AI COMMAND CENTER MODAL FLOW
  describe("AI Command Center Modal Flow", () => {
    it("renders spec suggestions, shows 'I interpreted this as...' confirmation card with editable params", async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ToastProvider>
              <AuthContext.Provider
                value={{
                  user: mockDirectorUser,
                  token: "mock_dir_token",
                  isLoading: false,
                  isAuthenticated: true,
                  login: async () => {},
                  logout: async () => {},
                  hasPermission: () => true,
                  refetchUser: async () => {},
                }}
              >
                <CommandCenterModal isOpen={true} onClose={() => {}} />
              </AuthContext.Provider>
            </ToastProvider>
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByTestId("command-center-modal")).toBeInTheDocument();
      expect(screen.getByTestId("spec-suggestion-0")).toHaveTextContent("Show the impact of closing Hostel C.");

      // Click suggestion
      fireEvent.click(screen.getByTestId("spec-suggestion-0"));

      await waitFor(() => {
        expect(screen.getByTestId("interpretation-card")).toBeInTheDocument();
        expect(screen.getByText(/I interpreted this as:/i)).toBeInTheDocument();
        expect(screen.getByTestId("param-input-entity_id")).toHaveValue("Hostel C");
      });

      // Edit parameter
      const paramInput = screen.getByTestId("param-input-entity_id");
      fireEvent.change(paramInput, { target: { value: "Hostel 3 Wing B" } });
      expect(paramInput).toHaveValue("Hostel 3 Wing B");

      // Execute command
      const execBtn = screen.getByTestId("execute-command-btn");
      fireEvent.click(execBtn);

      await waitFor(() => {
        expect(screen.getByTestId("command-results-panel")).toBeInTheDocument();
      });
    });
  });
});
