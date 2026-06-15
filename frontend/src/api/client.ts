import type { ApiErrorBody } from "../types/api";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;
  constructor(status: number, code: string, message?: string, requestId?: string) {
    super(message || code || `HTTP ${status}`);
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

function extractCode(
  body: ApiErrorBody | null,
  status: number
): { code: string; message?: string; requestId?: string } {
  if (body && typeof body.detail === "object" && body.detail) {
    return {
      code: body.detail.code ?? `http_${status}`,
      message: body.detail.message,
      requestId: (body.detail as { request_id?: string }).request_id,
    };
  }
  if (body && typeof body.detail === "string") {
    return { code: body.detail };
  }
  return { code: `http_${status}` };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch (e) {
    throw new ApiError(0, "network_error", "Cannot reach the backend. Is it running?");
  }

  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }
    const { code, message, requestId } = extractCode(body, res.status);
    throw new ApiError(res.status, code, message, requestId ?? res.headers.get("X-Request-ID") ?? undefined);
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

export const api = {
  baseUrl: BASE_URL,
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  getText: (path: string) => request<string>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
