import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "@/features/tasks/TasksPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, renderAuthenticated, stubFetch } from "@/test/render";

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
  assignee_id: null,
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
});
