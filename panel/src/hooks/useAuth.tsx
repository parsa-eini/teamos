import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/auth";
import { getCurrentUser } from "@/services/auth";
import type { User } from "@/types/api";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  isReady: boolean;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(() => getAccessToken());

  const userQuery = useQuery({
    queryKey: ["users", "me"],
    queryFn: getCurrentUser,
    enabled: Boolean(token),
  });

  const login = useCallback(
    (nextToken: string) => {
      setAccessToken(nextToken);
      setToken(nextToken);
      void queryClient.invalidateQueries({ queryKey: ["users", "me"] });
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    clearAccessToken();
    setToken(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    if (userQuery.isError) {
      logout();
    }
  }, [logout, userQuery.isError]);

  const value = useMemo(
    () => ({
      token,
      user: userQuery.data ?? null,
      isReady: !token || userQuery.isFetched || userQuery.isError,
      login,
      logout,
    }),
    [login, logout, token, userQuery.data, userQuery.isError, userQuery.isFetched],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
