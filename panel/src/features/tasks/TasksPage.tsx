import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Pagination } from "@/components/Pagination";
import { MemberSelect } from "@/components/MemberSelect";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import {
  Badge,
  Button,
  Card,
  FieldError,
  Input,
  Label,
  PageHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull, formatDate } from "@/lib/format";
import { listProjects } from "@/services/projects";
import { createTask, deleteTask, listTasks, updateTask } from "@/services/tasks";
import type { Task, TaskPriority, TaskStatus } from "@/types/api";

const STATUS_TONE: Record<TaskStatus, "slate" | "teal" | "green" | "amber"> = {
  TODO: "slate",
  IN_PROGRESS: "teal",
  DONE: "green",
  CANCELLED: "amber",
};

const PRIORITY_TONE: Record<TaskPriority, "slate" | "blue" | "amber" | "red"> = {
  LOW: "slate",
  MEDIUM: "blue",
  HIGH: "amber",
  URGENT: "red",
};

const emptyForm = {
  project_id: "",
  title: "",
  description: "",
  status: "TODO" as TaskStatus,
  priority: "MEDIUM" as TaskPriority,
  assignee_id: "",
  due_date: "",
};

export function TasksPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<TaskStatus | "">("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [assigneeId, setAssigneeId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<Task | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filters = {
    page,
    page_size: 20,
    status,
    priority,
    assignee_id: assigneeId.trim() || undefined,
    project_id: projectId.trim() || undefined,
  };

  const query = useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => listTasks(filters),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects", "picker"],
    queryFn: () => listProjects({ page: 1, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: async () => {
      setForm(emptyForm);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateTask>[1] }) =>
      updateTask(id, payload),
    onSuccess: async () => {
      setEditing(null);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: async () => {
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.title.trim() || !form.project_id) {
      setError("Title and a project are required.");
      return;
    }
    createMutation.mutate({
      project_id: form.project_id,
      title: form.title.trim(),
      description: emptyToNull(form.description),
      status: form.status,
      priority: form.priority,
      assignee_id: emptyToNull(form.assignee_id),
      due_date: emptyToNull(form.due_date),
    });
  }

  function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) {
      return;
    }
    if (!form.title.trim()) {
      setError("Title is required.");
      return;
    }
    updateMutation.mutate({
      id: editing.id,
      payload: {
        project_id: form.project_id || undefined,
        title: form.title.trim(),
        description: emptyToNull(form.description),
        status: form.status,
        priority: form.priority,
        assignee_id: emptyToNull(form.assignee_id),
        due_date: emptyToNull(form.due_date),
      },
    });
  }

  function startEdit(task: Task) {
    setEditing(task);
    setForm({
      project_id: task.project_id,
      title: task.title,
      description: task.description ?? "",
      status: task.status,
      priority: task.priority,
      assignee_id: task.assignee_id ?? "",
      due_date: task.due_date ?? "",
    });
    setError(null);
  }

  return (
    <div>
      <PageHeader
        title="Tasks"
        description="Filter, create, assign, and update work items."
      />
      <Card className="mb-6">
        <div className="grid gap-3 md:grid-cols-4">
          <Select
            aria-label="Status"
            value={status}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value as TaskStatus | "");
            }}
          >
            <option value="">All statuses</option>
            <option value="TODO">To do</option>
            <option value="IN_PROGRESS">In progress</option>
            <option value="DONE">Done</option>
            <option value="CANCELLED">Cancelled</option>
          </Select>
          <Select
            aria-label="Priority"
            value={priority}
            onChange={(event) => {
              setPage(1);
              setPriority(event.target.value as TaskPriority | "");
            }}
          >
            <option value="">All priorities</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </Select>
          <Select
            aria-label="Project"
            value={projectId}
            onChange={(event) => {
              setPage(1);
              setProjectId(event.target.value);
            }}
          >
            <option value="">All projects</option>
            {(projectsQuery.data?.data ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>
          <MemberSelect
            id="filter-assignee"
            value={assigneeId}
            onChange={(userId) => {
              setPage(1);
              setAssigneeId(userId);
            }}
            allowEmpty
            emptyLabel="All assignees"
          />
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <div>
          {query.isLoading ? <LoadingState label="Loading tasks…" /> : null}
          {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
          {query.data && query.data.data.length === 0 ? (
            <EmptyState title="No tasks match these filters" />
          ) : null}
          {query.data && query.data.data.length > 0 ? (
            <>
              <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3">Title</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Priority</th>
                      <th className="px-4 py-3">Due</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {query.data.data.map((task) => (
                      <tr
                        key={task.id}
                        className={`cursor-pointer hover:bg-slate-50 ${editing?.id === task.id ? "bg-teal-50" : ""}`}
                        onClick={() => startEdit(task)}
                      >
                        <td className="px-4 py-3 font-medium text-slate-900">{task.title}</td>
                        <td className="px-4 py-3">
                          <Badge tone={STATUS_TONE[task.status]}>{task.status}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={PRIORITY_TONE[task.priority]}>{task.priority}</Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-600">{formatDate(task.due_date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination meta={query.data.meta} onPageChange={setPage} />
            </>
          ) : null}
        </div>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-900">
            {editing ? "Edit task" : "Create task"}
          </h2>
          <form className="space-y-3" onSubmit={editing ? handleUpdate : handleCreate}>
            <div>
              <Label htmlFor="task-title">Title</Label>
              <Input
                id="task-title"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="task-project">Project</Label>
              <Select
                id="task-project"
                value={form.project_id}
                onChange={(event) => setForm({ ...form, project_id: event.target.value })}
              >
                <option value="">Select a project</option>
                {(projectsQuery.data?.data ?? []).map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="task-description">Description</Label>
              <Textarea
                id="task-description"
                rows={3}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="task-status">Status</Label>
                <Select
                  id="task-status"
                  value={form.status}
                  onChange={(event) => setForm({ ...form, status: event.target.value as TaskStatus })}
                >
                  <option value="TODO">To do</option>
                  <option value="IN_PROGRESS">In progress</option>
                  <option value="DONE">Done</option>
                  <option value="CANCELLED">Cancelled</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="task-priority">Priority</Label>
                <Select
                  id="task-priority"
                  value={form.priority}
                  onChange={(event) =>
                    setForm({ ...form, priority: event.target.value as TaskPriority })
                  }
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </Select>
              </div>
            </div>
            <MemberSelect
              id="task-assignee"
              label="Assignee"
              value={form.assignee_id}
              onChange={(userId) => setForm({ ...form, assignee_id: userId })}
              allowEmpty
              emptyLabel="Unassigned"
            />
            <div>
              <Label htmlFor="task-due">Due date</Label>
              <Input
                id="task-due"
                type="date"
                value={form.due_date}
                onChange={(event) => setForm({ ...form, due_date: event.target.value })}
              />
            </div>
            <FieldError message={error} />
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {editing ? "Save changes" : "Create task"}
              </Button>
              {editing ? (
                <>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setEditing(null);
                      setForm(emptyForm);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    onClick={() => {
                      if (window.confirm("Delete this task?")) {
                        deleteMutation.mutate(editing.id);
                      }
                    }}
                  >
                    Delete
                  </Button>
                </>
              ) : null}
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
