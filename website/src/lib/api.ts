import { ApiError } from "@/lib/errors";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
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

  const payload = (await response.json()) as {
    data?: T;
    error?: { code: string; message: string };
  };

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload.error?.code ?? "REQUEST_FAILED",
      payload.error?.message ?? "Request failed",
    );
  }

  return (payload.data ?? payload) as T;
}

export function redirectToPanel(accessToken?: string): void {
  const panelUrl = import.meta.env.VITE_PANEL_URL ?? "http://localhost:5174";
  if (accessToken) {
    window.location.assign(`${panelUrl}/auth/callback#access_token=${encodeURIComponent(accessToken)}`);
    return;
  }
  window.location.assign(`${panelUrl}/login`);
}
