"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, onSessionChange, post, refreshSession, setAccessToken } from "./api";
import { clearCache } from "./store";
import type { TokenResponse, User } from "./types";

type Status = "loading" | "authenticated" | "anonymous";

type AuthValue = {
  status: Status;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; username: string; display_name: string; password: string; timezone: string }) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);

  const accept = useCallback((t: TokenResponse | null) => {
    setAccessToken(t?.access_token ?? null);
    setUser(t?.user ?? null);
    setStatus(t ? "authenticated" : "anonymous");
  }, []);

  // Restore the session from the refresh cookie, then refresh the access token
  // shortly before it expires.
  useEffect(() => {
    const off = onSessionChange((t) => {
      setUser(t?.user ?? null);
      setStatus(t ? "authenticated" : "anonymous");
    });
    void refreshSession();
    return () => {
      off();
    };
  }, []);

  useEffect(() => {
    if (status !== "authenticated") return;
    const timer = window.setInterval(() => void refreshSession(), 12 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  const login = useCallback(
    async (email: string, password: string) => {
      accept(await post<TokenResponse>("/api/auth/login", { email, password }));
    },
    [accept],
  );

  const register = useCallback<AuthValue["register"]>(
    async (data) => {
      accept(await post<TokenResponse>("/api/auth/register", data));
    },
    [accept],
  );

  const logout = useCallback(async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      clearCache();
      accept(null);
    }
  }, [accept]);

  const value = useMemo(() => ({ status, user, login, register, logout, setUser }), [status, user, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
