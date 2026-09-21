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

const OWNER_ID = "11111111-1111-4111-8111-111111111111";
const MEMBER_ID = "22222222-2222-4222-8222-222222222222";

function ownerAndMember(reportsTo: string | null) {
  return [
    {
      user_id: OWNER_ID,
      email: "owner@example.com",
      first_name: "Ada",
      last_name: "Lovelace",
      role: "OWNER",
      reports_to_user_id: null,
      created_at: "2026-01-01T00:00:00Z",
    },
    {
      user_id: MEMBER_ID,
      email: "member@example.com",
      first_name: "Grace",
      last_name: "Hopper",
      role: "MEMBER",
      reports_to_user_id: reportsTo,
      created_at: "2026-01-01T00:00:00Z",
    },
  ];
}

describe("OrganizationMembersPage hierarchy", () => {
  beforeEach(() => {
    setAccessToken("test-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input);
        const body = (payload: unknown) => ({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => payload,
        });
        if (url.includes("/users/me")) {
          return body({
            data: {
              id: OWNER_ID,
              email: "owner@example.com",
              first_name: "Ada",
              last_name: "Lovelace",
              is_active: true,
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
          });
        }
        if (url.includes("/hierarchy")) {
          return body({
            data: [
              {
                user_id: OWNER_ID,
                email: "owner@example.com",
                first_name: "Ada",
                last_name: "Lovelace",
                role: "OWNER",
                reports: [
                  {
                    user_id: MEMBER_ID,
                    email: "member@example.com",
                    first_name: "Grace",
                    last_name: "Hopper",
                    role: "MEMBER",
                    reports: [],
                  },
                ],
              },
            ],
          });
        }
        if (init?.method === "PATCH") {
          return body({ data: ownerAndMember(OWNER_ID)[1] });
        }
        return body({ data: ownerAndMember(null), meta: { page: 1, page_size: 20, total: 2 } });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("assigns a manager from the members table", async () => {
    const user = userEvent.setup();
    renderMembers();
    const select = await screen.findByLabelText("Reports to for Grace Hopper");
    await user.selectOptions(select, OWNER_ID);

    const patch = vi
      .mocked(fetch)
      .mock.calls.find(([url, init]) => String(url).includes("/members/") && init?.method === "PATCH");
    expect(patch).toBeDefined();
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ reports_to_user_id: OWNER_ID });
  });

  it("renders the reporting tree", async () => {
    renderMembers();
    expect(await screen.findByText("Reporting hierarchy")).toBeInTheDocument();
    const tree = (await screen.findAllByText("Grace Hopper")).length;
    expect(tree).toBeGreaterThan(0);
  });
});
