import type { ReactNode } from "react";

import { Button } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
      {label}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6">
      <p className="text-sm font-medium text-red-800">{getErrorMessage(error)}</p>
      {onRetry ? (
        <Button variant="secondary" className="mt-3" onClick={onRetry} type="button">
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="text-sm font-medium text-slate-900">{title}</p>
      {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
