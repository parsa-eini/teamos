import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { SiteFooter, SiteHeader } from "@/components/layout";
import { redirectToPanel } from "@/lib/api";
import { getErrorMessage } from "@/lib/errors";
import { login, registerAccount } from "@/services/auth";

export function RegisterPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (
      !firstName.trim() ||
      !lastName.trim() ||
      !email.trim() ||
      password.length < 8 ||
      !organizationName.trim()
    ) {
      setError("All fields are required. Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    try {
      await registerAccount({
        email: email.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        organization_name: organizationName.trim(),
      });
      const token = await login(email.trim(), password);
      redirectToPanel(token);
    } catch (err) {
      setError(getErrorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex flex-1 items-center justify-center bg-slate-50 px-4 py-12">
        <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">Create an account</h1>
          <p className="mt-1 text-sm text-slate-600">
            Registration creates your user and initial organization. You become the owner.
          </p>
          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="first-name" className="mb-1 block text-sm font-medium text-slate-700">
                  First name
                </label>
                <input
                  id="first-name"
                  className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="last-name" className="mb-1 block text-sm font-medium text-slate-700">
                  Last name
                </label>
                <input
                  id="last-name"
                  className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                />
              </div>
            </div>
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="organization"
                className="mb-1 block text-sm font-medium text-slate-700"
              >
                Organization name
              </label>
              <input
                id="organization"
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={organizationName}
                onChange={(event) => setOrganizationName(event.target.value)}
              />
            </div>
            {error ? <p className="text-sm text-red-700">{error}</p> : null}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
            >
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-600">
            Already registered?{" "}
            <Link to="/login" className="font-medium text-teal-700 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
