import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("http://localhost:8000/health", () => {
    return HttpResponse.json({
      status: "healthy",
      version: "0.1.0",
      now: "2026-10-30T10:00:00Z"
    });
  }),

  http.get("http://localhost:8000/api/v1/meta", () => {
    return HttpResponse.json({
      version: "0.1.0",
      now: "2026-10-30T10:00:00Z",
      modules: ["participants", "accommodation"],
      auth_disabled: true
    });
  }),

  http.post("http://localhost:8000/api/v1/_example/items", async ({ request }) => {
    const body = (await request.json()) as any;
    if (body.name === "fail") {
      return HttpResponse.json(
        {
          error: {
            code: "VALIDATION_ERROR",
            message: "Invalid name",
            request_id: "req_test_123"
          }
        },
        { status: 422 }
      );
    }
    return HttpResponse.json({
      data: {
        change_set_id: "cs_mock_123",
        status: "APPLIED",
        violations: []
      },
      meta: {},
      warnings: []
    });
  }),
];

export const server = setupServer(...handlers);
