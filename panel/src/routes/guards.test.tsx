import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "@/app/queryClient";
import { AuthProvider } from "@/hooks/useAuth";
import { clearAccessToken } from "@/lib/auth";
import { ProtectedRoute } from "@/routes/guards";
import { stubFetch } from "@/test/render";

function renderGuarded(initial: string) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initial]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<p>Login screen</p>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<p>Protected dashboard</p>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("redirects unauthenticated visitors to login", async () => {
    stubFetch();
    renderGuarded("/dashboard");
    expect(await screen.findByText("Login screen")).toBeInTheDocument();
  });
});
