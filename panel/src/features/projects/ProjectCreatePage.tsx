import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { Button, Card, FieldError, Input, Label, PageHeader, Select, Textarea } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull, isUuid } from "@/lib/format";
import { createProject } from "@/services/projects";
import { listTeams } from "@/services/teams";
import type { ProjectStatus } from "@/types/api";

export function ProjectCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [teamId, setTeamId] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("PLANNED");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const teamsQuery = useQuery({
    queryKey: ["teams", "picker"],
    queryFn: () => listTeams({ page: 1, page_size: 100 }),
  });

  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}`);
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }
    if (teamId && !isUuid(teamId)) {
      setError("Team ID must be a valid UUID.");
      return;
    }
    mutation.mutate({
      name: name.trim(),
      description: emptyToNull(description),
      team_id: emptyToNull(teamId),
      status,
      start_date: emptyToNull(startDate),
      end_date: emptyToNull(endDate),
    });
  }

  return (
    <div>
      <PageHeader
        title="New project"
        actions={
          <Link to="/projects" className="text-sm text-teal-700 hover:underline">
            Cancel
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
              <Input
                id="end"
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </div>
          </div>
          <FieldError message={error} />
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Creating…" : "Create project"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
