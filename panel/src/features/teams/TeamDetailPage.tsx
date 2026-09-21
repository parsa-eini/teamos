import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Pagination } from "@/components/Pagination";
import { MemberSelect } from "@/components/MemberSelect";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Button, Card, FieldError, Input, Label, PageHeader, Textarea } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { displayName, emptyToNull } from "@/lib/format";
import {
  addTeamMember,
  deleteTeam,
  getTeam,
  listTeamMembers,
  removeTeamMember,
  updateTeam,
} from "@/services/teams";

export function TeamDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [memberId, setMemberId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const teamQuery = useQuery({
    queryKey: ["teams", id],
    queryFn: () => getTeam(id),
    enabled: Boolean(id),
  });

  const membersQuery = useQuery({
    queryKey: ["teams", id, "members", page],
    queryFn: () => listTeamMembers(id, { page, page_size: 20 }),
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (teamQuery.data && !hydrated) {
      setName(teamQuery.data.name);
      setDescription(teamQuery.data.description ?? "");
      setHydrated(true);
    }
  }, [hydrated, teamQuery.data]);

  const updateMutation = useMutation({
    mutationFn: () => updateTeam(id, { name: name.trim(), description: emptyToNull(description) }),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["teams", id] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteTeam(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["teams"] });
      navigate("/teams");
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) => addTeamMember(id, userId),
    onSuccess: async () => {
      setMemberId("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["teams", id, "members"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeTeamMember(id, userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["teams", id, "members"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Team name is required.");
      return;
    }
    updateMutation.mutate();
  }

  function handleAddMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!memberId) {
      setError("Select a person to add to this team.");
      return;
    }
    addMutation.mutate(memberId);
  }

  if (teamQuery.isLoading) {
    return <LoadingState label="Loading team…" />;
  }
  if (teamQuery.isError) {
    return <ErrorState error={teamQuery.error} onRetry={() => void teamQuery.refetch()} />;
  }
  if (!teamQuery.data) {
    return <EmptyState title="Team not found" />;
  }

  return (
    <div>
      <PageHeader
        title={teamQuery.data.name}
        description="Team details and membership."
        actions={
          <Link to="/teams" className="text-sm text-teal-700 hover:underline">
            Back to teams
          </Link>
        }
      />
      <FieldError message={error} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Details</h2>
          <form className="space-y-4" onSubmit={handleUpdate}>
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
            <div className="flex gap-2">
              <Button type="submit" disabled={updateMutation.isPending}>
                Save
              </Button>
              <Button
                type="button"
                variant="danger"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (window.confirm("Delete this team?")) {
                    deleteMutation.mutate();
                  }
                }}
              >
                Delete
              </Button>
            </div>
          </form>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Members</h2>
          <p className="mb-3 text-xs text-slate-500">
            Choose someone who already belongs to this organization. Add new people from{" "}
            <Link to="/organization/members" className="text-teal-700 hover:underline">
              Members
            </Link>
            .
          </p>
          <form className="mb-4 flex items-end gap-2" onSubmit={handleAddMember}>
            <div className="min-w-0 flex-1">
              <MemberSelect
                id="team-member"
                value={memberId}
                onChange={setMemberId}
                emptyLabel="Select a person"
                excludeIds={(membersQuery.data?.data ?? []).map((member) => member.user_id)}
              />
            </div>
            <Button type="submit" disabled={addMutation.isPending}>
              Add
            </Button>
          </form>
          {membersQuery.isLoading ? <LoadingState label="Loading members…" /> : null}
          {membersQuery.isError ? (
            <ErrorState error={membersQuery.error} onRetry={() => void membersQuery.refetch()} />
          ) : null}
          {membersQuery.data && membersQuery.data.data.length === 0 ? (
            <EmptyState title="No members" description="Add a person from this organization." />
          ) : null}
          {membersQuery.data && membersQuery.data.data.length > 0 ? (
            <>
              <ul className="divide-y divide-slate-100">
                {membersQuery.data.data.map((member) => (
                  <li key={member.user_id} className="flex items-center justify-between py-3 text-sm">
                    <div>
                      <p className="font-medium text-slate-900">
                        {displayName(member.first_name, member.last_name)}
                      </p>
                      <p className="text-xs text-slate-500">{member.email}</p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => removeMutation.mutate(member.user_id)}
                    >
                      Remove
                    </Button>
                  </li>
                ))}
              </ul>
              <Pagination meta={membersQuery.data.meta} onPageChange={setPage} />
            </>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
