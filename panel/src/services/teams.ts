import { apiRequest, toQuery } from "@/lib/api";
import type { CollectionResponse, DataResponse, ListParams, Team, TeamMember } from "@/types/api";

export async function listTeams(params: ListParams = {}): Promise<CollectionResponse<Team>> {
  return apiRequest(`/teams${toQuery(params)}`);
}

export async function getTeam(teamId: string): Promise<Team> {
  const response = await apiRequest<DataResponse<Team>>(`/teams/${teamId}`);
  return response.data;
}

export async function createTeam(payload: {
  name: string;
  description?: string | null;
}): Promise<Team> {
  const response = await apiRequest<DataResponse<Team>>("/teams", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function updateTeam(
  teamId: string,
  payload: { name?: string; description?: string | null },
): Promise<Team> {
  const response = await apiRequest<DataResponse<Team>>(`/teams/${teamId}`, {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}

export async function deleteTeam(teamId: string): Promise<void> {
  await apiRequest(`/teams/${teamId}`, { method: "DELETE" });
}

export async function listTeamMembers(
  teamId: string,
  params: ListParams = {},
): Promise<CollectionResponse<TeamMember>> {
  return apiRequest(`/teams/${teamId}/members${toQuery(params)}`);
}

export async function addTeamMember(teamId: string, userId: string): Promise<TeamMember> {
  const response = await apiRequest<DataResponse<TeamMember>>(`/teams/${teamId}/members`, {
    method: "POST",
    body: { user_id: userId },
  });
  return response.data;
}

export async function removeTeamMember(teamId: string, userId: string): Promise<void> {
  await apiRequest(`/teams/${teamId}/members/${userId}`, { method: "DELETE" });
}
