import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout";
import { clearAccessToken } from "@/lib/auth";
import { renderAuthenticated, stubFetch } from "@/test/render";

const ACTIVE_CLASS = "bg-teal-700";

function renderNavAt(route: string) {
  return renderAuthenticated(
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/organization" element={<p>Organization</p>} />
        <Route path="/organization/members" element={<p>Members</p>} />
      </Route>
    </Routes>,
    { route },
  );
}

describe("AppLayout navigation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("highlights only Members on the members page", async () => {
    stubFetch();
    renderNavAt("/organization/members");
    expect(await screen.findByRole("link", { name: "Members" })).toHaveClass(ACTIVE_CLASS);
    expect(screen.getByRole("link", { name: "Organization" })).not.toHaveClass(ACTIVE_CLASS);
  });

  it("highlights only Organization on the organization page", async () => {
    stubFetch();
    renderNavAt("/organization");
    expect(await screen.findByRole("link", { name: "Organization" })).toHaveClass(ACTIVE_CLASS);
    expect(screen.getByRole("link", { name: "Members" })).not.toHaveClass(ACTIVE_CLASS);
  });
});
