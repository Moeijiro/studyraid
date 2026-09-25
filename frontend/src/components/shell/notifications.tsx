"use client";

import clsx from "clsx";
import { AnimatePresence, motion } from "motion/react";
import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { post } from "@/lib/api";
import { relative } from "@/lib/format";
import { useRealtime } from "@/lib/realtime";
import { invalidate, useResource } from "@/lib/store";
import type { Notification } from "@/lib/types";
import { useToasts } from "@/components/game/toasts";

// Kinds already celebrated by the action that caused them (quest completion toasts).
const SILENT = new Set(["achievement", "level_up"]);

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { data } = useResource<{ items: Notification[]; unread: number }>("/api/notifications");
  const { push } = useToasts();
  const wrap = useRef<HTMLDivElement>(null);

  useRealtime((e) => {
    if (e.type === "notification" && !SILENT.has(e.notification.kind)) push({ kind: "info", title: e.notification.title, body: e.notification.body });
  });

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !wrap.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const unread = data?.unread ?? 0;
  const markAll = async () => {
    await post("/api/notifications/read-all");
    invalidate("/api/notifications", "/api/me/summary");
  };
  const markOne = async (n: Notification) => {
    if (!n.read) {
      await post(`/api/notifications/${n.id}/read`);
      invalidate("/api/notifications");
    }
    setOpen(false);
  };

  return (
    <div ref={wrap} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
        className="relative inline-flex size-10 items-center justify-center rounded-xl text-muted transition-colors hover:bg-white/[0.06] hover:text-fg"
      >
        <Bell className="size-[19px]" />
        {unread ? (
          <span className="num absolute top-1.5 right-1.5 flex min-w-4 items-center justify-center rounded-full bg-brand px-1 text-[10px] leading-4 font-bold text-brand-ink">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </button>
      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.16 }}
            className="panel fixed inset-x-3 top-16 z-50 max-h-[70dvh] overflow-hidden sm:absolute sm:inset-x-auto sm:top-12 sm:right-0 sm:w-96"
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <p className="font-display font-semibold">Notifications</p>
              <button onClick={markAll} disabled={!unread} className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-fg disabled:opacity-40">
                <CheckCheck className="size-3.5" /> Mark all read
              </button>
            </div>
            <ul className="max-h-[calc(70dvh-52px)] overflow-y-auto">
              {data?.items.length ? (
                data.items.map((n) => (
                  <li key={n.id}>
                    <Link href={n.link ?? "/dashboard"} onClick={() => markOne(n)} className={clsx("flex gap-3 border-b border-line/60 px-4 py-3 transition-colors hover:bg-white/[0.03]", !n.read && "bg-brand/[0.04]")}>
                      <span className={clsx("mt-1.5 size-2 shrink-0 rounded-full", n.read ? "bg-transparent" : "bg-brand")} aria-hidden="true" />
                      <span className="min-w-0">
                        <span className={clsx("block text-sm", n.read ? "text-muted" : "font-medium text-fg")}>{n.title}</span>
                        {n.body ? <span className="mt-0.5 block truncate text-xs text-faint">{n.body}</span> : null}
                        <span className="mt-1 block text-[11px] text-faint">{relative(n.created_at)}</span>
                      </span>
                    </Link>
                  </li>
                ))
              ) : (
                <li className="px-4 py-10 text-center text-sm text-muted">You&apos;re all caught up.</li>
              )}
            </ul>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
