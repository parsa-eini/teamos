import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RegisterPage } from "@/features/auth/RegisterPage";

describe("RegisterPage", () => {
  it("validates required fields before calling the API", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(
      screen.getByText("All fields are required. Password must be at least 8 characters."),
    ).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
