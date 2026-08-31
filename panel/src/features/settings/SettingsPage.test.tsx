import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "@/features/settings/SettingsPage";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, renderAuthenticated, stubFetch } from "@/test/render";

describe("SettingsPage", () => {
  beforeEach(() => {
    stubFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("loads the current organization and requires name and slug", async () => {
    const user = userEvent.setup();
    renderAuthenticated(<SettingsPage />);
    expect(await screen.findByDisplayValue("Acme")).toBeInTheDocument();
    expect(screen.getByDisplayValue("acme")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Name"));
    await user.clear(screen.getByLabelText("Slug"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Name and slug are required.")).toBeInTheDocument();
  });

  it("saves organization settings", async () => {
    stubFetch((url, init) => {
      if (url.includes("/organizations/current") && init?.method === "PATCH") {
        return jsonResponse({
          data: {
            id: "33333333-3333-4333-8333-333333333333",
            name: "Acme Labs",
            slug: "acme-labs",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-02T00:00:00Z",
          },
        });
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderAuthenticated(<SettingsPage />);
    await screen.findByDisplayValue("Acme");
    await user.clear(screen.getByLabelText("Name"));
    await user.type(screen.getByLabelText("Name"), "Acme Labs");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Organization updated.")).toBeInTheDocument();
  });
});
