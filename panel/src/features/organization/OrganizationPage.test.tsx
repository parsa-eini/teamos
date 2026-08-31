import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "@/app/queryClient";
import { OrganizationMembersPage } from "@/features/organization/OrganizationPage";
import { AuthProvider } from "@/hooks/useAuth";
import { clearAccessToken, setAccessToken } from "@/lib/auth";

function renderMembers() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <OrganizationMembersPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OrganizationMembersPage", () => {
  beforeEach(() => {
    setAccessToken("test-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/users/me")) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: async () => ({
              data: {
                id: "11111111-1111-4111-8111-111111111111",
                email: "owner@example.com",
                first_name: "Ada",
                last_name: "Lovelace",
                is_active: true,
                created_at: "2026-01-01T00:00:00Z",
                updated_at: "2026-01-01T00:00:00Z",
              },
            }),
          };
        }
        return {
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({
            data: [],
            meta: { page: 1, page_size: 20, total: 0 },
          }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("validates member details before calling create", async () => {
    const user = userEvent.setup();
    renderMembers();
    await user.click(await screen.findByRole("button", { name: "Add member" }));
    expect(
      screen.getByText("Name, email, and a password of at least 8 characters are required."),
    ).toBeInTheDocument();
    const createCalls = vi
      .mocked(fetch)
      .mock.calls.filter(([url, init]) => String(url).includes("/members") && init?.method === "POST");
    expect(createCalls).toHaveLength(0);
  });
});
