export interface ApiResponseEnvelope<T> {
  data: T;
  meta: Record<string, unknown>;
  warnings: string[];
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

export interface ApiErrorEnvelope {
  error: ApiErrorDetail;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;
  requestId?: string;

  constructor(status: number, errorDetail: ApiErrorDetail) {
    super(errorDetail.message);
    this.name = "ApiError";
    this.status = status;
    this.code = errorDetail.code;
    this.details = errorDetail.details;
    this.requestId = errorDetail.request_id;
  }
}

export interface RequestOptions extends RequestInit {
  idempotencyKey?: string;
  params?: Record<string, string | number | boolean | undefined>;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function generateIdempotencyKey(): string {
  return `idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { idempotencyKey, params, headers: customHeaders, ...fetchOptions } = options;

  let url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined) searchParams.append(key, String(val));
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const headers = new Headers(customHeaders);
  if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Inject JWT if available
  const token = localStorage.getItem("festos_token");
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Inject Idempotency-Key if provided
  if (idempotencyKey) {
    headers.set("Idempotency-Key", idempotencyKey);
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    let errorDetail: ApiErrorDetail;
    try {
      const errJson = (await response.json()) as ApiErrorEnvelope;
      errorDetail = errJson.error || {
        code: "HTTP_ERROR",
        message: response.statusText || `Request failed with status ${response.status}`,
      };
    } catch {
      errorDetail = {
        code: "HTTP_ERROR",
        message: response.statusText || `Request failed with status ${response.status}`,
      };
    }
    throw new ApiError(response.status, errorDetail);
  }

  const json = await response.json();
  // Unwrap envelope data if present, otherwise return raw payload (e.g. /health)
  if (json && typeof json === "object" && "data" in json) {
    return (json as ApiResponseEnvelope<T>).data;
  }
  return json as T;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: "DELETE" }),
};
