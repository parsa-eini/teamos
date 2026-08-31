import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "@/lib/api";
import { clearAccessToken, setAccessToken } from "@/lib/auth";
import { ApiError } from "@/lib/errors";

describe("apiRequest", () => {
  beforeEach(() => {
    clearAccessToken();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ data: { id: "1" } }),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("sends a bearer token when one is stored", async () => {
    setAccessToken("test-token");
    await apiRequest("/users/me");
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/users/me",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer test-token");
  });

  it("parses the API error envelope", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: { code: "RESOURCE_NOT_FOUND", message: "Team not found" } }),
    } as Response);

    await expect(apiRequest("/teams/missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "RESOURCE_NOT_FOUND",
      message: "Team not found",
    } satisfies Partial<ApiError>);
  });
});
