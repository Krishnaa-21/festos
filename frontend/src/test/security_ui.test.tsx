import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { Badge, ConfirmWithReason, MaskedField } from "../components/ui";
import { RequireAuth, RequirePermission } from "../features/auth/RouteGuards";
import { AuthContext, AuthContextType } from "../features/auth/AuthContext";

describe("Frontend Security & UI Components", () => {
  describe("Badge Component", () => {
    it("renders Tri-state YES with distinct check icon and label", () => {
      render(<Badge triState="YES" />);
      expect(screen.getByText("YES")).toBeInTheDocument();
      const badge = screen.getByTestId("badge-tri-yes");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("text-emerald-300");
      expect(screen.getByTestId("icon-yes")).toBeInTheDocument();
    });

    it("renders Tri-state NO with distinct X icon and label", () => {
      render(<Badge triState="NO" />);
      expect(screen.getByText("NO")).toBeInTheDocument();
      const badge = screen.getByTestId("badge-tri-no");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("text-rose-300");
      expect(screen.getByTestId("icon-no")).toBeInTheDocument();
    });

    it("renders Tri-state UNKNOWN with distinct Help icon and label (never coerced to false)", () => {
      render(<Badge triState="UNKNOWN" />);
      expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
      const badge = screen.getByTestId("badge-tri-unknown");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("text-amber-300");
      expect(screen.getByTestId("icon-unknown")).toBeInTheDocument();
    });

    it("renders severity levels with icons and text labels (never color-only)", () => {
      const { rerender } = render(<Badge severity="CRITICAL" />);
      expect(screen.getByText("CRITICAL")).toBeInTheDocument();
      expect(screen.getByTestId("badge-severity-critical")).toBeInTheDocument();
      expect(screen.getByTestId("icon-sev-critical")).toBeInTheDocument();

      rerender(<Badge severity="HIGH" />);
      expect(screen.getByText("HIGH")).toBeInTheDocument();
      expect(screen.getByTestId("badge-severity-high")).toBeInTheDocument();
      expect(screen.getByTestId("icon-sev-high")).toBeInTheDocument();

      rerender(<Badge severity="MEDIUM" />);
      expect(screen.getByText("MEDIUM")).toBeInTheDocument();
      expect(screen.getByTestId("badge-severity-medium")).toBeInTheDocument();
      expect(screen.getByTestId("icon-sev-medium")).toBeInTheDocument();

      rerender(<Badge severity="LOW" />);
      expect(screen.getByText("LOW")).toBeInTheDocument();
      expect(screen.getByTestId("badge-severity-low")).toBeInTheDocument();
      expect(screen.getByTestId("icon-sev-low")).toBeInTheDocument();
    });

    it("renders status badges correctly", () => {
      render(<Badge status="PENDING_APPROVAL" />);
      expect(screen.getByText("PENDING APPROVAL")).toBeInTheDocument();
    });
  });

  describe("ConfirmWithReason Component", () => {
    it("disables confirm button when reason is empty or whitespace", () => {
      const onConfirm = vi.fn();
      const onClose = vi.fn();

      render(
        <ConfirmWithReason
          isOpen={true}
          onClose={onClose}
          onConfirm={onConfirm}
          title="Override Capacity Constraint"
          description="Emergency bed allocation over standard threshold."
          riskLevel="HIGH"
        />
      );

      const confirmBtn = screen.getByTestId("confirm-button");
      expect(confirmBtn).toBeDisabled();

      const input = screen.getByTestId("reason-input");
      fireEvent.change(input, { target: { value: "   " } });
      expect(confirmBtn).toBeDisabled();

      expect(onConfirm).not.toHaveBeenCalled();
    });

    it("enables confirm button and passes reason when user inputs mandatory rationale", async () => {
      const onConfirm = vi.fn().mockResolvedValue(undefined);
      const onClose = vi.fn();

      render(
        <ConfirmWithReason
          isOpen={true}
          onClose={onClose}
          onConfirm={onConfirm}
          title="Authorize High-Risk Approval"
          description="Sign off on contingent budget expansion."
          riskLevel="CRITICAL"
        />
      );

      const input = screen.getByTestId("reason-input");
      const confirmBtn = screen.getByTestId("confirm-button");

      fireEvent.change(input, {
        target: { value: "Approved under Festival Director emergency contingency pool." },
      });
      expect(confirmBtn).not.toBeDisabled();

      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith(
          "Approved under Festival Director emergency contingency pool."
        );
      });
    });

    it("calls onClose when cancel is clicked", () => {
      const onConfirm = vi.fn();
      const onClose = vi.fn();

      render(
        <ConfirmWithReason
          isOpen={true}
          onClose={onClose}
          onConfirm={onConfirm}
          title="Reject Request"
          description="Cancel action"
        />
      );

      const cancelBtn = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelBtn);
      expect(onClose).toHaveBeenCalled();
      expect(onConfirm).not.toHaveBeenCalled();
    });
  });

  describe("MaskedField Component", () => {
    it("renders unmasked value directly when isMasked is false", () => {
      render(
        <MaskedField
          value="+91-9876543210"
          entity="participant:1"
          field="phone"
          isMasked={false}
        />
      );

      expect(screen.getByText("+91-9876543210")).toBeInTheDocument();
      expect(screen.queryByTestId("break-glass-trigger")).not.toBeInTheDocument();
    });

    it("renders masked value with BREAK GLASS badge when masked", () => {
      render(
        <MaskedField
          value="+91-XXXXX-3210"
          entity="participant:1"
          field="phone"
          isMasked={true}
        />
      );

      expect(screen.getByText("+91-XXXXX-3210")).toBeInTheDocument();
      expect(screen.getByText("BREAK GLASS")).toBeInTheDocument();
      expect(screen.getByTestId("break-glass-trigger")).toBeInTheDocument();
    });

    it("opens break-glass dialog on click and requires reason for emergency elevation", async () => {
      const onBreakGlass = vi.fn().mockResolvedValue(undefined);

      render(
        <MaskedField
          value="[RESTRICTED MEDICAL DATA]"
          entity="participant:42"
          field="medical_history"
          isMasked={true}
          onBreakGlass={onBreakGlass}
        />
      );

      // Click the masked field to trigger break-glass dialog
      const trigger = screen.getByTestId("break-glass-trigger");
      fireEvent.click(trigger);

      expect(screen.getByText("Emergency Break-Glass Unmasking")).toBeInTheDocument();
      expect(screen.getByText(/Target Entity:/)).toBeInTheDocument();

      const submitBtn = screen.getByTestId("break-glass-submit");
      expect(submitBtn).toBeDisabled();

      const input = screen.getByTestId("break-glass-reason-input");
      fireEvent.change(input, {
        target: { value: "Severe allergic reaction reported at Dining Hall 2." },
      });

      expect(submitBtn).not.toBeDisabled();
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(onBreakGlass).toHaveBeenCalledWith(
          "participant:42",
          "medical_history",
          "Severe allergic reaction reported at Dining Hall 2."
        );
      });
    });
  });

  describe("Route Guards", () => {
    const mockAuthContext = (overrides: Partial<AuthContextType> = {}): AuthContextType => ({
      user: {
        id: "usr_vol",
        email: "volunteer@festos.internal",
        full_name: "Volunteer Agent",
        role: "VOLUNTEER",
        permissions: ["checkin:read", "checkin:create"],
      },
      token: "mock_jwt_token",
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refetchUser: vi.fn(),
      hasPermission: (perm: string) =>
        overrides.user?.permissions?.includes(perm) ??
        ["checkin:read", "checkin:create"].includes(perm),
      ...overrides,
    });

    it("RequireAuth redirects unauthenticated user to /login", () => {
      const unauthContext = mockAuthContext({
        user: null,
        token: null,
        isAuthenticated: false,
      });

      render(
        <AuthContext.Provider value={unauthContext}>
          <MemoryRouter initialEntries={["/dashboard"]}>
            <Routes>
              <Route path="/login" element={<div>LOGIN PAGE CONTENT</div>} />
              <Route
                path="/dashboard"
                element={
                  <RequireAuth>
                    <div>PROTECTED DASHBOARD</div>
                  </RequireAuth>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      );

      expect(screen.getByText("LOGIN PAGE CONTENT")).toBeInTheDocument();
      expect(screen.queryByText("PROTECTED DASHBOARD")).not.toBeInTheDocument();
    });

    it("RequireAuth renders children when user is authenticated", () => {
      const authContext = mockAuthContext();

      render(
        <AuthContext.Provider value={authContext}>
          <MemoryRouter initialEntries={["/dashboard"]}>
            <Routes>
              <Route
                path="/dashboard"
                element={
                  <RequireAuth>
                    <div>PROTECTED DASHBOARD</div>
                  </RequireAuth>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      );

      expect(screen.getByText("PROTECTED DASHBOARD")).toBeInTheDocument();
    });

    it("RequirePermission renders Access Restricted view when user lacks permission", () => {
      const volunteerContext = mockAuthContext();

      render(
        <AuthContext.Provider value={volunteerContext}>
          <RequirePermission permission="audit:read">
            <div>AUDIT LOGS CONTENT</div>
          </RequirePermission>
        </AuthContext.Provider>
      );

      expect(screen.getByTestId("permission-denied")).toBeInTheDocument();
      expect(screen.getByText("Access Restricted")).toBeInTheDocument();
      expect(screen.getByText("audit:read")).toBeInTheDocument();
      expect(screen.queryByText("AUDIT LOGS CONTENT")).not.toBeInTheDocument();
    });

    it("RequirePermission renders children when user possesses permission", () => {
      const auditorContext = mockAuthContext({
        user: {
          id: "usr_aud",
          email: "auditor@festos.internal",
          full_name: "Audit Officer",
          role: "AUDITOR",
          permissions: ["audit:read"],
        },
        hasPermission: (perm: string) => perm === "audit:read",
      });

      render(
        <AuthContext.Provider value={auditorContext}>
          <RequirePermission permission="audit:read">
            <div>AUDIT LOGS CONTENT</div>
          </RequirePermission>
        </AuthContext.Provider>
      );

      expect(screen.getByText("AUDIT LOGS CONTENT")).toBeInTheDocument();
      expect(screen.queryByTestId("permission-denied")).not.toBeInTheDocument();
    });
  });
});
