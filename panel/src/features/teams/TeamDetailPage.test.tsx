import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TeamDetailPage } from "@/features/teams/TeamDetailPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, MEMBER_USER, renderAuthenticated, stubFetch } from "@/test/render";

describe("TeamDetailPage", () => {
  beforeEach(() => {
    stubFetch((url) => {
      if (/\/teams\/t1(?:\?|$)/.test(url) && !url.includes("/members")) {
        return jsonResponse({
          data: {
            id: "t1",
            name: "Platform",
            description: "Core services",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        });
      }
      if (url.includes("/teams/t1/members")) {
        return jsonResponse({
          data: [
            {
              user_id: MEMBER_USER.user_id,
              email: MEMBER_USER.email,
              first_name: MEMBER_USER.first_name,
              last_name: MEMBER_USER.last_name,
              created_at: "2026-01-01T00:00:00Z",
            },
          ],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      return undefined;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows team details and members", async () => {
    renderAuthenticated(
      <Routes>
        <Route path="/teams/:id" element={<TeamDetailPage />} />
      </Routes>,
      { route: "/teams/t1" },
    );
    expect(await screen.findByDisplayValue("Platform")).toBeInTheDocument();
    expect(screen.getByText(/Grace Hopper/)).toBeInTheDocument();
    expect(screen.getByText("member@example.com")).toBeInTheDocument();
  });
});
