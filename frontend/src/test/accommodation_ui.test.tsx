import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";
import { AuthContext } from "../features/auth/AuthContext";

// Components to test
import AccommodationWorkspace from "../features/accommodation/AccommodationWorkspace";
import ShortageView from "../features/accommodation/ShortageView";
import OccupancyMap from "../features/accommodation/OccupancyMap";
import DecisionFlowModal from "../features/accommodation/DecisionFlowModal";
import CheckInDesk from "../features/checkin/CheckInDesk";
import ParticipantAccommodationTab from "../features/accommodation/ParticipantAccommodationTab";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const mockUserAccommodationLead = {
  id: "usr_accom_lead",
  email: "accom.lead@festos.internal",
  full_name: "Anita Desai",
  role: "ACCOMMODATION_LEAD",
  permissions: ["accommodation:read", "accommodation:write"],
};

const mockUserFestivalDirector = {
  id: "usr_director",
  email: "director@festos.internal",
  full_name: "Festival Director",
  role: "FESTIVAL_DIRECTOR",
  permissions: ["*"],
};

const renderWithProviders = (
  ui: React.ReactElement,
  user: any = mockUserAccommodationLead
) => {
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

describe("Accommodation & Check-in Desk UI Suite (p3/09-ui-accom)", () => {
  beforeEach(() => {
    queryClient.clear();
    localStorage.clear();
  });

  // Feature 1: Accommodation Workspace & Plan Comparison
  describe("1. Accommodation Workspace & Candidate Plan Generator", () => {
    it("renders workspace header, budget-unset warning banner, and compare table", async () => {
      renderWithProviders(<AccommodationWorkspace />);

      // Header
      expect(screen.getByText(/Accommodation Workspace/i)).toBeInTheDocument();

      // Budget-unset banner
      expect(await screen.findByTestId("budget-unset-banner")).toBeInTheDocument();
      expect(screen.getByText(/External Accommodation Budget is Unset \(NULL\)/i)).toBeInTheDocument();

      // Side-by-side plan compare table
      expect(await screen.findByText(/Side-by-Side Candidate Plan Comparison/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan A: Cohesion-First/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan B: Cost-First/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan C: Balanced \(Recommended\)/i)).toBeInTheDocument();

      // Metrics in compare rows
      expect(screen.getByText(/On-Campus Placed/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Contingent Splits/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Total External Cost/i)).toBeInTheDocument();
      expect(screen.getByText(/Plain-Language Sacrifice Explanation/i)).toBeInTheDocument();
    });

    it("allows selecting plan kind, adjusting parameters, and generating new candidate plan", async () => {
      renderWithProviders(<AccommodationWorkspace />);

      // Switch to Plan A
      const planABtn = await screen.findByTestId("plan-a-btn");
      fireEvent.click(planABtn);

      // Trigger Generator Solver
      const generateBtn = screen.getByTestId("generate-plan-btn");
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(screen.getByText(/Run Solver for Plan A/i)).toBeInTheDocument();
      });
    });

    it("renders Recharts cost-versus-cohesion trade-off chart with trade-off summaries", async () => {
      renderWithProviders(<AccommodationWorkspace />);

      expect(
        await screen.findByText(/Cost-versus-Cohesion Trade-Off Chart/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Plan A: Maximum Unity/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan B: Minimum Cost/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan C: Pareto Optimal/i)).toBeInTheDocument();
    });

    it("allows committing plan to live with ConfirmWithReason", async () => {
      renderWithProviders(<AccommodationWorkspace />);

      const commitBtn = await screen.findByTestId("commit-live-btn");
      fireEvent.click(commitBtn);

      // ConfirmWithReason dialog
      expect(screen.getByText(/Commit Accommodation Plan to LIVE Operational Status/i)).toBeInTheDocument();
      const reasonInput = screen.getByTestId("reason-input");
      fireEvent.change(reasonInput, { target: { value: "Authorized after Finance Lead joint review" } });

      const confirmBtn = screen.getByText(/Commit & Authorize Live Plan/i);
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(screen.getByText(/LIVE OPERATIONAL PLAN ACTIVE/i)).toBeInTheDocument();
      });
    });
  });

  // Feature 2: Shortage View & "Why-not?" Explainable Diagnostics
  describe("2. Shortage View & Explainable Why-not? Panel", () => {
    it("renders unplaced delegates grouped by blocking bottlenecks", async () => {
      renderWithProviders(<ShortageView />);

      // Bottleneck category cards
      expect(await screen.findByText(/Gender Unknown \(Safety Gate #2\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Ground-Floor Accessible Room Deficit/i)).toBeInTheDocument();
      expect(screen.getByText(/External Property Room Exhaustion/i)).toBeInTheDocument();
      expect(screen.getByText(/Minor Participant Off-Campus Restriction/i)).toBeInTheDocument();
    });

    it("opens Why-not? diagnostic drawer with root cause, counterfactual impact, and quick verify", async () => {
      renderWithProviders(<ShortageView />);

      // Find Sneha Mukherjee Why-not button
      const whyNotBtn = await screen.findByTestId("why-not-P0104");
      fireEvent.click(whyNotBtn);

      // Panel contents
      expect(await screen.findByText(/Why-not\? Unplaced Diagnosis Panel/i)).toBeInTheDocument();
      expect(screen.getByText(/Rule 2: Gender-Appropriate Allocation & Safety Policy/i)).toBeInTheDocument();
      expect(screen.getByText(/Gender attribute is UNKNOWN in raw import dataset/i)).toBeInTheDocument();
      expect(screen.getByText(/Counterfactual Resolution \(What changes if confirmed\)/i)).toBeInTheDocument();

      // Quick verify button
      const verifyFemaleBtn = screen.getByText(/Verify as Female/i);
      expect(verifyFemaleBtn).toBeInTheDocument();
      fireEvent.click(verifyFemaleBtn);
    });
  });

  // Feature 3: Occupancy Map
  describe("3. Occupancy Map & Bed Status Visualization", () => {
    const mockOccupancy = {
      blocks: [
        {
          block_id: "H3",
          name: "Hostel 3 (Boys Block)",
          gender_class: "boys" as const,
          total_beds: 360,
          occupied_beds: 348,
          cleaning_beds: 6,
          closed_beds: 2,
          free_beds: 4,
          floors: [
            {
              floor_number: 0,
              is_ground: true,
              rooms: [
                {
                  room_id: "H3-101",
                  room_number: "101",
                  accessible: true,
                  status: "AVAILABLE" as const,
                  cleaning_status: "READY" as const,
                  beds: [
                    {
                      bed_id: "H3-101-A",
                      status: "OCCUPIED" as const,
                      contingent_id: "C05",
                      contingent_name: "IIT Bombay",
                      contingent_color: "#6366f1",
                      participant_id: "P0103",
                      participant_name: "Rohan Deshmukh",
                      is_leader: true,
                      version: 1,
                    },
                    {
                      bed_id: "H3-101-B",
                      status: "FREE" as const,
                      version: 1,
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
      external_properties: [
        {
          property_id: "ext_01",
          name: "Radisson Blu Rau",
          total_beds: 200,
          occupied_beds: 184,
          free_beds: 16,
          cost_per_bed_night: 2800,
          distance_km: 11.5,
          accessibility_verified: false,
          gender_suitability_verified: false,
          transport_limited: true,
        },
      ],
    };

    it("displays blocks, floors, explicit text bed status badges, leader indicators, and external properties with UNVERIFIED badges", () => {
      renderWithProviders(<OccupancyMap occupancyData={mockOccupancy} />);

      // Block tab
      expect(screen.getByText("Hostel 3 (Boys Block)")).toBeInTheDocument();

      // Floor 0
      expect(screen.getByText(/Floor 0 \(Ground Floor\)/i)).toBeInTheDocument();
      expect(screen.getByText(/WHEELCHAIR RAMP ACCESS/i)).toBeInTheDocument();

      // Bed statuses (non-colour-only text badges)
      expect(screen.getAllByText("FREE").length).toBeGreaterThan(0);
      expect(screen.getAllByText("OCCUPIED").length).toBeGreaterThan(0);

      // Leader proximity badge
      expect(screen.getByText(/LEADER ROOM/i)).toBeInTheDocument();
      expect(screen.getByText("Rohan Deshmukh")).toBeInTheDocument();

      // External property cards with UNVERIFIED badges
      expect(screen.getByText("Radisson Blu Rau")).toBeInTheDocument();
      expect(screen.getByText(/Accessibility:/i)).toBeInTheDocument();
      expect(screen.getByText(/Gender Suitability:/i)).toBeInTheDocument();
      expect(screen.getAllByText(/UNVERIFIED/i).length).toBeGreaterThan(0);
    });
  });

  // Feature 4: Decision Flow & Live Constraint Checks
  describe("4. Decision Flow Modal & Live Constraint Enforcement", () => {
    it("locks hard constraint override for non-director accommodation lead", async () => {
      renderWithProviders(
        <DecisionFlowModal
          isOpen={true}
          onClose={() => {}}
          selectedBed={{ bed_id: "H3-101-B", status: "FREE", version: 1 }}
        />,
        mockUserAccommodationLead
      );

      // Pre-flight check evaluates P0104 into Boys Hostel 3
      expect(
        await screen.findByText(/Hostel 3 is a Boys block\. Participant P0104 has UNKNOWN gender/i)
      ).toBeInTheDocument();

      // Non-director warning
      expect(
        screen.getByText(/Hard safety constraints can only be overridden by the/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/NON-DIRECTOR \(LOCKED\)/i)).toBeInTheDocument();

      // Proceed button disabled
      const proceedBtn = screen.getByTestId("proceed-assign-btn");
      expect(proceedBtn).toBeDisabled();
    });

    it("allows Festival Director to authorize emergency override with reason and produces WhyCard", async () => {
      renderWithProviders(
        <DecisionFlowModal
          isOpen={true}
          onClose={() => {}}
          selectedBed={{ bed_id: "H3-101-B", status: "FREE", version: 1 }}
        />,
        mockUserFestivalDirector
      );

      // Festival Director has clearance checkbox
      const overrideCheckbox = await screen.findByTestId("director-override-checkbox");
      expect(overrideCheckbox).toBeInTheDocument();
      fireEvent.click(overrideCheckbox);

      // Now proceed button is enabled
      const proceedBtn = screen.getByTestId("proceed-assign-btn");
      expect(proceedBtn).toBeEnabled();
      fireEvent.click(proceedBtn);

      // ConfirmWithReason dialog
      expect(screen.getByText(/Authorize Hard Safety Constraint Override/i)).toBeInTheDocument();
      const reasonInput = screen.getByTestId("reason-input");
      fireEvent.change(reasonInput, { target: { value: "Director emergency bypass pending arrival verification" } });

      const confirmBtn = screen.getByText(/Confirm & Commit Assignment/i);
      fireEvent.click(confirmBtn);

      // WhyCard rendered
      await waitFor(() => {
        expect(screen.getByText(/Assignment Committed to Plan Engine/i)).toBeInTheDocument();
        expect(screen.getByText(/WhyCard/i) || screen.getByText(/Bed Assignment:/i)).toBeInTheDocument();
      });
    });

    it("handles 409 concurrency conflict with refresh recovery action", async () => {
      renderWithProviders(
        <DecisionFlowModal
          isOpen={true}
          onClose={() => {}}
          selectedBed={{ bed_id: "H3-101-B", status: "FREE", version: 999 }}
        />,
        mockUserFestivalDirector
      );

      const overrideCheckbox = await screen.findByTestId("director-override-checkbox");
      fireEvent.click(overrideCheckbox);

      const proceedBtn = screen.getByTestId("proceed-assign-btn");
      fireEvent.click(proceedBtn);

      const reasonInput = screen.getByTestId("reason-input");
      fireEvent.change(reasonInput, { target: { value: "Test concurrent update collision" } });

      const confirmBtn = screen.getByText(/Confirm & Commit Assignment/i);
      fireEvent.click(confirmBtn);

      // Catches 409 and displays conflict alert
      expect(await screen.findByTestId("conflict-alert")).toBeInTheDocument();
      expect(screen.getByText(/Concurrency Conflict \(409 Version Conflict\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Refresh Occupancy Map & Retry/i)).toBeInTheDocument();
    });
  });

  // Feature 5: Check-in Desk Mode
  describe("5. Check-in Desk Mode & One-Handed Reception Terminal", () => {
    it("renders scan field, room readiness, dietary prompt, and arrival board", async () => {
      renderWithProviders(<CheckInDesk />);

      // Search field with '/' shortcut prompt
      expect(screen.getByText(/Press \[ \/ \] to focus/i)).toBeInTheDocument();
      const searchInput = screen.getByTestId("checkin-search-input");
      expect(searchInput).toBeInTheDocument();

      // Participant card
      expect(await screen.findByTestId("participant-desk-card")).toBeInTheDocument();
      expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();

      // Room readiness (180m buffer)
      expect(screen.getByText(/ROOM READY FOR KEY RELEASE/i)).toBeInTheDocument();
      expect(screen.getByText(/Room 101 \(Bed H3-101-A\)/i)).toBeInTheDocument();

      // Arrival board counts
      expect(screen.getByText(/Live Arrival Board & Transit Delays/i)).toBeInTheDocument();
      expect(screen.getByText(/Late Curfew Breaches/i)).toBeInTheDocument();
    });

    it("performs arrival verification, releases room key, and allows checkout", async () => {
      renderWithProviders(<CheckInDesk />);

      const verifyBtn = await screen.findByTestId("verify-checkin-btn");
      expect(verifyBtn).toBeInTheDocument();
      fireEvent.click(verifyBtn);

      // Check-out & clean action
      const checkoutBtn = screen.getByText(/Check-out & Clean/i);
      expect(checkoutBtn).toBeInTheDocument();
      fireEvent.click(checkoutBtn);
    });
  });

  // Feature 6: Participant 360 Accommodation Tab
  describe("6. Participant 360 Accommodation Tab", () => {
    it("renders allocated room, accessibility status, and active plan provenance", () => {
      const mockParticipantData = {
        participant: {
          id: "P0102",
          name: "Aarav Sharma",
          housing_preference: "CAMPUS_HOSTEL",
        },
        contingent: {
          code: "C05",
          leader_name: "Rohan Deshmukh",
        },
        accessibility: {
          requires_ground_floor: false,
        },
        sections: {
          accommodation: {
            status: "ALLOCATED",
            plan_kind: "Plan C: Balanced (Recommended)",
            room: "Hostel 3 (Wing B, Room 101)",
          },
        },
      };

      renderWithProviders(
        <ParticipantAccommodationTab participantId="P0102" data={mockParticipantData} />
      );

      expect(screen.getByText(/Bed Allocation Status/i)).toBeInTheDocument();
      expect(screen.getByText(/Hostel 3 \(Wing B, Room 101\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Plan C: Balanced \(Recommended\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Contingent Cluster Cohesion/i)).toBeInTheDocument();
    });
  });
});
