import { Link } from "react-router-dom";

import { SiteFooter, SiteHeader } from "@/components/layout";

const FEATURES = [
  {
    title: "Teams",
    body: "Group people into teams and keep membership inside the organization.",
  },
  {
    title: "Projects and tasks",
    body: "Plan work, assign tasks, and filter by status, priority, and owner.",
  },
  {
    title: "Goals",
    body: "Track progress from 0 to 100 without a heavy OKR process.",
  },
  {
    title: "Check-ins",
    body: "Run a simple draft, submit, and review loop between managers and members.",
  },
  {
    title: "Manager dashboard",
    body: "See members, open work, overdue tasks, goals, and recent activity in one place.",
  },
];

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex-1">
        <section className="bg-slate-900 text-white">
          <div className="mx-auto max-w-6xl px-4 py-20">
            <p className="text-sm font-medium uppercase tracking-wide text-teal-300">
              Team visibility
            </p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
              Know what the team committed to, what moved, and where attention is needed.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-slate-300">
              Teamos is a lightweight workspace for engineering managers: organizations, teams,
              projects, tasks, goals, check-ins, and a manager dashboard.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/register"
                className="rounded-md bg-teal-500 px-4 py-2.5 text-sm font-medium text-slate-950 hover:bg-teal-400"
              >
                Create an account
              </Link>
              <Link
                to="/features"
                className="rounded-md border border-slate-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
              >
                See features
              </Link>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold text-slate-900">The problem</h2>
          <p className="mt-3 max-w-3xl text-slate-600">
            Managers often stitch together chat, spreadsheets, and issue trackers to answer basic
            questions: who is on the team, what is in flight, which goals are stalled, and who
            needs a check-in. That context is scattered, so attention arrives late.
          </p>
        </section>

        <section className="bg-slate-50">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <h2 className="text-2xl font-semibold text-slate-900">The solution</h2>
            <p className="mt-3 max-w-3xl text-slate-600">
              One organization-scoped product for the weekly management loop. Create an account,
              set up a team, assign work, record goals and check-ins, and open the dashboard.
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold text-slate-900">Features</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="rounded-lg border border-slate-200 p-5">
                <h3 className="font-medium text-slate-900">{feature.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{feature.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-teal-800 text-white">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <h2 className="text-2xl font-semibold">Start with your team this week</h2>
            <p className="mt-3 max-w-2xl text-teal-50">
              Register, create an organization, and open the panel. No integrations required for
              the MVP.
            </p>
            <Link
              to="/register"
              className="mt-6 inline-flex rounded-md bg-white px-4 py-2.5 text-sm font-medium text-teal-900 hover:bg-teal-50"
            >
              Get started
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
