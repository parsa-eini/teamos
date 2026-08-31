import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Pagination } from "@/components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge, Button, Card, FieldError, Input, Label, PageHeader, Select } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { organizationMembersQueryKey } from "@/hooks/useOrganizationMembers";
import { getErrorMessage } from "@/lib/errors";
import { displayName, formatDateTime } from "@/lib/format";
import {
  createOrganizationMember,
  getCurrentOrganization,
  listOrganizationMembers,
} from "@/services/organizations";
import type { OrganizationRole } from "@/types/api";

const ROLE_TONE: Record<OrganizationRole, "teal" | "blue" | "amber" | "slate"> = {
  OWNER: "teal",
  ADMIN: "blue",
  MANAGER: "amber",
  MEMBER: "slate",
};

export function OrganizationPage() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ["organizations", "current"],
    queryFn: getCurrentOrganization,
  });

  if (query.isLoading) {
    return <LoadingState label="Loading organization…" />;
  }
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (!query.data) {
    return <EmptyState title="Organization not found" />;
  }

  const organization = query.data;

  return (
    <div>
      <PageHeader
        title="Organization"
        description="Current workspace derived from your membership."
      />
      <Card className="max-w-2xl">
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Name</dt>
            <dd className="mt-1 font-medium text-slate-900">{organization.name}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Slug</dt>
            <dd className="mt-1 font-medium text-slate-900">{organization.slug}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Created</dt>
            <dd className="mt-1 text-slate-900">{formatDateTime(organization.created_at)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Updated</dt>
            <dd className="mt-1 text-slate-900">{formatDateTime(organization.updated_at)}</dd>
          </div>
        </dl>
        <p className="mt-6 text-sm text-slate-600">
          Signed in as {user ? displayName(user.first_name, user.last_name) : "the current user"}.
          Organization settings are on the{" "}
          <Link className="text-teal-700 hover:underline" to="/settings">
            settings
          </Link>{" "}
          page. People are managed under{" "}
          <Link className="text-teal-700 hover:underline" to="/organization/members">
            members
          </Link>
          .
        </p>
      </Card>
    </div>
  );
}

export function OrganizationMembersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Exclude<OrganizationRole, "OWNER">>("MEMBER");
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: [...organizationMembersQueryKey, page],
    queryFn: () => listOrganizationMembers({ page, page_size: 20 }),
  });

  const createMutation = useMutation({
    mutationFn: createOrganizationMember,
    onSuccess: async () => {
      setFirstName("");
      setLastName("");
      setEmail("");
      setPassword("");
      setRole("MEMBER");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: organizationMembersQueryKey });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!firstName.trim() || !lastName.trim() || !email.trim() || password.length < 8) {
      setError("Name, email, and a password of at least 8 characters are required.");
      return;
    }
    createMutation.mutate({
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      email: email.trim(),
      password,
      role,
    });
  }

  return (
    <div>
      <PageHeader
        title="Members"
        description="People in this organization. Owners and admins can add members; they sign in with the email and password you set."
      />
      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Add member</h2>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreate}>
          <div>
            <Label htmlFor="member-first-name">First name</Label>
            <Input
              id="member-first-name"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="member-last-name">Last name</Label>
            <Input
              id="member-last-name"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="member-email">Email</Label>
            <Input
              id="member-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="member-password">Password</Label>
            <Input
              id="member-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="member-role">Role</Label>
            <Select
              id="member-role"
              value={role}
              onChange={(event) => setRole(event.target.value as Exclude<OrganizationRole, "OWNER">)}
            >
              <option value="MEMBER">Member</option>
              <option value="MANAGER">Manager</option>
              <option value="ADMIN">Admin</option>
            </Select>
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Adding…" : "Add member"}
            </Button>
          </div>
        </form>
        <FieldError message={error} />
      </Card>

      {query.isLoading ? <LoadingState label="Loading members…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState title="No members" description="Add someone to this organization." />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.data.map((member) => (
                  <tr key={member.user_id}>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {displayName(member.first_name, member.last_name)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{member.email}</td>
                    <td className="px-4 py-3">
                      <Badge tone={ROLE_TONE[member.role]}>{member.role}</Badge>
                    </td>
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
