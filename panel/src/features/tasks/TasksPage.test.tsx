import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "@/features/tasks/TasksPage";
import { clearAccessToken } from "@/lib/auth";
import {
  jsonResponse,
  MEMBER_USER,
  OWNER_MEMBER,
  renderAuthenticated,
  stubFetch,
} from "@/test/render";

const project = {
  id: "p1",
  name: "Launch",
  description: null,
  team_id: null,
  status: "ACTIVE",
  start_date: null,
  end_date: null,
  created_by: "11111111-1111-4111-8111-111111111111",
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
  assignee_ids: [] as string[],
  due_date: "2026-09-15",
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("TasksPage", () => {
  beforeEach(() => {
    stubFetch((url) => {
      if (url.includes("/projects")) {
        return jsonResponse({ data: [project], meta: { page: 1, page_size: 100, total: 1 } });
      }
      if (url.includes("/tasks")) {
        return jsonResponse({ data: [task], meta: { page: 1, page_size: 20, total: 1 } });
      }
      return undefined;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("lists tasks and requires a title and project to create", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<TasksPage />);
    expect(await screen.findByText("Write spec")).toBeInTheDocument();
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create task" }));
    expect(screen.getByText("Title and a project are required.")).toBeInTheDocument();
  });

  it("requests filtered tasks when the status filter changes", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<TasksPage />);
    await screen.findByText("Write spec");
    await user.selectOptions(screen.getByDisplayValue("All statuses"), "IN_PROGRESS");
    await waitFor(() => {
      expect(
        vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes("status=IN_PROGRESS")),
      ).toBe(true);
    });
  });

  it("creates a task with several assignees", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<TasksPage />);
    await screen.findByText("Write spec");

    await user.type(screen.getByLabelText("Title"), "Pair up");
    await user.selectOptions(
      screen.getByLabelText("Project", { selector: "#task-project" }),
      "p1",
    );
    await user.click(screen.getByRole("checkbox", { name: /Ada Lovelace/ }));
    await user.click(screen.getByRole("checkbox", { name: /Grace Hopper/ }));
    await user.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => {
      const post = vi
        .mocked(fetch)
        .mock.calls.find(([url, init]) => String(url).includes("/tasks") && init?.method === "POST");
      expect(post).toBeTruthy();
      expect(JSON.parse(String(post?.[1]?.body))).toMatchObject({
        title: "Pair up",
        project_id: "p1",
        assignee_ids: [OWNER_MEMBER.user_id, MEMBER_USER.user_id],
      });
    });
  });

  it("shows every assignee on the task row", async () => {
    vi.unstubAllGlobals();
    stubFetch((url) => {
      if (url.includes("/projects")) {
        return jsonResponse({ data: [project], meta: { page: 1, page_size: 100, total: 1 } });
      }
      if (url.includes("/tasks")) {
        return jsonResponse({
          data: [{ ...task, assignee_ids: [OWNER_MEMBER.user_id, MEMBER_USER.user_id] }],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      return undefined;
    });
    renderAuthenticated(<TasksPage />);
    expect(await screen.findByText("Ada Lovelace, Grace Hopper")).toBeInTheDocument();
  });

  it("labels an unassigned task on the row", async () => {
    renderAuthenticated(<TasksPage />);
    expect(await screen.findByText("Unassigned")).toBeInTheDocument();
  });
});
