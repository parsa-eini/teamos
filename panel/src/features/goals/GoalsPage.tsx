import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CheckboxGroup } from "@/components/CheckboxGroup";
import { MemberMultiSelect } from "@/components/MemberMultiSelect";
import { Pagination } from "@/components/Pagination";
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
import { personName, useOrganizationMembers } from "@/hooks/useOrganizationMembers";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull } from "@/lib/format";
import { createGoal, listGoals, updateGoal } from "@/services/goals";
import { listTasks } from "@/services/tasks";
import { listTeams } from "@/services/teams";
import type { Goal, GoalStatus } from "@/types/api";

const STATUS_TONE: Record<GoalStatus, "slate" | "teal" | "green" | "amber"> = {
  NOT_STARTED: "slate",
  IN_PROGRESS: "teal",
  COMPLETED: "green",
  CANCELLED: "amber",
};

export function GoalsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [teamIds, setTeamIds] = useState<string[]>([]);
  const [ownerIds, setOwnerIds] = useState<string[]>([]);
  const [taskIds, setTaskIds] = useState<string[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingLinksFor, setEditingLinksFor] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["goals", page],
    queryFn: () => listGoals({ page, page_size: 20 }),
  });
  const teamsQuery = useQuery({
    queryKey: ["teams", "picker"],
    queryFn: () => listTeams({ page: 1, page_size: 100 }),
  });
  const tasksQuery = useQuery({
    queryKey: ["tasks", "picker"],
    queryFn: () => listTasks({ page: 1, page_size: 100 }),
  });
  const membersQuery = useOrganizationMembers();
  const people = membersQuery.data?.data;

  const teamOptions = (teamsQuery.data?.data ?? []).map((team) => ({
    id: team.id,
    label: team.name,
  }));
  const taskOptions = (tasksQuery.data?.data ?? []).map((task) => ({
    id: task.id,
    label: `${task.title} (${task.status.replaceAll("_", " ").toLowerCase()})`,
  }));

  const createMutation = useMutation({
    mutationFn: createGoal,
    onSuccess: async () => {
      setTitle("");
      setDescription("");
      setTeamIds([]);
      setOwnerIds([]);
      setTaskIds([]);
      setCreateError(null);
      await queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
    onError: (err) => setCreateError(getErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateGoal>[1] }) =>
      updateGoal(id, payload),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      setCreateError("Goal title is required.");
      return;
    }
    createMutation.mutate({
      title: title.trim(),
      description: emptyToNull(description),
      team_ids: teamIds,
      owner_ids: ownerIds,
      task_ids: taskIds,
    });
  }

  function saveGoal(goal: Goal, payload: Parameters<typeof updateGoal>[1]) {
    setError(null);
    updateMutation.mutate({ id: goal.id, payload });
  }

  function ownerLabel(goal: Goal) {
    if (goal.owner_ids.length === 0) {
      return "No owner";
    }
    return goal.owner_ids.map((userId) => personName(people, userId)).join(", ");
  }

  function teamLabel(goal: Goal) {
    if (goal.team_ids.length === 0) {
      return "Whole organization";
    }
    return goal.team_ids
      .map((teamId) => teamOptions.find((team) => team.id === teamId)?.label ?? "Unknown team")
      .join(", ");
  }

  return (
    <div>
      <PageHeader
        title="Goals"
        description="Track progress from 0 to 100. Linking tasks makes progress follow the work."
      />
      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Create goal</h2>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreate}>
          <div className="md:col-span-2">
            <Label htmlFor="goal-title">Title</Label>
            <Input id="goal-title" value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="goal-description">Description</Label>
            <Textarea
              id="goal-description"
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <CheckboxGroup
            id="goal-teams"
            label="Teams"
            options={teamOptions}
            value={teamIds}
            onChange={setTeamIds}
            isLoading={teamsQuery.isLoading}
            isError={teamsQuery.isError}
            emptyHint="No teams yet. A goal with no team applies to the whole organization."
            errorHint="Could not load teams."
          />
          <MemberMultiSelect
            id="goal-owners"
            label="Owners"
            value={ownerIds}
            onChange={setOwnerIds}
          />
          <div className="md:col-span-2">
            <CheckboxGroup
              id="goal-tasks"
              label="Tasks that measure this goal"
              options={taskOptions}
              value={taskIds}
              onChange={setTaskIds}
              isLoading={tasksQuery.isLoading}
              isError={tasksQuery.isError}
              emptyHint="No tasks yet. Without tasks you set progress by hand."
              errorHint="Could not load tasks."
            />
          </div>
          <div>
            <Button type="submit" disabled={createMutation.isPending}>
              Create goal
            </Button>
          </div>
        </form>
        <FieldError message={createError} />
      </Card>

      {query.isLoading ? <LoadingState label="Loading goals…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState title="No goals yet" description="Create a goal to start tracking progress." />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="space-y-4">
            {query.data.data.map((goal) => (
              <Card key={goal.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="font-medium text-slate-900">{goal.title}</h3>
                    <p className="mt-1 text-sm text-slate-600">{goal.description ?? "No description"}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {teamLabel(goal)} · {ownerLabel(goal)}
                    </p>
                  </div>
                  <Badge tone={STATUS_TONE[goal.status]}>{goal.status.replaceAll("_", " ")}</Badge>
                </div>
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-sm text-slate-600">
                    <span>Progress</span>
                    <span>{goal.progress}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-teal-700"
                      style={{ width: `${goal.progress}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {goal.progress_is_derived
                      ? `Calculated from ${goal.task_ids.length} linked ${
                          goal.task_ids.length === 1 ? "task" : "tasks"
                        }: the share of them that is done.`
                      : "Set by hand. Link tasks to calculate it from completed work."}
                  </p>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {goal.progress_is_derived ? null : (
                    <input
                      aria-label={`Progress for ${goal.title}`}
                      type="range"
                      min={0}
                      max={100}
                      value={goal.progress}
                      onChange={(event) =>
                        saveGoal(goal, { progress: Number(event.target.value) })
                      }
                      className="w-48"
                    />
                  )}
                  <Select
                    aria-label={`Status for ${goal.title}`}
                    value={goal.status}
                    onChange={(event) =>
                      saveGoal(goal, { status: event.target.value as GoalStatus })
                    }
                    className="max-w-xs"
                  >
                    <option value="NOT_STARTED">Not started</option>
                    <option value="IN_PROGRESS">In progress</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="CANCELLED">Cancelled</option>
                  </Select>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() =>
                      setEditingLinksFor(editingLinksFor === goal.id ? null : goal.id)
                    }
                  >
                    {editingLinksFor === goal.id ? "Close links" : "Edit links"}
                  </Button>
                </div>
                {editingLinksFor === goal.id ? (
                  <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 md:grid-cols-3">
                    <CheckboxGroup
                      id={`goal-teams-${goal.id}`}
                      label="Teams"
                      options={teamOptions}
                      value={goal.team_ids}
                      onChange={(ids) => saveGoal(goal, { team_ids: ids })}
                      isLoading={teamsQuery.isLoading}
                      isError={teamsQuery.isError}
                      emptyHint="No teams yet."
                      errorHint="Could not load teams."
                    />
                    <MemberMultiSelect
                      id={`goal-owners-${goal.id}`}
                      label="Owners"
                      value={goal.owner_ids}
                      onChange={(ids) => saveGoal(goal, { owner_ids: ids })}
                    />
                    <CheckboxGroup
                      id={`goal-tasks-${goal.id}`}
                      label="Tasks"
                      options={taskOptions}
                      value={goal.task_ids}
                      onChange={(ids) => saveGoal(goal, { task_ids: ids })}
                      isLoading={tasksQuery.isLoading}
                      isError={tasksQuery.isError}
                      emptyHint="No tasks yet."
                      errorHint="Could not load tasks."
                    />
                  </div>
                ) : null}
                {updateMutation.variables?.id === goal.id && error ? (
                  <FieldError message={error} />
                ) : null}
              </Card>
            ))}
          </div>
          <Pagination meta={query.data.meta} onPageChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
