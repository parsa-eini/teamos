import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FeedbackPage } from "@/features/feedback/FeedbackPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, MEMBER_USER, OWNER_MEMBER, renderAuthenticated, stubFetch } from "@/test/render";

const feedback = {
  id: "feedback-1",
  subject_id: MEMBER_USER.user_id,
  author_id: OWNER_MEMBER.user_id,
  sentiment: "NEGATIVE",
  body: "Missed two handovers this month.",
  created_at: "2026-03-01T10:00:00Z",
  updated_at: "2026-03-01T10:00:00Z",
};

const requests: Array<{ url: string; init?: RequestInit }> = [];

describe("FeedbackPage", () => {
  beforeEach(() => {
    requests.length = 0;
    stubFetch((url, init) => {
      if (url.includes("/feedback")) {
        requests.push({ url, init });
        if (init?.method === "POST") {
          return jsonResponse({ data: feedback }, 201);
        }
        return jsonResponse({ data: [feedback], meta: { page: 1, page_size: 20, total: 1 } });
      }
      return undefined;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("shows who the feedback is about and marks the sentiment", async () => {
    renderAuthenticated(<FeedbackPage />);
    expect(await screen.findByText("About Grace Hopper")).toBeInTheDocument();
    expect(screen.getByText("Missed two handovers this month.")).toBeInTheDocument();
    expect(screen.getByText("NEGATIVE")).toBeInTheDocument();
  });

  it("requires a person and a note before posting", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<FeedbackPage />);
    await user.click(await screen.findByRole("button", { name: "Save feedback" }));
    expect(screen.getByText("Pick a person and write a note.")).toBeInTheDocument();
    expect(requests.some((request) => request.init?.method === "POST")).toBe(false);
  });

  it("posts feedback about a colleague", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<FeedbackPage />);
    await screen.findByRole("option", { name: /Grace Hopper/ });
    await user.selectOptions(screen.getByLabelText("About"), MEMBER_USER.user_id);
    await user.selectOptions(screen.getByLabelText("Sentiment"), "NEGATIVE");
    await user.type(screen.getByLabelText("Note"), "Missed two handovers.");
    await user.click(screen.getByRole("button", { name: "Save feedback" }));

    await waitFor(() => {
      const post = requests.find((request) => request.init?.method === "POST");
      expect(post).toBeDefined();
      expect(JSON.parse(String(post?.init?.body))).toEqual({
        subject_id: MEMBER_USER.user_id,
        sentiment: "NEGATIVE",
        body: "Missed two handovers.",
      });
    });
  });

  it("filters by sentiment", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<FeedbackPage />);
    await screen.findByText("About Grace Hopper");
    await user.selectOptions(screen.getByLabelText("Show"), "POSITIVE");
    await waitFor(() => {
      expect(requests.some((request) => request.url.includes("sentiment=POSITIVE"))).toBe(true);
    });
  });
});
