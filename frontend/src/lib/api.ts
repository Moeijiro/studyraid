// Fetch wrapper. The access token lives in memory only; on a 401 the client
// asks /api/auth/refresh (HttpOnly cookie) for a new one and retries once.

import type { TokenResponse } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

let accessToken: string | null = null;
let refreshing: Promise<TokenResponse | null> | null = null;
const listeners = new Set<(t: TokenResponse | null) => void>();

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function onSessionChange(fn: (t: TokenResponse | null) => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

const CLIENT = { "X-StudyRaid-Client": "web" };

async function parse(res: Response): Promise<never> {
  let body: { error?: { code?: string; message?: string; details?: unknown } } = {};
  try {
    body = await res.json();
  } catch {
    /* non-JSON error */
  }
  throw new ApiError(res.status, body.error?.code ?? "http_error", body.error?.message ?? `Request failed (${res.status})`, body.error?.details);
}

/** Single-flight refresh: concurrent 401s share one refresh request. */
export function refreshSession(): Promise<TokenResponse | null> {
  if (!refreshing) {
    refreshing = fetch("/api/auth/refresh", { method: "POST", headers: CLIENT, credentials: "same-origin" })
      .then(async (res) => (res.status === 200 ? ((await res.json()) as TokenResponse) : null))
      .catch(() => null)
      .then((t) => {
        accessToken = t?.access_token ?? null;
        listeners.forEach((fn) => fn(t));
        return t;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

type Options = { method?: string; body?: unknown; params?: Record<string, string | number | boolean | string[] | undefined>; signal?: AbortSignal };

export async function api<T>(path: string, opts: Options = {}, retry = true): Promise<T> {
  const url = new URL(path, window.location.origin);
  for (const [k, v] of Object.entries(opts.params ?? {})) {
    if (v === undefined) continue;
    if (Array.isArray(v)) v.forEach((item) => url.searchParams.append(k, item));
    else url.searchParams.set(k, String(v));
  }
  const headers: Record<string, string> = { ...CLIENT };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    credentials: "same-origin",
    signal: opts.signal,
  });
  if (res.status === 401 && retry && !path.startsWith("/api/auth/")) {
    const t = await refreshSession();
    if (t) return api<T>(path, opts, false);
  }
  if (!res.ok) return parse(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const post = <T>(path: string, body?: unknown) => api<T>(path, { method: "POST", body });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });
