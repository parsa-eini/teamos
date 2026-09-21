import { apiRequest } from "@/lib/api";
import type { Dashboard, DataResponse } from "@/types/api";

export async function getDashboard(): Promise<Dashboard> {
  const response = await apiRequest<DataResponse<Dashboard>>("/dashboard");
  return response.data;
}
