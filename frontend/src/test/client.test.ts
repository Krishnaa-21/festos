import { describe, it, expect } from "vitest";
import { api, ApiError, generateIdempotencyKey } from "../api/client";

describe("apiClient", () => {
  it("unwraps envelope data for successful mutating calls", async () => {
    const idemKey = generateIdempotencyKey();
    const result = await api.post<{ change_set_id: string; status: string }>(
      "/api/v1/_example/items",
      { name: "Valid Kit" },
      { idempotencyKey: idemKey }
    );

    expect(result).toBeDefined();
    expect(result.status).toBe("APPLIED");
    expect(result.change_set_id).toBe("cs_mock_123");
  });

  it("fetches health status without envelope", async () => {
    const health = await api.get<{ status: string; version: string }>("/health");
    expect(health.status).toBe("healthy");
    expect(health.version).toBe("0.1.0");
  });

  it("throws typed ApiError on validation failure", async () => {
    try {
      await api.post("/api/v1/_example/items", { name: "fail" });
      expect.fail("Expected ApiError to be thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(422);
      expect(apiErr.code).toBe("VALIDATION_ERROR");
      expect(apiErr.message).toBe("Invalid name");
      expect(apiErr.requestId).toBe("req_test_123");
    }
  });
});
