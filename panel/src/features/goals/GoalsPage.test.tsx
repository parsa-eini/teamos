import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GoalsPage } from "@/features/goals/GoalsPage";
import { clearAccessToken } from "@/lib/auth";
import {
  jsonResponse,
  MEMBER_USER,
  OWNER_MEMBER,
  renderAuthenticated,
  stubFetch,
} from "@/test/render";
import type { Goal } from "@/types/api";

const goal: Goal = {
  id: "g1",
  title: "Ship v1",
  description: "Launch the MVP",
  team_ids: [],
  owner_ids: [],
  task_ids: [],
  status: "IN_PROGRESS",
  progress: 40,
  progress_is_derived: false,
  start_date: null,
  due_date: null,
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const team = {
  id: "t1",
  name: "Platform",
  description: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const task = {
  id: "task-1",
  project_id: "p1",
  title: "Write spec",
  description: null,
  status: "TODO",
  priority: "HIGH",
  assignee_ids: [],
  due_date: null,
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

/** Serves goals, teams, and tasks; `overrides` replaces the goal list payload. */
function stubGoals(goals: Goal[], onPatch?: () => Response) {
  stubFetch((url, init) => {
    if (url.includes("/goals") && init?.method === "PATCH") {
      return onPatch ? onPatch() : jsonResponse({ data: goals[0] });
    }
    if (url.includes("/goals") && init?.method === "POST") {
      return jsonResponse({ data: goals[0] }, 201);
    }
    if (url.includes("/goals")) {
      return jsonResponse({ data: goals, meta: { page: 1, page_size: 20, total: goals.length } });
    }
    if (url.includes("/teams")) {
      return jsonResponse({ data: [team], meta: { page: 1, page_size: 100, total: 1 } });
    }
    if (url.includes("/tasks")) {
      return jsonResponse({ data: [task], meta: { page: 1, page_size: 100, total: 1 } });
    }
    return undefined;
  });
}

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
    stubGoals([goal], () => jsonResponse({ data: { ...goal, status: "COMPLETED" } }));
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

  it("creates a goal with several teams, owners, and linked tasks", async () => {
    stubGoals([goal]);
    const user = userEvent.setup();
    renderAuthenticated(<GoalsPage />);
    await screen.findByText("Ship v1");

    await user.type(screen.getByLabelText("Title"), "Company goal");
    await user.click(screen.getByRole("checkbox", { name: "Platform" }));
    await user.click(screen.getByRole("checkbox", { name: /Ada Lovelace/ }));
    await user.click(screen.getByRole("checkbox", { name: /Grace Hopper/ }));
    await user.click(screen.getByRole("checkbox", { name: /Write spec/ }));
    await user.click(screen.getByRole("button", { name: "Create goal" }));

    await waitFor(() => {
      const post = vi
        .mocked(fetch)
        .mock.calls.find(([url, init]) => String(url).includes("/goals") && init?.method === "POST");
      expect(post).toBeTruthy();
      expect(JSON.parse(String(post?.[1]?.body))).toMatchObject({
        title: "Company goal",
        team_ids: ["t1"],
        owner_ids: [OWNER_MEMBER.user_id, MEMBER_USER.user_id],
        task_ids: ["task-1"],
      });
    });
  });

  it("hides the progress slider and explains the calculation when tasks drive progress", async () => {
    stubGoals([
      { ...goal, task_ids: ["task-1", "task-2"], progress: 50, progress_is_derived: true },
    ]);
    renderAuthenticated(<GoalsPage />);
    expect(await screen.findByText("Ship v1")).toBeInTheDocument();
    expect(
      screen.getByText("Calculated from 2 linked tasks: the share of them that is done."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Progress for Ship v1")).not.toBeInTheDocument();
  });

  it("keeps the progress slider when no tasks are linked", async () => {
    stubGoals([goal]);
    renderAuthenticated(<GoalsPage />);
    expect(await screen.findByText("Ship v1")).toBeInTheDocument();
    expect(screen.getByLabelText("Progress for Ship v1")).toBeInTheDocument();
    expect(
      screen.getByText("Set by hand. Link tasks to calculate it from completed work."),
    ).toBeInTheDocument();
  });

  it("names the teams and owners on the goal card", async () => {
    stubGoals([{ ...goal, team_ids: ["t1"], owner_ids: [MEMBER_USER.user_id] }]);
    renderAuthenticated(<GoalsPage />);
    expect(await screen.findByText("Platform · Grace Hopper")).toBeInTheDocument();
  });

  it("describes an unscoped goal as organization wide", async () => {
    stubGoals([goal]);
    renderAuthenticated(<GoalsPage />);
    expect(await screen.findByText("Whole organization · No owner")).toBeInTheDocument();
  });

  it("shows a failed link change next to the goal", async () => {
    stubGoals([goal], () =>
      jsonResponse(
        { error: { code: "VALIDATION_ERROR", message: "progress is derived from linked tasks" } },
        422,
      ),
    );
    const user = userEvent.setup();
    renderAuthenticated(<GoalsPage />);
    await screen.findByText("Ship v1");
    await user.selectOptions(screen.getByLabelText("Status for Ship v1"), "COMPLETED");
    expect(
      await screen.findByText("progress is derived from linked tasks"),
    ).toBeInTheDocument();
  });
});
