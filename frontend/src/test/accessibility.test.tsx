import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "../components/ui/Toast";
import { AuthContext, UserProfile } from "../features/auth/AuthContext";
import { VolunteerMobileView } from "../features/checkin/VolunteerMobileView";
import { KeyboardShortcutsModal } from "../components/layout/KeyboardShortcutsModal";

describe("Accessibility (axe) Audit - WCAG 2.1 AA Compliance", () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const mockVolunteer: UserProfile = {
    id: "usr_vol_001",
    email: "volunteer@festos.internal",
    full_name: "Pooja Sharma",
    role: "VOLUNTEER",
    permissions: ["checkin:write", "merchandise:write"],
  };

  it("VolunteerMobileView passes axe accessibility audit with no serious/critical violations", async () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ToastProvider>
            <AuthContext.Provider
              value={{
                user: mockVolunteer,
                token: "mock-token",
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

    const results = await axe.run(container, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa"],
      },
    });

    const seriousViolations = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );

    expect(seriousViolations).toEqual([]);
  });

  it("KeyboardShortcutsModal passes axe accessibility audit with no serious/critical violations", async () => {
    const { container } = render(
      <KeyboardShortcutsModal isOpen={true} onClose={() => {}} />
    );

    const results = await axe.run(container, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa"],
      },
    });

    const seriousViolations = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );

    expect(seriousViolations).toEqual([]);
  });
});

