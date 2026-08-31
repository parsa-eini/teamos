import { apiRequest } from "@/lib/api";
import type { DataResponse, TokenResponse, User } from "@/types/api";

export async function login(email: string, password: string): Promise<TokenResponse> {
  const response = await apiRequest<DataResponse<TokenResponse>>("/auth/login", {
    method: "POST",
    body: { email, password },
    skipAuth: true,
  });
  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiRequest<DataResponse<User>>("/users/me");
  return response.data;
}
