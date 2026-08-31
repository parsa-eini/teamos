import { apiRequest, toQuery } from "@/lib/api";
import type { CollectionResponse, DataResponse, ListParams, Project, ProjectStatus } from "@/types/api";

export async function listProjects(
  params: ListParams & { status?: ProjectStatus | "" } = {},
): Promise<CollectionResponse<Project>> {
  return apiRequest(`/projects${toQuery(params)}`);
}

export async function getProject(projectId: string): Promise<Project> {
  const response = await apiRequest<DataResponse<Project>>(`/projects/${projectId}`);
  return response.data;
}

export async function createProject(payload: {
  name: string;
  description?: string | null;
  team_id?: string | null;
  status?: ProjectStatus;
  start_date?: string | null;
  end_date?: string | null;
}): Promise<Project> {
  const response = await apiRequest<DataResponse<Project>>("/projects", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function updateProject(
  projectId: string,
  payload: {
    name?: string;
    description?: string | null;
    team_id?: string | null;
    status?: ProjectStatus;
    start_date?: string | null;
    end_date?: string | null;
  },
): Promise<Project> {
  const response = await apiRequest<DataResponse<Project>>(`/projects/${projectId}`, {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}

export async function deleteProject(projectId: string): Promise<void> {
  await apiRequest(`/projects/${projectId}`, { method: "DELETE" });
}
