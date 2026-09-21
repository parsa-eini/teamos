import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button, Card, FieldError, Input, Label, PageHeader, Select, Textarea } from "@/components/ui";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull } from "@/lib/format";
import { deleteProject, getProject, updateProject } from "@/services/projects";
import { listTeams } from "@/services/teams";
import type { ProjectStatus } from "@/types/api";

export function ProjectDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [teamId, setTeamId] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("PLANNED");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const query = useQuery({
    queryKey: ["projects", id],
    queryFn: () => getProject(id),
    enabled: Boolean(id),
  });
  const teamsQuery = useQuery({
    queryKey: ["teams", "picker"],
    queryFn: () => listTeams({ page: 1, page_size: 100 }),
  });

  useEffect(() => {
    if (query.data && !hydrated) {
      setName(query.data.name);
      setDescription(query.data.description ?? "");
      setTeamId(query.data.team_id ?? "");
      setStatus(query.data.status);
      setStartDate(query.data.start_date ?? "");
      setEndDate(query.data.end_date ?? "");
      setHydrated(true);
    }
  }, [hydrated, query.data]);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateProject(id, {
        name: name.trim(),
        description: emptyToNull(description),
        team_id: emptyToNull(teamId),
        status,
        start_date: emptyToNull(startDate),
        end_date: emptyToNull(endDate),
      }),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate("/projects");
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }
    updateMutation.mutate();
  }

  if (query.isLoading) {
    return <LoadingState label="Loading project…" />;
  }
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (!query.data) {
    return <EmptyState title="Project not found" />;
  }

  return (
    <div>
      <PageHeader
        title={query.data.name}
        actions={
          <Link to="/projects" className="text-sm text-teal-700 hover:underline">
            Back to projects
          </Link>
        }
      />
      <Card className="max-w-2xl">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              rows={4}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="team">Team</Label>
            <Select id="team" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
              <option value="">Organization-wide</option>
              {(teamsQuery.data?.data ?? []).map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="status">Status</Label>
            <Select
              id="status"
              value={status}
              onChange={(event) => setStatus(event.target.value as ProjectStatus)}
            >
              <option value="PLANNED">Planned</option>
              <option value="ACTIVE">Active</option>
              <option value="COMPLETED">Completed</option>
              <option value="ARCHIVED">Archived</option>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="start">Start date</Label>
              <Input
                id="start"
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="end">End date</Label>
              <Input id="end" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </div>
          </div>
          <FieldError message={error} />
          <div className="flex gap-2">
            <Button type="submit" disabled={updateMutation.isPending}>
              Save
            </Button>
            <Button
              type="button"
              variant="danger"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (window.confirm("Delete this project?")) {
                  deleteMutation.mutate();
                }
              }}
            >
              Delete
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
