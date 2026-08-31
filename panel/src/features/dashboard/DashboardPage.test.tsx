import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, renderAuthenticated, stubFetch } from "@/test/render";

describe("DashboardPage", () => {
  beforeEach(() => {
    stubFetch((url) => {
      if (url.includes("/dashboard")) {
        return jsonResponse({
          data: {
            member_count: 12,
            active_projects: 4,
            open_tasks: 47,
            overdue_tasks: 6,
            goal_summary: {
              total: 1,
              items: [{ id: "g1", title: "Product Launch", progress: 70, status: "IN_PROGRESS" }],
            },
            recent_checkins: [],
            recent_activity: [
              {
                type: "task_completed",
                message: 'Ada Lovelace completed "API redesign"',
                occurred_at: "2026-08-01T12:00:00Z",
              },
            ],
          },
        });
      }
      return undefined;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows team overview stats, goals, and activity", async () => {
    renderAuthenticated(<DashboardPage />);
    expect(await screen.findByText("Members")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("47")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByText("Product Launch")).toBeInTheDocument();
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getByText("No recent check-ins")).toBeInTheDocument();
    expect(screen.getByText('Ada Lovelace completed "API redesign"')).toBeInTheDocument();
  });

  it("shows a permission message when the dashboard is forbidden", async () => {
    stubFetch((url) => {
      if (url.includes("/dashboard")) {
        return jsonResponse(
          { error: { code: "FORBIDDEN", message: "You do not have permission to view the dashboard" } },
          403,
        );
      }
      return undefined;
    });
    renderAuthenticated(<DashboardPage />);
    expect(
      await screen.findByText("You do not have permission to view the manager dashboard."),
    ).toBeInTheDocument();
  });

  it("shows empty goal and activity states", async () => {
    stubFetch((url) => {
      if (url.includes("/dashboard")) {
        return jsonResponse({
          data: {
            member_count: 1,
            active_projects: 0,
            open_tasks: 0,
            overdue_tasks: 0,
            goal_summary: { total: 0, items: [] },
            recent_checkins: [],
            recent_activity: [],
          },
        });
      }
      return undefined;
    });
    renderAuthenticated(<DashboardPage />);
    expect(await screen.findByText("No goals yet")).toBeInTheDocument();
    expect(screen.getByText("No recent activity")).toBeInTheDocument();
  });
});
