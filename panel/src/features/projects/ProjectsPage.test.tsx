import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectsPage } from "@/features/projects/ProjectsPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, renderAuthenticated, stubFetch } from "@/test/render";

describe("ProjectsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows an empty state with a create action", async () => {
    stubFetch();
    renderAuthenticated(<ProjectsPage />);
    expect(await screen.findByText("No projects")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create project" })).toHaveAttribute("href", "/projects/new");
  });

  it("lists projects returned by the API", async () => {
    stubFetch((url) => {
      if (url.includes("/projects")) {
        return jsonResponse({
          data: [
            {
              id: "p1",
              name: "Launch",
              description: null,
              team_id: null,
              status: "ACTIVE",
              start_date: "2026-01-01",
              end_date: "2026-03-01",
              created_by: "11111111-1111-4111-8111-111111111111",
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
          ],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      return undefined;
    });
    renderAuthenticated(<ProjectsPage />);
    expect(await screen.findByRole("link", { name: "Launch" })).toHaveAttribute("href", "/projects/p1");
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });
});
