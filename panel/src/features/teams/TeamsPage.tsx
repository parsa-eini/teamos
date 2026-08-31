import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Pagination } from "@/components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Button, Card, FieldError, Input, Label, PageHeader, Textarea } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull, formatDateTime } from "@/lib/format";
import { createTeam, listTeams } from "@/services/teams";

export function TeamsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["teams", page],
    queryFn: () => listTeams({ page, page_size: 20 }),
  });

  const createMutation = useMutation({
    mutationFn: createTeam,
    onSuccess: async () => {
      setName("");
      setDescription("");
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["teams"] });
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setFormError("Team name is required.");
      return;
    }
    createMutation.mutate({ name: name.trim(), description: emptyToNull(description) });
  }

  return (
    <div>
      <PageHeader
        title="Teams"
        description="Create teams and open a team to manage members."
      />
      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Create team</h2>
        <form className="grid gap-4 md:grid-cols-[1fr_2fr_auto]" onSubmit={handleCreate}>
          <div>
            <Label htmlFor="team-name">Name</Label>
            <Input id="team-name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div>
            <Label htmlFor="team-description">Description</Label>
            <Textarea
              id="team-description"
              rows={1}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
        </form>
        <FieldError message={formError} />
      </Card>

      {query.isLoading ? <LoadingState label="Loading teams…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState title="No teams yet" description="Create a team to group people and projects." />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.data.map((team) => (
                  <tr key={team.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link className="font-medium text-teal-800 hover:underline" to={`/teams/${team.id}`}>
                        {team.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{team.description ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(team.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination meta={query.data.meta} onPageChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
