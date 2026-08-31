import { apiRequest, toQuery } from "@/lib/api";
import type { CollectionResponse, DataResponse, Goal, GoalStatus, ListParams } from "@/types/api";

export async function listGoals(params: ListParams = {}): Promise<CollectionResponse<Goal>> {
  return apiRequest(`/goals${toQuery(params)}`);
}

export async function createGoal(payload: {
  title: string;
  description?: string | null;
  team_id?: string | null;
  user_id?: string | null;
  status?: GoalStatus;
  progress?: number;
  start_date?: string | null;
  due_date?: string | null;
}): Promise<Goal> {
  const response = await apiRequest<DataResponse<Goal>>("/goals", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function updateGoal(
  goalId: string,
  payload: {
    title?: string;
    description?: string | null;
    team_id?: string | null;
    user_id?: string | null;
    status?: GoalStatus;
    progress?: number;
    start_date?: string | null;
    due_date?: string | null;
  },
): Promise<Goal> {
  const response = await apiRequest<DataResponse<Goal>>(`/goals/${goalId}`, {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}
