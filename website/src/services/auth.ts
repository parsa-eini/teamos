import { apiRequest } from "@/lib/api";

export async function registerAccount(payload: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  organization_name: string;
}): Promise<void> {
  await apiRequest("/auth/register", { method: "POST", body: payload });
}

export async function login(email: string, password: string): Promise<string> {
  const data = await apiRequest<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  return data.access_token;
}
