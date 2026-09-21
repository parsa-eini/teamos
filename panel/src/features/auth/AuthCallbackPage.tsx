import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingState } from "@/components/states";
import { useAuth } from "@/hooks/useAuth";

export function AuthCallbackPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, "");
    const params = new URLSearchParams(hash);
    const token = params.get("access_token");
    if (token) {
      login(token);
      window.history.replaceState(null, "", "/dashboard");
      navigate("/dashboard", { replace: true });
      return;
    }
    navigate("/login", { replace: true });
  }, [login, navigate]);

  return (
    <div className="p-8">
      <LoadingState label="Signing you in…" />
    </div>
  );
}
