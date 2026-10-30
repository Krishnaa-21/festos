import { describe, it, expect } from "vitest";
import { getRegisteredFeatures, getFeaturesByGroup } from "../app/registry";

describe("Feature Registry Auto-Discovery", () => {
  it("auto-discovers dashboard feature from features directory", () => {
    const features = getRegisteredFeatures();
    const dashboard = features.find((f) => f.id === "dashboard");
    expect(dashboard).toBeDefined();
    expect(dashboard?.label).toBe("Executive Dashboard");
    expect(dashboard?.group).toBe("Overview");
  });

  it("organizes discovered features by spec section 18 nav groups", () => {
    const grouped = getFeaturesByGroup();
    expect(grouped["Overview"]).toBeDefined();
    expect(grouped["Overview"].some((f) => f.id === "dashboard")).toBe(true);
    expect(grouped["Accommodation"]).toBeDefined();
    expect(grouped["Participants"]).toBeDefined();
  });
});
