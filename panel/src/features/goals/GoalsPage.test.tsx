import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GoalsPage } from "@/features/goals/GoalsPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, renderAuthenticated, stubFetch } from "@/test/render";

describe("GoalsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows an empty state and requires a title", async () => {
    stubFetch();
    const user = userEvent.setup();
    renderAuthenticated(<GoalsPage />);
    expect(await screen.findByText("No goals yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create goal" }));
    expect(screen.getByText("Goal title is required.")).toBeInTheDocument();
  });

  it("lists a goal and can update status", async () => {
    stubFetch((url, init) => {
      if (url.includes("/goals") && init?.method === "PATCH") {
        return jsonResponse({
          data: {
            id: "g1",
            title: "Ship v1",
            description: null,
            team_id: null,
            user_id: null,
            status: "COMPLETED",
            progress: 40,
            start_date: null,
            due_date: null,
            created_by: "11111111-1111-4111-8111-111111111111",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        });
      }
      if (url.includes("/goals")) {
        return jsonResponse({
          data: [
            {
              id: "g1",
              title: "Ship v1",
              description: "Launch the MVP",
              team_id: null,
              user_id: null,
              status: "IN_PROGRESS",
              progress: 40,
              start_date: null,
              due_date: null,
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
    renderAuthenticated(<GoalsPage />);
    expect(await screen.findByText("Ship v1")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    await userEvent.setup().selectOptions(screen.getByLabelText("Status for Ship v1"), "COMPLETED");
    expect(
      vi.mocked(fetch).mock.calls.some(
        ([url, init]) => String(url).includes("/goals/g1") && init?.method === "PATCH",
      ),
    ).toBe(true);
  });
});
