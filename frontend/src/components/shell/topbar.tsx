"use client";

import Link from "next/link";
import { LogOut, Settings, Trophy } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Avatar, CoinCount, StreakBadge } from "@/components/game/bits";
import { LogoMark } from "@/components/game/logo";
import { useAuth } from "@/lib/auth";
import { useRealtime } from "@/lib/realtime";
import { useResource } from "@/lib/store";
import type { Summary } from "@/lib/types";
import { NotificationBell } from "./notifications";

export function Topbar() {
  const { data } = useResource<Summary>("/api/me/summary");
  const connected = useRealtime();
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/75 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1320px] items-center gap-3 px-4 sm:px-6 lg:px-8">
        <Link href="/dashboard" className="lg:hidden" aria-label="StudyRaid dashboard">
          <LogoMark />
        </Link>
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          {data ? (
            <div className="mr-1 flex items-center gap-3 rounded-xl border border-line bg-white/[0.02] px-3 py-1.5 text-sm sm:gap-4">
              <span title={`${data.streak.current}-day streak`}>
                <StreakBadge days={data.streak.current} active={data.streak.active_today} />
              </span>
              <span className="h-4 w-px bg-line-2" aria-hidden="true" />
              <span title="Coins">
                <CoinCount coins={data.coins} />
              </span>
            </div>
          ) : null}
          <span
            className={`hidden size-2 rounded-full sm:block ${connected ? "bg-ok shadow-[0_0_8px] shadow-ok/60" : "bg-faint"}`}
            title={connected ? "Live updates connected" : "Live updates reconnecting"}
            aria-label={connected ? "Live updates connected" : "Live updates offline"}
            role="status"
          />
          <NotificationBell />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  if (!user) return null;
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label="Account menu" className="rounded-full p-0.5 hover:ring-2 hover:ring-line-2">
        <Avatar name={user.display_name} hue={user.avatar_hue} size={34} />
      </button>
      {open ? (
        <div className="panel absolute top-12 right-0 z-50 w-56 p-1.5">
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium">{user.display_name}</p>
            <p className="truncate text-xs text-faint">@{user.username}</p>
          </div>
          <div className="my-1 h-px bg-line" />
          <Link href="/achievements" onClick={() => setOpen(false)} className="flex h-9 items-center gap-2.5 rounded-lg px-3 text-sm text-muted hover:bg-white/[0.05] hover:text-fg">
            <Trophy className="size-4" /> Achievements
          </Link>
          <Link href="/settings" onClick={() => setOpen(false)} className="flex h-9 items-center gap-2.5 rounded-lg px-3 text-sm text-muted hover:bg-white/[0.05] hover:text-fg">
            <Settings className="size-4" /> Settings
          </Link>
          <button
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
            className="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-sm text-muted hover:bg-white/[0.05] hover:text-fg"
          >
            <LogOut className="size-4" /> Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
