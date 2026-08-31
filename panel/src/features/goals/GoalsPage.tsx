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
import { emptyToNull } from "@/lib/format";
import { createGoal, listGoals, updateGoal } from "@/services/goals";
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
  const [teamId, setTeamId] = useState("");
  const [userId, setUserId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["goals", page],
    queryFn: () => listGoals({ page, page_size: 20 }),
  });
  const teamsQuery = useQuery({
    queryKey: ["teams", "picker"],
    queryFn: () => listTeams({ page: 1, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: createGoal,
    onSuccess: async () => {
      setTitle("");
      setDescription("");
      setTeamId("");
      setUserId("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateGoal>[1] }) =>
      updateGoal(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      setError("Goal title is required.");
      return;
    }
    createMutation.mutate({
      title: title.trim(),
      description: emptyToNull(description),
      team_id: emptyToNull(teamId),
      user_id: emptyToNull(userId),
    });
  }

  function saveGoal(goal: Goal, changes: Partial<Goal>) {
    updateMutation.mutate({
      id: goal.id,
      payload: {
        status: changes.status,
        progress: changes.progress,
      },
    });
  }

  return (
    <div>
      <PageHeader title="Goals" description="Track progress from 0 to 100." />
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
          <div>
            <Label htmlFor="goal-team">Team</Label>
            <Select id="goal-team" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
              <option value="">None</option>
              {(teamsQuery.data?.data ?? []).map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </Select>
          </div>
          <MemberSelect
            id="goal-user"
            label="Owner"
            value={userId}
            onChange={setUserId}
            allowEmpty
            emptyLabel="No owner"
          />
          <div>
            <Button type="submit" disabled={createMutation.isPending}>
              Create goal
            </Button>
          </div>
        </form>
        <FieldError message={error} />
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
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <input
                    aria-label={`Progress for ${goal.title}`}
                    type="range"
                    min={0}
                    max={100}
                    value={goal.progress}
                    onChange={(event) => saveGoal(goal, { progress: Number(event.target.value) })}
                    className="w-48"
                  />
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
                </div>
              </Card>
            ))}
          </div>
          <Pagination meta={query.data.meta} onPageChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
