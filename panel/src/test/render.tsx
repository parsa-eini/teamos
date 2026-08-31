import { QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { createQueryClient } from "@/app/queryClient";
import { AuthProvider } from "@/hooks/useAuth";
import { setAccessToken } from "@/lib/auth";
import type { OrganizationMember, User } from "@/types/api";

export const OWNER_USER: User = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "owner@example.com",
  first_name: "Ada",
  last_name: "Lovelace",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const OWNER_MEMBER: OrganizationMember = {
  user_id: OWNER_USER.id,
  email: OWNER_USER.email,
  first_name: OWNER_USER.first_name,
  last_name: OWNER_USER.last_name,
  role: "OWNER",
  created_at: "2026-01-01T00:00:00Z",
};

export const MEMBER_USER: OrganizationMember = {
  user_id: "22222222-2222-4222-8222-222222222222",
  email: "member@example.com",
  first_name: "Grace",
  last_name: "Hopper",
  role: "MEMBER",
  created_at: "2026-01-01T00:00:00Z",
};

export function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => body,
  } as Response;
}

export function emptyCollection() {
  return { data: [], meta: { page: 1, page_size: 20, total: 0 } };
}

type FetchHandler = (url: string, init?: RequestInit) => Response | undefined | Promise<Response | undefined>;

export function stubFetch(handler?: FetchHandler): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (handler) {
        const override = await handler(url, init);
        if (override) {
          return override;
        }
      }
      if (url.includes("/users/me")) {
        return jsonResponse({ data: OWNER_USER });
      }
      if (url.includes("/organizations/current/members")) {
        return jsonResponse({
          data: [OWNER_MEMBER, MEMBER_USER],
          meta: { page: 1, page_size: 100, total: 2 },
        });
      }
      if (url.includes("/organizations/current") && !url.includes("/members")) {
        return jsonResponse({
          data: {
            id: "33333333-3333-4333-8333-333333333333",
            name: "Acme",
            slug: "acme",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        });
      }
      return jsonResponse(emptyCollection());
    }),
  );
}

export function renderAuthenticated(
  ui: ReactElement,
  options: { route?: string; token?: string } = {},
): RenderResult {
  setAccessToken(options.token ?? "test-token");
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[options.route ?? "/"]}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
