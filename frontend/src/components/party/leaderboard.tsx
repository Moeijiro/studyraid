"use client";

import clsx from "clsx";
import { Crown } from "lucide-react";
import { useState } from "react";
import { Avatar } from "@/components/game/bits";
import { Skeleton } from "@/components/ui/card";
import { Segmented } from "@/components/ui/field";
import { minutesLabel, num } from "@/lib/format";
import { useResource } from "@/lib/store";
import type { Leaderboard as Board } from "@/lib/types";

export function Leaderboard({ scope }: { scope: string }) {
  const [metric, setMetric] = useState<Board["metric"]>("xp");
  const { data } = useResource<Board>(`/api/leaderboards?scope=${scope}&metric=${metric}`);
  const fmt = (v: number) => (metric === "xp" ? `${num(v)} XP` : metric === "quests" ? `${v} quests` : minutesLabel(v));
  return (
    <div>
      <div className="px-5">
        <Segmented size="sm" label="Leaderboard metric" value={metric} onChange={setMetric} options={[{ value: "xp", label: "XP" }, { value: "quests", label: "Quests" }, { value: "focus", label: "Focus" }]} />
      </div>
      {data ? (
        <ol className="mt-3 px-3 pb-4">
          {data.rows.map((r) => (
            <li key={r.user_id} className={clsx("flex items-center gap-3 rounded-xl px-2 py-2", r.is_me && "bg-brand/[0.07]")}>
              <span className={clsx("num w-5 text-center text-sm font-semibold", r.rank === 1 ? "text-xp" : "text-faint")}>{r.rank === 1 ? <Crown className="mx-auto size-4" aria-label="1st" /> : r.rank}</span>
              <Avatar name={r.display_name} hue={r.avatar_hue} size={28} />
              <span className="min-w-0 flex-1 truncate text-sm font-medium">
                {r.display_name}
                {r.is_me ? <span className="ml-1.5 text-xs text-faint">you</span> : null}
              </span>
              <span className="num text-sm text-muted">{fmt(r.value)}</span>
            </li>
          ))}
        </ol>
      ) : (
        <div className="space-y-2 p-5">
          <Skeleton className="h-8" />
          <Skeleton className="h-8" />
          <Skeleton className="h-8" />
        </div>
      )}
      <p className="px-5 pb-4 text-[11px] text-faint">This week (Monday 00:00 UTC onwards). Anyone can hide themselves in Settings.</p>
    </div>
  );
}
