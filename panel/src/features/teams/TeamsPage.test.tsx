import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TeamsPage } from "@/features/teams/TeamsPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, renderAuthenticated, stubFetch } from "@/test/render";

describe("TeamsPage", () => {
  beforeEach(() => {
    stubFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows an empty state and requires a team name", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<TeamsPage />);
    expect(await screen.findByText("No teams yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(screen.getByText("Team name is required.")).toBeInTheDocument();
    const createCalls = vi
      .mocked(fetch)
      .mock.calls.filter(([url, init]) => String(url).includes("/teams") && init?.method === "POST");
    expect(createCalls).toHaveLength(0);
  });

  it("lists teams returned by the API", async () => {
    stubFetch((url) => {
      if (url.includes("/api/v1/teams") && !url.includes("/members")) {
        return jsonResponse({
          data: [
            {
              id: "t1",
              name: "Platform",
              description: "Core services",
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-02T00:00:00Z",
            },
          ],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      return undefined;
    });
    renderAuthenticated(<TeamsPage />);
    expect(await screen.findByRole("link", { name: "Platform" })).toHaveAttribute("href", "/teams/t1");
    expect(screen.getByText("Core services")).toBeInTheDocument();
  });
});
