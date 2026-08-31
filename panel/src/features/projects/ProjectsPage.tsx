import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Pagination } from "@/components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge, Button, PageHeader, Select } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { listProjects } from "@/services/projects";
import type { ProjectStatus } from "@/types/api";

const STATUS_TONE: Record<ProjectStatus, "slate" | "teal" | "green" | "amber"> = {
  PLANNED: "slate",
  ACTIVE: "teal",
  COMPLETED: "green",
  ARCHIVED: "amber",
};

export function ProjectsPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<ProjectStatus | "">("");

  const query = useQuery({
    queryKey: ["projects", page, status],
    queryFn: () => listProjects({ page, page_size: 20, status }),
  });

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Track planned, active, and completed work."
        actions={
          <Link to="/projects/new">
            <Button type="button">New project</Button>
          </Link>
        }
      />
      <div className="mb-4 max-w-xs">
        <Select
          aria-label="Filter by status"
          value={status}
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value as ProjectStatus | "");
          }}
        >
          <option value="">All statuses</option>
          <option value="PLANNED">Planned</option>
          <option value="ACTIVE">Active</option>
          <option value="COMPLETED">Completed</option>
          <option value="ARCHIVED">Archived</option>
        </Select>
      </div>
      {query.isLoading ? <LoadingState label="Loading projects…" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.data.data.length === 0 ? (
        <EmptyState
          title="No projects"
          description="Create a project to start assigning tasks."
          action={
            <Link to="/projects/new">
              <Button type="button">Create project</Button>
            </Link>
          }
        />
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Dates</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.data.map((project) => (
                  <tr key={project.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link
                        className="font-medium text-teal-800 hover:underline"
                        to={`/projects/${project.id}`}
                      >
                        {project.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={STATUS_TONE[project.status]}>{project.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatDate(project.start_date)} – {formatDate(project.end_date)}
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
