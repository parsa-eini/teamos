import { Link } from "react-router-dom";

import { SiteFooter, SiteHeader } from "@/components/layout";

export function FeaturesPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-semibold text-slate-900">Features</h1>
        <p className="mt-3 text-slate-600">
          Phase 1 covers the weekly management loop. Authenticated work happens in the panel, not
          on this site.
        </p>
        <ul className="mt-8 list-disc space-y-3 pl-5 text-slate-700">
          <li>Email and password accounts, with an organization created at registration</li>
          <li>Teams and team membership inside the organization</li>
          <li>Projects, tasks, assignment, and status tracking</li>
          <li>Goals with 0–100 progress</li>
          <li>Check-ins with draft, submitted, and reviewed states</li>
          <li>A manager dashboard with cached organization aggregates</li>
        </ul>
        <Link to="/register" className="mt-8 inline-block font-medium text-teal-700 hover:underline">
          Create an account
        </Link>
      </main>
      <SiteFooter />
    </div>
  );
}

export function PricingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-semibold text-slate-900">Pricing</h1>
        <p className="mt-3 text-slate-600">
          Billing and subscriptions are not part of Phase 1. You can register and use the MVP
          without a paid plan.
        </p>
        <Link to="/register" className="mt-8 inline-block font-medium text-teal-700 hover:underline">
          Get started
        </Link>
      </main>
      <SiteFooter />
    </div>
  );
}

export function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-semibold text-slate-900">About</h1>
        <p className="mt-3 text-slate-600">
          Teamos is a team-management product for engineering managers and team leads. It is not
          intended to replace Jira, Linear, or a full HR platform. The MVP is a single place to
          understand what the team is working on, what they committed to, and where attention is
          needed.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
