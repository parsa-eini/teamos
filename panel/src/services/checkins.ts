import { apiRequest, toQuery } from "@/lib/api";
import type { CheckIn, CheckInStatus, CollectionResponse, DataResponse, ListParams } from "@/types/api";

export async function listCheckins(params: ListParams = {}): Promise<CollectionResponse<CheckIn>> {
  return apiRequest(`/checkins${toQuery(params)}`);
}

export async function createCheckin(payload: {
  member_id: string;
  manager_id?: string | null;
  period_start: string;
  period_end: string;
  wins?: string | null;
  challenges?: string | null;
  next_steps?: string | null;
}): Promise<CheckIn> {
  const response = await apiRequest<DataResponse<CheckIn>>("/checkins", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function updateCheckin(
  checkinId: string,
  payload: {
    period_start?: string;
    period_end?: string;
    status?: CheckInStatus;
    wins?: string | null;
    challenges?: string | null;
    next_steps?: string | null;
    manager_notes?: string | null;
  },
): Promise<CheckIn> {
  const response = await apiRequest<DataResponse<CheckIn>>(`/checkins/${checkinId}`, {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}
