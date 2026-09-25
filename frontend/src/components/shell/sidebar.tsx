"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings } from "lucide-react";
import { LevelRing } from "@/components/game/xp-bar";
import { Logo } from "@/components/game/logo";
import { rankTitle } from "@/lib/game";
import { num } from "@/lib/format";
import { useResource } from "@/lib/store";
import type { Summary } from "@/lib/types";
import { NAV } from "./nav";

export function Sidebar() {
  const path = usePathname();
  const { data } = useResource<Summary>("/api/me/summary");
  return (
    <aside className="sticky top-0 hidden h-dvh w-[248px] shrink-0 flex-col border-r border-line bg-bg-2/70 px-4 py-5 backdrop-blur lg:flex">
      <Link href="/dashboard" className="px-2" aria-label="StudyRaid dashboard">
        <Logo />
      </Link>
      <nav aria-label="Main" className="mt-8 flex flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={clsx(
                "group relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
                active ? "bg-white/[0.06] text-fg" : "text-muted hover:bg-white/[0.035] hover:text-fg",
              )}
            >
              {active ? <span className="absolute top-2 bottom-2 -left-4 w-[3px] rounded-r-full bg-brand" aria-hidden="true" /> : null}
              <Icon className={clsx("size-[18px]", active ? "text-brand" : "text-faint group-hover:text-muted")} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        {data ? (
          <Link href="/dashboard" className="panel panel-hover flex items-center gap-3 p-3">
            <LevelRing level={data.level.level} progress={data.level.progress} size={48} stroke={4} />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{data.user.display_name}</p>
              <p className="text-xs text-muted">{rankTitle(data.level.level)}</p>
              <p className="num mt-0.5 text-[11px] text-faint">
                {num(data.level.xp_for_level - data.level.xp_into_level)} XP to next
              </p>
            </div>
          </Link>
        ) : null}
        <Link
          href="/settings"
          aria-current={path === "/settings" ? "page" : undefined}
          className="flex h-10 items-center gap-3 rounded-xl px-3 text-sm text-muted hover:bg-white/[0.035] hover:text-fg aria-[current=page]:text-fg"
        >
          <Settings className="size-[18px] text-faint" /> Settings
        </Link>
      </div>
    </aside>
  );
}
