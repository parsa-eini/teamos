import { apiRequest, toQuery } from "@/lib/api";
import type {
  CollectionResponse,
  DataResponse,
  ListParams,
  Meeting,
  MeetingStatus,
  MeetingType,
} from "@/types/api";

export type MeetingListParams = ListParams & {
  type?: MeetingType | "";
};

export async function listMeetings(
  params: MeetingListParams = {},
): Promise<CollectionResponse<Meeting>> {
  return apiRequest(`/meetings${toQuery(params)}`);
}

export async function createMeeting(payload: {
  member_id: string;
  manager_id?: string | null;
  type?: MeetingType;
  scheduled_on: string;
  wins?: string | null;
  challenges?: string | null;
  next_steps?: string | null;
}): Promise<Meeting> {
  const response = await apiRequest<DataResponse<Meeting>>("/meetings", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function updateMeeting(
  meetingId: string,
  payload: {
    type?: MeetingType;
    scheduled_on?: string;
    status?: MeetingStatus;
    wins?: string | null;
    challenges?: string | null;
    next_steps?: string | null;
    manager_notes?: string | null;
  },
): Promise<Meeting> {
  const response = await apiRequest<DataResponse<Meeting>>(`/meetings/${meetingId}`, {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}
