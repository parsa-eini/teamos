import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { MemberSelect } from "@/components/MemberSelect";
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
import { useAuth } from "@/hooks/useAuth";
import { personName, useOrganizationMembers } from "@/hooks/useOrganizationMembers";
import { getErrorMessage } from "@/lib/errors";
import { emptyToNull, formatDate } from "@/lib/format";
import { createMeeting, listMeetings, updateMeeting } from "@/services/meetings";
import type { Meeting, MeetingType } from "@/types/api";

const STATUS_TONE = {
  DRAFT: "slate",
  SUBMITTED: "teal",
  REVIEWED: "green",
} as const;

const TYPE_LABEL: Record<MeetingType, string> = {
  CHECK_IN: "Check-in",
  ONE_ON_ONE: "One-on-one",
  PERFORMANCE_REVIEW: "Performance review",
};

export function MeetingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<MeetingType | "">("");
  const [memberId, setMemberId] = useState("");
  const [type, setType] = useState<MeetingType>("CHECK_IN");
  const [scheduledOn, setScheduledOn] = useState("");
  const [wins, setWins] = useState("");
  const [challenges, setChallenges] = useState("");
  const [nextSteps, setNextSteps] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [content, setContent] = useState<
    Record<string, { wins: string; challenges: string; next_steps: string }>
  >({});
  const [createError, setCreateError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  const filters = { page, page_size: 20, type: typeFilter };
  const query = useQuery({
    queryKey: ["meetings", filters],
    queryFn: () => listMeetings(filters),
  });
  const membersQuery = useOrganizationMembers();
  const people = membersQuery.data?.data;

  const createMutation = useMutation({
    mutationFn: createMeeting,
    onSuccess: async () => {
      setMemberId("");
      setScheduledOn("");
      setWins("");
      setChallenges("");
      setNextSteps("");
      setCreateError(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err) => setCreateError(getErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateMeeting>[1] }) =>
      updateMeeting(id, payload),
    onSuccess: async (_data, variables) => {
      setError(null);
      // Drop the local draft so the refetched server values become authoritative.
      setContent((current) => {
        const next = { ...current };
        delete next[variables.id];
        return next;
      });
      setSavedId(variables.id);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err) => {
      setSavedId(null);
      setError(getErrorMessage(err));
    },
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!memberId || !scheduledOn) {
      setCreateError("Member and date are required.");
      return;
    }
    createMutation.mutate({
      member_id: memberId,
      type,
      scheduled_on: scheduledOn,
      wins: emptyToNull(wins),
      challenges: emptyToNull(challenges),
      next_steps: emptyToNull(nextSteps),
    });
  }

  function fieldsFor(meeting: Meeting) {
    return (
      content[meeting.id] ?? {
        wins: meeting.wins ?? "",
        challenges: meeting.challenges ?? "",
        next_steps: meeting.next_steps ?? "",
      }
    );
  }

  return (
    <div>
      <PageHeader
        title="Meetings"
        description="Draft, submit, and review check-ins, one-on-ones, and performance reviews."
      />
      <Card className="mb-6">
        <Label htmlFor="meeting-type-filter">Show</Label>
        <Select
          id="meeting-type-filter"
          className="max-w-xs"
          value={typeFilter}
          onChange={(event) => {
            setPage(1);
            setTypeFilter(event.target.value as MeetingType | "");
          }}
        >
          <option value="">All meetings</option>
          <option value="CHECK_IN">Check-ins</option>
          <option value="ONE_ON_ONE">One-on-ones</option>
          <option value="PERFORMANCE_REVIEW">Performance reviews</option>
        </Select>
      </Card>
      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Create draft</h2>
        <p className="mb-3 text-xs text-slate-500">
          Owners and managers can create a meeting for someone else in the organization.
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
              <Label htmlFor="meeting-type">Type</Label>
              <Select
                id="meeting-type"
                value={type}
                onChange={(event) => setType(event.target.value as MeetingType)}
              >
                <option value="CHECK_IN">Check-in</option>
                <option value="ONE_ON_ONE">One-on-one</option>
                <option value="PERFORMANCE_REVIEW">Performance review</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="scheduled-on">Date</Label>
              <Input
                id="scheduled-on"
                type="date"
                value={scheduledOn}
                onChange={(event) => setScheduledOn(event.target.value)}
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
              Create meeting
            </Button>
          </div>
        </form>
        <FieldError message={createError} />
      </Card>

      {query.isLoading ? <LoadingState label="Loading meetings…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState title="No meetings" description="Create a draft to start the workflow." />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="space-y-4">
            {query.data.data.map((meeting) => {
              const fields = fieldsFor(meeting);
              const isMember = user?.id === meeting.member_id;
              const isManager = user?.id === meeting.manager_id;
              const isTarget = updateMutation.variables?.id === meeting.id;
              const isSaving = isTarget && updateMutation.isPending;
              return (
                <Card key={meeting.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {TYPE_LABEL[meeting.type]} · {formatDate(meeting.scheduled_on)}
                      </p>
                      <p className="text-xs text-slate-500">
                        {personName(people, meeting.member_id, "Member")} · Manager{" "}
                        {personName(people, meeting.manager_id, "unknown")}
                      </p>
                    </div>
                    <Badge tone={STATUS_TONE[meeting.status]}>{meeting.status}</Badge>
                  </div>
                  {meeting.status === "DRAFT" ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <div>
                        <Label htmlFor={`wins-${meeting.id}`}>Wins</Label>
                        <Textarea
                          id={`wins-${meeting.id}`}
                          rows={3}
                          value={fields.wins}
                          onChange={(event) =>
                            setContent({
                              ...content,
                              [meeting.id]: { ...fields, wins: event.target.value },
                            })
                          }
                        />
                      </div>
                      <div>
                        <Label htmlFor={`challenges-${meeting.id}`}>Challenges</Label>
                        <Textarea
                          id={`challenges-${meeting.id}`}
                          rows={3}
                          value={fields.challenges}
                          onChange={(event) =>
                            setContent({
                              ...content,
                              [meeting.id]: { ...fields, challenges: event.target.value },
                            })
                          }
                        />
                      </div>
                      <div>
                        <Label htmlFor={`next-steps-${meeting.id}`}>Next steps</Label>
                        <Textarea
                          id={`next-steps-${meeting.id}`}
                          rows={3}
                          value={fields.next_steps}
                          onChange={(event) =>
                            setContent({
                              ...content,
                              [meeting.id]: { ...fields, next_steps: event.target.value },
                            })
                          }
                        />
                      </div>
                    </div>
                  ) : (
                    <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                      <div>
                        <dt className="font-medium text-slate-700">Wins</dt>
                        <dd className="mt-1 text-slate-600">{meeting.wins || "—"}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-slate-700">Challenges</dt>
                        <dd className="mt-1 text-slate-600">{meeting.challenges || "—"}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-slate-700">Next steps</dt>
                        <dd className="mt-1 text-slate-600">{meeting.next_steps || "—"}</dd>
                      </div>
                    </dl>
                  )}
                  {meeting.manager_notes ? (
                    <p className="mt-3 text-sm text-slate-600">
                      <span className="font-medium text-slate-700">Manager notes: </span>
                      {meeting.manager_notes}
                    </p>
                  ) : null}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {meeting.status === "DRAFT" && (isMember || isManager) ? (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={isSaving}
                        onClick={() => {
                          setSavedId(null);
                          updateMutation.mutate({
                            id: meeting.id,
                            payload: {
                              wins: emptyToNull(fields.wins),
                              challenges: emptyToNull(fields.challenges),
                              next_steps: emptyToNull(fields.next_steps),
                            },
                          });
                        }}
                      >
                        {isSaving ? "Saving…" : "Save draft"}
                      </Button>
                    ) : null}
                    {meeting.status === "DRAFT" && isMember ? (
                      <Button
                        type="button"
                        disabled={isSaving}
                        onClick={() => {
                          setSavedId(null);
                          updateMutation.mutate({
                            id: meeting.id,
                            payload: {
                              wins: emptyToNull(fields.wins),
                              challenges: emptyToNull(fields.challenges),
                              next_steps: emptyToNull(fields.next_steps),
                              status: "SUBMITTED",
                            },
                          });
                        }}
                      >
                        Submit
                      </Button>
                    ) : null}
                    {meeting.status === "SUBMITTED" && isManager ? (
                      <>
                        <Textarea
                          className="min-w-[16rem] flex-1"
                          rows={2}
                          placeholder="Manager notes"
                          value={notes[meeting.id] ?? meeting.manager_notes ?? ""}
                          onChange={(event) =>
                            setNotes({ ...notes, [meeting.id]: event.target.value })
                          }
                        />
                        <Button
                          type="button"
                          disabled={isSaving}
                          onClick={() => {
                            setSavedId(null);
                            updateMutation.mutate({
                              id: meeting.id,
                              payload: {
                                manager_notes: emptyToNull(notes[meeting.id] ?? ""),
                                status: "REVIEWED",
                              },
                            });
                          }}
                        >
                          Mark reviewed
                        </Button>
                      </>
                    ) : null}
                  </div>
                  {isTarget && error ? <FieldError message={error} /> : null}
                  {savedId === meeting.id ? (
                    <p className="mt-2 text-sm text-teal-700" role="status">
                      Saved.
                    </p>
                  ) : null}
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
