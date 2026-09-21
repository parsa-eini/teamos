import { Button } from "@/components/ui";
import type { PaginationMeta } from "@/types/api";

export function Pagination({
  meta,
  onPageChange,
}: {
  meta: PaginationMeta;
  onPageChange: (page: number) => void;
}) {
  const pageCount = Math.max(1, Math.ceil(meta.total / meta.page_size));
  if (meta.total <= meta.page_size) {
    return null;
  }

  return (
    <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
      <p>
        Page {meta.page} of {pageCount} · {meta.total} total
      </p>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={meta.page <= 1}
          onClick={() => onPageChange(meta.page - 1)}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={meta.page >= pageCount}
          onClick={() => onPageChange(meta.page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
