import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MeetingsPage } from "@/features/meetings/MeetingsPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, MEMBER_USER, OWNER_MEMBER, renderAuthenticated, stubFetch } from "@/test/render";

const meeting = {
  id: "meeting-1",
  manager_id: OWNER_MEMBER.user_id,
  member_id: MEMBER_USER.user_id,
  type: "CHECK_IN",
  scheduled_on: "2026-02-06",
  status: "DRAFT",
  wins: null,
  challenges: null,
  next_steps: null,
  manager_notes: null,
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

function stubMeetings(
  overrides: {
    meetings?: Array<Record<string, unknown>>;
    onPatch?: (url: string, init?: RequestInit) => Response | undefined;
    onList?: (url: string) => void;
  } = {},
) {
  const rows = overrides.meetings ?? [meeting];
  stubFetch((url, init) => {
    if (url.includes("/meetings/") && init?.method === "PATCH") {
      return overrides.onPatch?.(url, init) ?? jsonResponse({ data: { ...rows[0], status: "DRAFT" } });
    }
    if (url.includes("/meetings")) {
      overrides.onList?.(url);
      return jsonResponse({ data: rows, meta: { page: 1, page_size: 20, total: rows.length } });
    }
    return undefined;
  });
}

describe("MeetingsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows the meeting type and requires a member and date to create", async () => {
    const user = userEvent.setup();
    stubMeetings();
    renderAuthenticated(<MeetingsPage />);
    expect(await screen.findByText(/Check-in · /)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create meeting" }));
    expect(screen.getByText("Member and date are required.")).toBeInTheDocument();
  });

  it("labels the draft fields visibly", async () => {
    stubMeetings();
    renderAuthenticated(<MeetingsPage />);
    expect(await screen.findByLabelText("Wins", { selector: "#wins-meeting-1" })).toBeInTheDocument();
    expect(
      screen.getByLabelText("Challenges", { selector: "#challenges-meeting-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Next steps", { selector: "#next-steps-meeting-1" }),
    ).toBeInTheDocument();
  });

  it("reports save failures next to the meeting", async () => {
    const user = userEvent.setup();
    stubMeetings({
      onPatch: () =>
        jsonResponse({ error: { code: "FORBIDDEN", message: "Not a participant" } }, 403),
    });
    renderAuthenticated(<MeetingsPage />);
    await user.click(await screen.findByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("Not a participant")).toBeInTheDocument();
  });

  it("hides Save draft from people who are neither the member nor the manager", async () => {
    stubMeetings({
      meetings: [
        { ...meeting, manager_id: MEMBER_USER.user_id, member_id: "44444444-4444-4444-8444-444444444444" },
      ],
    });
    renderAuthenticated(<MeetingsPage />);
    expect(await screen.findByText(/Check-in · /)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save draft" })).not.toBeInTheDocument();
  });

  it("filters by meeting type", async () => {
    const user = userEvent.setup();
    const urls: string[] = [];
    stubMeetings({ onList: (url) => urls.push(url) });
    renderAuthenticated(<MeetingsPage />);
    await screen.findByText(/Check-in · /);
    await user.selectOptions(screen.getByLabelText("Show"), "PERFORMANCE_REVIEW");
    await waitFor(() => {
      expect(urls.some((url) => url.includes("type=PERFORMANCE_REVIEW"))).toBe(true);
    });
  });
});
