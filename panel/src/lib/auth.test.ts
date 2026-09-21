import { afterEach, describe, expect, it } from "vitest";

import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/auth";

describe("access token storage", () => {
  afterEach(() => {
    clearAccessToken();
  });

  it("stores and clears the access token", () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken("abc");
    expect(getAccessToken()).toBe("abc");
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });
});
