import { clearAccessToken, getAccessToken } from "@/lib/auth";
import { ApiError } from "@/lib/errors";
import type { ApiErrorBody } from "@/types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  skipAuth?: boolean;
};

function redirectToLogin(): void {
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const token = options.skipAuth ? null : getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...options,
    headers,
    body,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown = null;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    payload = await response.json();
  }

  if (!response.ok) {
    const errorBody = payload as ApiErrorBody | null;
    const code = errorBody?.error?.code ?? "REQUEST_FAILED";
    const message = errorBody?.error?.message ?? "Request failed";
    if (response.status === 401 && !options.skipAuth) {
      clearAccessToken();
      redirectToLogin();
    }
    throw new ApiError(response.status, code, message);
  }

  return payload as T;
}

export function toQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}
