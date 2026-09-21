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
  Label,
  PageHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { personName, useOrganizationMembers } from "@/hooks/useOrganizationMembers";
import { getErrorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { createFeedback, deleteFeedback, listFeedback } from "@/services/feedback";
import type { FeedbackSentiment } from "@/types/api";

const SENTIMENT_STYLE: Record<FeedbackSentiment, { border: string; tone: "green" | "red" }> = {
  POSITIVE: { border: "border-l-4 border-l-green-600", tone: "green" },
  NEGATIVE: { border: "border-l-4 border-l-red-600", tone: "red" },
};

export function FeedbackPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [sentimentFilter, setSentimentFilter] = useState<FeedbackSentiment | "">("");
  const [subjectId, setSubjectId] = useState("");
  const [sentiment, setSentiment] = useState<FeedbackSentiment>("POSITIVE");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const filters = { page, page_size: 20, sentiment: sentimentFilter };
  const query = useQuery({
    queryKey: ["feedback", filters],
    queryFn: () => listFeedback(filters),
  });
  const membersQuery = useOrganizationMembers();
  const people = membersQuery.data?.data;

  const createMutation = useMutation({
    mutationFn: createFeedback,
    onSuccess: async () => {
      setSubjectId("");
      setBody("");
      setSentiment("POSITIVE");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["feedback"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteFeedback,
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["feedback"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subjectId || !body.trim()) {
      setError("Pick a person and write a note.");
      return;
    }
    createMutation.mutate({ subject_id: subjectId, sentiment, body: body.trim() });
  }

  return (
    <div>
      <PageHeader
        title="Feedback"
        description="Notes about colleagues. People never see feedback written about them; their management line does."
      />
      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Write feedback</h2>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreate}>
          <MemberSelect
            id="feedback-subject"
            label="About"
            value={subjectId}
            onChange={setSubjectId}
            emptyLabel="Select a person"
            excludeIds={user ? [user.id] : []}
          />
          <div>
            <Label htmlFor="feedback-sentiment">Sentiment</Label>
            <Select
              id="feedback-sentiment"
              value={sentiment}
              onChange={(event) => setSentiment(event.target.value as FeedbackSentiment)}
            >
              <option value="POSITIVE">Positive</option>
              <option value="NEGATIVE">Negative</option>
            </Select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="feedback-body">Note</Label>
            <Textarea
              id="feedback-body"
              rows={3}
              value={body}
              onChange={(event) => setBody(event.target.value)}
            />
          </div>
          <div>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Saving…" : "Save feedback"}
            </Button>
          </div>
        </form>
        <FieldError message={error} />
      </Card>

      <Card className="mb-6">
        <Label htmlFor="feedback-filter">Show</Label>
        <Select
          id="feedback-filter"
          className="max-w-xs"
          value={sentimentFilter}
          onChange={(event) => {
            setPage(1);
            setSentimentFilter(event.target.value as FeedbackSentiment | "");
          }}
        >
          <option value="">All feedback</option>
          <option value="POSITIVE">Positive</option>
          <option value="NEGATIVE">Negative</option>
        </Select>
      </Card>

      {query.isLoading ? <LoadingState label="Loading feedback…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState
          title="No feedback"
          description="Feedback you write, and feedback about people who report to you, appears here."
        />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="space-y-4">
            {query.data.data.map((item) => {
              const style = SENTIMENT_STYLE[item.sentiment];
              return (
                <Card key={item.id} className={style.border}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        About {personName(people, item.subject_id)}
                      </p>
                      <p className="text-xs text-slate-500">
                        By {personName(people, item.author_id)} ·{" "}
                        {formatDateTime(item.created_at)}
                      </p>
                    </div>
                    <Badge tone={style.tone}>{item.sentiment}</Badge>
                  </div>
                  <p className="mt-3 whitespace-pre-line text-sm text-slate-700">{item.body}</p>
                  {item.author_id === user?.id ? (
                    <div className="mt-3">
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(item.id)}
                      >
                        Delete
                      </Button>
                    </div>
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
