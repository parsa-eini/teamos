import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { LandingPage } from "@/features/landing/LandingPage";

describe("LandingPage", () => {
  it("renders the hero, problem, solution, features, and CTA", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", {
        name: /Know what the team committed to/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The problem" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The solution" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Features" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Create an account" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Get started" }).length).toBeGreaterThan(0);
  });
});
