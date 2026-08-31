export type PaginationMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type DataResponse<T> = {
  data: T;
};

export type CollectionResponse<T> = {
  data: T[];
  meta: PaginationMeta;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
  };
};

export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
};

export type OrganizationRole = "OWNER" | "ADMIN" | "MANAGER" | "MEMBER";

export type OrganizationMember = {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: OrganizationRole;
  created_at: string;
};

export type Team = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type TeamMember = {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  created_at: string;
};

export type ProjectStatus = "PLANNED" | "ACTIVE" | "COMPLETED" | "ARCHIVED";

export type Project = {
  id: string;
  name: string;
  description: string | null;
  team_id: string | null;
  status: ProjectStatus;
  start_date: string | null;
  end_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE" | "CANCELLED";
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type Task = {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assignee_id: string | null;
  due_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type GoalStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type Goal = {
  id: string;
  title: string;
  description: string | null;
  team_id: string | null;
  user_id: string | null;
  status: GoalStatus;
  progress: number;
  start_date: string | null;
  due_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type CheckInStatus = "DRAFT" | "SUBMITTED" | "REVIEWED";

export type CheckIn = {
  id: string;
  manager_id: string;
  member_id: string;
  period_start: string;
  period_end: string;
  status: CheckInStatus;
  wins: string | null;
  challenges: string | null;
  next_steps: string | null;
  manager_notes: string | null;
  created_at: string;
  updated_at: string;
};

export type Dashboard = {
  member_count: number;
  active_projects: number;
  open_tasks: number;
  overdue_tasks: number;
  goal_summary: {
    total: number;
    items: Array<{
      id: string;
      title: string;
      progress: number;
      status: GoalStatus;
    }>;
  };
  recent_checkins: Array<{
    id: string;
    member_id: string;
    status: CheckInStatus;
    period_start: string;
    period_end: string;
    updated_at: string;
  }>;
  recent_activity: Array<{
    type: string;
    message: string;
    occurred_at: string;
  }>;
};

export type ListParams = {
  page?: number;
  page_size?: number;
};
