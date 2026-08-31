import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Button, Card, FieldError, Input, Label, PageHeader } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { getCurrentOrganization, updateCurrentOrganization } from "@/services/organizations";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  const query = useQuery({
    queryKey: ["organizations", "current"],
    queryFn: getCurrentOrganization,
  });

  useEffect(() => {
    if (query.data && !hydrated) {
      setName(query.data.name);
      setSlug(query.data.slug);
      setHydrated(true);
    }
  }, [hydrated, query.data]);

  const mutation = useMutation({
    mutationFn: () => updateCurrentOrganization({ name: name.trim(), slug: slug.trim() }),
    onSuccess: async () => {
      setError(null);
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
    onError: (err) => {
      setSaved(false);
      setError(getErrorMessage(err));
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !slug.trim()) {
      setError("Name and slug are required.");
      return;
    }
    mutation.mutate();
  }

  if (query.isLoading) {
    return <LoadingState label="Loading settings…" />;
  }
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (!query.data) {
    return <EmptyState title="Organization not found" />;
  }

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Update the current organization. Only the owner can save changes."
      />
      <Card className="max-w-xl">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <Label htmlFor="org-name">Name</Label>
            <Input id="org-name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div>
            <Label htmlFor="org-slug">Slug</Label>
            <Input id="org-slug" value={slug} onChange={(event) => setSlug(event.target.value)} />
            <p className="mt-1 text-xs text-slate-500">Lowercase letters, numbers, and hyphens.</p>
          </div>
          <FieldError message={error} />
          {saved ? <p className="text-sm text-teal-800">Organization updated.</p> : null}
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Save"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
