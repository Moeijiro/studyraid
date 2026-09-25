// A tiny data layer: cached GETs keyed by path, invalidated by mutations and by
// realtime events. Enough for this app without pulling in a query library.

"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api, ApiError } from "./api";

type Entry = { data?: unknown; error?: ApiError; loading: boolean; stamp: number };

const cache = new Map<string, Entry>();
const subs = new Map<string, Set<() => void>>();
const inflight = new Map<string, Promise<void>>();

function notify(key: string) {
  subs.get(key)?.forEach((fn) => fn());
}

function set(key: string, entry: Entry) {
  cache.set(key, entry);
  notify(key);
}

async function load(key: string) {
  if (inflight.has(key)) return inflight.get(key);
  const prev = cache.get(key);
  set(key, { ...(prev ?? { stamp: 0 }), loading: true });
  const p = api<unknown>(key)
    .then((data) => set(key, { data, loading: false, stamp: Date.now() }))
    .catch((error: ApiError) => set(key, { ...(cache.get(key) ?? { stamp: 0 }), error, loading: false }))
    .finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

/** Refetch every cached key that starts with one of the prefixes. */
export function invalidate(...prefixes: string[]) {
  for (const key of cache.keys()) {
    if (prefixes.some((p) => key.startsWith(p))) void load(key);
  }
}

export function clearCache() {
  cache.clear();
}

export function useResource<T>(key: string | null) {
  const subscribe = useCallback(
    (fn: () => void) => {
      if (!key) return () => {};
      if (!subs.has(key)) subs.set(key, new Set());
      subs.get(key)!.add(fn);
      return () => subs.get(key)?.delete(fn);
    },
    [key],
  );
  const entry = useSyncExternalStore(
    subscribe,
    () => (key ? cache.get(key) : undefined),
    () => undefined,
  );
  useEffect(() => {
    if (key && (!cache.get(key) || Date.now() - (cache.get(key)?.stamp ?? 0) > 15_000)) void load(key);
  }, [key]);
  const reload = useCallback(() => (key ? load(key) : Promise.resolve()), [key]);
  return {
    data: entry?.data as T | undefined,
    error: entry?.error,
    loading: !entry || (entry.loading && entry.data === undefined),
    /** When the data was received (ms since epoch), e.g. to measure server clock offset. */
    stamp: entry?.stamp ?? 0,
    reload,
  };
}

/** Wraps a mutation with pending/error state. */
export function useAction<A extends unknown[], R>(fn: (...args: A) => Promise<R>) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });
  const run = useCallback(async (...args: A): Promise<R | undefined> => {
    setPending(true);
    setError(null);
    try {
      return await ref.current(...args);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "network", "Network error. Is the API running?"));
      return undefined;
    } finally {
      setPending(false);
    }
  }, []);
  return { run, pending, error, setError };
}
