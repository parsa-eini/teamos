import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CheckinsPage } from "@/features/checkins/CheckinsPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, OWNER_USER, renderAuthenticated, stubFetch } from "@/test/render";

const draft = {
  id: "c1",
  manager_id: "99999999-9999-4999-8999-999999999999",
  member_id: OWNER_USER.id,
  period_start: "2026-08-01",
  period_end: "2026-08-07",
  status: "DRAFT" as const,
  wins: "Shipped the API",
  challenges: null,
  next_steps: null,
  manager_notes: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("CheckinsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("requires member and period when creating a draft", async () => {
    stubFetch();
    const user = userEvent.setup();
    renderAuthenticated(<CheckinsPage />);
    expect(await screen.findByText("No check-ins")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create check-in" }));
    expect(screen.getByText("Member, start date, and end date are required.")).toBeInTheDocument();
  });

  it("lets the member submit a draft check-in", async () => {
    stubFetch((url, init) => {
      if (url.includes("/checkins") && init?.method === "PATCH") {
        return jsonResponse({ data: { ...draft, status: "SUBMITTED" } });
      }
      if (url.includes("/checkins")) {
        return jsonResponse({
          data: [draft],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderAuthenticated(<CheckinsPage />);
    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Submit" }));
    const patch = vi
      .mocked(fetch)
      .mock.calls.find(([url, init]) => String(url).includes("/checkins/c1") && init?.method === "PATCH");
    expect(patch).toBeTruthy();
    expect(JSON.parse(String(patch?.[1]?.body))).toMatchObject({ status: "SUBMITTED" });
  });
});
