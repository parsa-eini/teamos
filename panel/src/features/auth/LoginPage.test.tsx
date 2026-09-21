import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "@/app/queryClient";
import { LoginPage } from "@/features/auth/LoginPage";
import { AuthProvider } from "@/hooks/useAuth";
import { clearAccessToken } from "@/lib/auth";
import { jsonResponse, OWNER_USER } from "@/test/render";

function renderLogin() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<p>Dashboard home</p>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    clearAccessToken();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("requires email and password", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByText("Email and password are required.")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows an API error when credentials are invalid", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({
        error: { code: "INVALID_CREDENTIALS", message: "Invalid credentials" },
      }),
    } as Response);

    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });

  it("stores the token and navigates to the dashboard on success", async () => {
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/auth/login")) {
        return jsonResponse({ data: { access_token: "access-token", token_type: "bearer" } });
      }
      if (url.includes("/users/me")) {
        return jsonResponse({ data: OWNER_USER });
      }
      return jsonResponse({ error: { code: "RESOURCE_NOT_FOUND", message: "Not found" } }, 404);
    });

    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Dashboard home")).toBeInTheDocument();
  });
});
