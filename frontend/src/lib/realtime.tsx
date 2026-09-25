"use client";

// One WebSocket per tab. It fetches a single-use ticket over REST, connects
// straight to the API, reconnects with backoff, and fans events out to listeners.
// Every event also invalidates the cached resources it affects.

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { post } from "./api";
import { invalidate } from "./store";
import type { RealtimeEvent } from "./types";

type Listener = (e: RealtimeEvent) => void;
type Value = { connected: boolean; subscribe: (fn: Listener) => () => void };

const RealtimeContext = createContext<Value | null>(null);

function socketUrl(ticket: string) {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? `${location.protocol === "https:" ? "wss" : "ws"}://${location.hostname}:8000/api/ws`;
  return `${base}?ticket=${encodeURIComponent(ticket)}`;
}

const INVALIDATES: Partial<Record<RealtimeEvent["type"], string[]>> = {
  xp: ["/api/me/summary", "/api/me/heatmap", "/api/analytics"],
  achievement: ["/api/me/achievements", "/api/me/summary"],
  notification: ["/api/notifications", "/api/me/summary"],
  challenge_progress: ["/api/parties", "/api/me/summary", "/api/leaderboards"],
  challenge_completed: ["/api/parties", "/api/me/summary"],
  party_activity: ["/api/parties", "/api/leaderboards"],
  party_invite: ["/api/parties"],
  party_member_joined: ["/api/parties"],
  party_member_left: ["/api/parties"],
  quest_completed: ["/api/quests"],
  focus_completed: ["/api/focus"],
};

export function RealtimeProvider({ enabled, children }: { enabled: boolean; children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const listeners = useRef(new Set<Listener>());

  useEffect(() => {
    if (!enabled) return;
    let socket: WebSocket | null = null;
    let stopped = false;
    let attempt = 0;
    let timer: number | undefined;

    const connect = async () => {
      try {
        const { ticket } = await post<{ ticket: string }>("/api/realtime/ticket");
        if (stopped) return;
        socket = new WebSocket(socketUrl(ticket));
        socket.onopen = () => {
          attempt = 0;
          setConnected(true);
        };
        socket.onmessage = (msg) => {
          const event = JSON.parse(msg.data) as RealtimeEvent;
          const keys = INVALIDATES[event.type];
          if (keys) invalidate(...keys);
          listeners.current.forEach((fn) => fn(event));
        };
        socket.onclose = () => {
          setConnected(false);
          if (!stopped) schedule();
        };
      } catch {
        schedule();
      }
    };
    const schedule = () => {
      attempt += 1;
      timer = window.setTimeout(connect, Math.min(30_000, 1000 * 2 ** Math.min(attempt, 5)));
    };
    void connect();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [enabled]);

  const subscribe = (fn: Listener) => {
    listeners.current.add(fn);
    return () => {
      listeners.current.delete(fn);
    };
  };

  return <RealtimeContext.Provider value={{ connected, subscribe }}>{children}</RealtimeContext.Provider>;
}

export function useRealtime(fn?: Listener) {
  const ctx = useContext(RealtimeContext);
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });
  useEffect(() => {
    if (!ctx || !ref.current) return;
    return ctx.subscribe((e) => ref.current?.(e));
  }, [ctx]);
  return ctx?.connected ?? false;
}
