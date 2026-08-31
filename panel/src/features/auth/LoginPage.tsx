import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Button, FieldError, Input, Label } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { getErrorMessage } from "@/lib/errors";
import { login as loginRequest } from "@/services/auth";

const WEBSITE_URL = import.meta.env.VITE_WEBSITE_URL ?? "http://localhost:5173";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }
    setSubmitting(true);
    try {
      const token = await loginRequest(email.trim(), password);
      login(token.access_token);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Sign in</h1>
        <p className="mt-1 text-sm text-slate-600">Access your Teamos workspace.</p>
        {searchParams.get("registered") === "1" ? (
          <p className="mt-4 rounded-md bg-teal-50 px-3 py-2 text-sm text-teal-800">
            Account created. Sign in to continue.
          </p>
        ) : null}
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <FieldError message={error} />
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-600">
          Need an account?{" "}
          <a className="font-medium text-teal-700 hover:underline" href={`${WEBSITE_URL}/register`}>
            Register
          </a>
        </p>
      </div>
    </div>
  );
}
