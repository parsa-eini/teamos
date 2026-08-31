import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge, Card, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/errors";
import { formatDate, formatDateTime } from "@/lib/format";
import { getDashboard } from "@/services/dashboard";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <p className="text-sm text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
    </Card>
  );
}

export function DashboardPage() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });

  if (query.isLoading) {
    return <LoadingState label="Loading dashboard…" />;
  }
  if (query.isError) {
    const forbidden = query.error instanceof ApiError && query.error.status === 403;
    return (
      <>
        <PageHeader title="Dashboard" description="Team overview for the current organization." />
        <ErrorState
          error={
            forbidden
              ? "You do not have permission to view the manager dashboard."
              : query.error
          }
          onRetry={forbidden ? undefined : () => void query.refetch()}
        />
      </>
    );
  }

  const dashboard = query.data;
  if (!dashboard) {
    return <EmptyState title="Dashboard is not available." />;
  }

  return (
    <div>
      <PageHeader title="Team overview" description="Status across people, work, and goals." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Members" value={dashboard.member_count} />
        <Stat label="Active projects" value={dashboard.active_projects} />
        <Stat label="Open tasks" value={dashboard.open_tasks} />
        <Stat label="Overdue tasks" value={dashboard.overdue_tasks} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Goals</h2>
            <Link to="/goals" className="text-sm text-teal-700 hover:underline">
              View all
            </Link>
          </div>
          {dashboard.goal_summary.items.length === 0 ? (
            <EmptyState title="No goals yet" description="Create a goal to track progress." />
          ) : (
            <ul className="space-y-4">
              {dashboard.goal_summary.items.map((goal) => (
                <li key={goal.id}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-slate-900">{goal.title}</span>
                    <span className="text-slate-600">{goal.progress}%</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-teal-700"
                      style={{ width: `${goal.progress}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-4 text-sm font-semibold text-slate-900">Recent check-ins</h2>
          {dashboard.recent_checkins.length === 0 ? (
            <EmptyState title="No recent check-ins" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {dashboard.recent_checkins.map((checkin) => (
                <li key={checkin.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="text-slate-900">
                      {formatDate(checkin.period_start)} – {formatDate(checkin.period_end)}
                    </p>
                    <p className="text-xs text-slate-500">Updated {formatDateTime(checkin.updated_at)}</p>
                  </div>
                  <Badge tone={checkin.status === "REVIEWED" ? "green" : checkin.status === "SUBMITTED" ? "teal" : "slate"}>
                    {checkin.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-900">Recent activity</h2>
        {dashboard.recent_activity.length === 0 ? (
          <EmptyState title="No recent activity" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {dashboard.recent_activity.map((item, index) => (
              <li key={`${item.type}-${item.occurred_at}-${index}`} className="py-3 text-sm">
                <p className="text-slate-900">{item.message}</p>
                <p className="text-xs text-slate-500">{formatDateTime(item.occurred_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
