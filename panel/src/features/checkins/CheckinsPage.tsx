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
  Textarea,
} from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { personName, useOrganizationMembers } from "@/hooks/useOrganizationMembers";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull, formatDate } from "@/lib/format";
import { createCheckin, listCheckins, updateCheckin } from "@/services/checkins";
import type { CheckIn } from "@/types/api";

const STATUS_TONE = {
  DRAFT: "slate",
  SUBMITTED: "teal",
  REVIEWED: "green",
} as const;

export function CheckinsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [memberId, setMemberId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [wins, setWins] = useState("");
  const [challenges, setChallenges] = useState("");
  const [nextSteps, setNextSteps] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [content, setContent] = useState<
    Record<string, { wins: string; challenges: string; next_steps: string }>
  >({});
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["checkins", page],
    queryFn: () => listCheckins({ page, page_size: 20 }),
  });
  const membersQuery = useOrganizationMembers();
  const people = membersQuery.data?.data;

  const createMutation = useMutation({
    mutationFn: createCheckin,
    onSuccess: async () => {
      setMemberId("");
      setPeriodStart("");
      setPeriodEnd("");
      setWins("");
      setChallenges("");
      setNextSteps("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["checkins"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateCheckin>[1] }) =>
      updateCheckin(id, payload),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["checkins"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!memberId || !periodStart || !periodEnd) {
      setError("Member, start date, and end date are required.");
      return;
    }
    createMutation.mutate({
      member_id: memberId,
      period_start: periodStart,
      period_end: periodEnd,
      wins: emptyToNull(wins),
      challenges: emptyToNull(challenges),
      next_steps: emptyToNull(nextSteps),
    });
  }

  function fieldsFor(checkin: CheckIn) {
    return (
      content[checkin.id] ?? {
        wins: checkin.wins ?? "",
        challenges: checkin.challenges ?? "",
        next_steps: checkin.next_steps ?? "",
      }
    );
  }

  return (
    <div>
      <PageHeader
        title="Check-ins"
        description="Draft, submit, and review periodic check-ins."
      />
      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Create draft</h2>
        <p className="mb-3 text-xs text-slate-500">
          Owners and managers can create a check-in for someone else in the organization.
        </p>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreate}>
          <MemberSelect
            id="member-id"
            label="Member"
            value={memberId}
            onChange={setMemberId}
            emptyLabel="Select a person"
            excludeIds={user ? [user.id] : []}
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="period-start">Period start</Label>
              <Input
                id="period-start"
                type="date"
                value={periodStart}
                onChange={(event) => setPeriodStart(event.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="period-end">Period end</Label>
              <Input
                id="period-end"
                type="date"
                value={periodEnd}
                onChange={(event) => setPeriodEnd(event.target.value)}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="wins">Wins</Label>
            <Textarea id="wins" rows={2} value={wins} onChange={(event) => setWins(event.target.value)} />
          </div>
          <div>
            <Label htmlFor="challenges">Challenges</Label>
            <Textarea
              id="challenges"
              rows={2}
              value={challenges}
              onChange={(event) => setChallenges(event.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="next-steps">Next steps</Label>
            <Textarea
              id="next-steps"
              rows={2}
              value={nextSteps}
              onChange={(event) => setNextSteps(event.target.value)}
            />
          </div>
          <div>
            <Button type="submit" disabled={createMutation.isPending}>
              Create check-in
            </Button>
          </div>
        </form>
        <FieldError message={error} />
      </Card>

      {query.isLoading ? <LoadingState label="Loading check-ins…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState title="No check-ins" description="Create a draft to start the workflow." />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="space-y-4">
            {query.data.data.map((checkin) => {
              const fields = fieldsFor(checkin);
              const isMember = user?.id === checkin.member_id;
              const isManager = user?.id === checkin.manager_id;
              return (
                <Card key={checkin.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {formatDate(checkin.period_start)} – {formatDate(checkin.period_end)}
                      </p>
                      <p className="text-xs text-slate-500">
                        {personName(people, checkin.member_id, "Member")} · Manager{" "}
                        {personName(people, checkin.manager_id, "unknown")}
                      </p>
                    </div>
                    <Badge tone={STATUS_TONE[checkin.status]}>{checkin.status}</Badge>
                  </div>
                  {checkin.status === "DRAFT" ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <Textarea
                        aria-label="Wins"
                        rows={3}
                        value={fields.wins}
                        onChange={(event) =>
                          setContent({
                            ...content,
                            [checkin.id]: { ...fields, wins: event.target.value },
                          })
                        }
                      />
                      <Textarea
                        aria-label="Challenges"
                        rows={3}
                        value={fields.challenges}
                        onChange={(event) =>
                          setContent({
                            ...content,
                            [checkin.id]: { ...fields, challenges: event.target.value },
                          })
                        }
                      />
                      <Textarea
                        aria-label="Next steps"
                        rows={3}
                        value={fields.next_steps}
                        onChange={(event) =>
                          setContent({
                            ...content,
                            [checkin.id]: { ...fields, next_steps: event.target.value },
                          })
                        }
                      />
                    </div>
                  ) : (
                    <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                      <div>
                        <dt className="font-medium text-slate-700">Wins</dt>
                        <dd className="mt-1 text-slate-600">{checkin.wins || "—"}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-slate-700">Challenges</dt>
                        <dd className="mt-1 text-slate-600">{checkin.challenges || "—"}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-slate-700">Next steps</dt>
                        <dd className="mt-1 text-slate-600">{checkin.next_steps || "—"}</dd>
                      </div>
                    </dl>
                  )}
                  {checkin.manager_notes ? (
                    <p className="mt-3 text-sm text-slate-600">
                      <span className="font-medium text-slate-700">Manager notes: </span>
                      {checkin.manager_notes}
                    </p>
                  ) : null}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {checkin.status === "DRAFT" ? (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          updateMutation.mutate({
                            id: checkin.id,
                            payload: {
                              wins: emptyToNull(fields.wins),
                              challenges: emptyToNull(fields.challenges),
                              next_steps: emptyToNull(fields.next_steps),
                            },
                          })
                        }
                      >
                        Save draft
                      </Button>
                    ) : null}
                    {checkin.status === "DRAFT" && isMember ? (
                      <Button
                        type="button"
                        onClick={() =>
                          updateMutation.mutate({
                            id: checkin.id,
                            payload: {
                              wins: emptyToNull(fields.wins),
                              challenges: emptyToNull(fields.challenges),
                              next_steps: emptyToNull(fields.next_steps),
                              status: "SUBMITTED",
                            },
                          })
                        }
                      >
                        Submit
                      </Button>
                    ) : null}
                    {checkin.status === "SUBMITTED" && isManager ? (
                      <>
                        <Textarea
                          className="min-w-[16rem] flex-1"
                          rows={2}
                          placeholder="Manager notes"
                          value={notes[checkin.id] ?? checkin.manager_notes ?? ""}
                          onChange={(event) =>
                            setNotes({ ...notes, [checkin.id]: event.target.value })
                          }
                        />
                        <Button
                          type="button"
                          onClick={() =>
                            updateMutation.mutate({
                              id: checkin.id,
                              payload: {
                                manager_notes: emptyToNull(notes[checkin.id] ?? ""),
                                status: "REVIEWED",
                              },
                            })
                          }
                        >
                          Mark reviewed
                        </Button>
                      </>
                    ) : null}
                  </div>
                </Card>
              );
            })}
          </div>
          <Pagination meta={query.data.meta} onPageChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
