import { Navigate, Outlet } from "react-router-dom";

import { LoadingState } from "@/components/states";
import { useAuth } from "@/hooks/useAuth";

export function ProtectedRoute() {
  const { token, user, isReady } = useAuth();

  if (!isReady) {
    return (
      <div className="p-8">
        <LoadingState label="Checking session…" />
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!user) {
    return (
      <div className="p-8">
        <LoadingState label="Loading account…" />
      </div>
    );
  }

  return <Outlet />;
}

export function GuestRoute() {
  const { token, isReady } = useAuth();

  if (!isReady) {
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  }

  if (token) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
