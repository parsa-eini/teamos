import { apiRequest, toQuery } from "@/lib/api";
import type {
  CollectionResponse,
  DataResponse,
  ListParams,
  Task,
  TaskPriority,
  TaskStatus,
} from "@/types/api";

export type TaskListParams = ListParams & {
  status?: TaskStatus | "";
  priority?: TaskPriority | "";
  assignee_id?: string;
  project_id?: string;
};

export async function listTasks(params: TaskListParams = {}): Promise<CollectionResponse<Task>> {
  return apiRequest(`/tasks${toQuery(params)}`);
}

export async function getTask(taskId: string): Promise<Task> {
  const response = await apiRequest<DataResponse<Task>>(`/tasks/${taskId}`);
  return response.data;
}

export async function createTask(payload: {
  project_id: string;
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string | null;
  due_date?: string | null;
}): Promise<Task> {
  const response = await apiRequest<DataResponse<Task>>("/tasks", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function updateTask(
  taskId: string,
  payload: {
    project_id?: string;
    title?: string;
    description?: string | null;
    status?: TaskStatus;
    priority?: TaskPriority;
    assignee_id?: string | null;
    due_date?: string | null;
  },
): Promise<Task> {
  const response = await apiRequest<DataResponse<Task>>(`/tasks/${taskId}`, {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiRequest(`/tasks/${taskId}`, { method: "DELETE" });
}
