"use client";

import clsx from "clsx";
import { Medal } from "@/components/game/bits";
import { ProgressBar } from "@/components/game/xp-bar";
import { ErrorNote, Skeleton } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { TIER } from "@/lib/game";
import { num, relative } from "@/lib/format";
import { useResource } from "@/lib/store";
import type { Achievement } from "@/lib/types";

export default function AchievementsPage() {
  const { data, error, reload } = useResource<Achievement[]>("/api/me/achievements");
  const unlocked = data?.filter((a) => a.unlocked_at) ?? [];
  const locked = (data?.filter((a) => !a.unlocked_at) ?? []).sort((a, b) => b.progress / b.target - a.progress / a.target);
  return (
    <div>
      <title>Achievements · StudyRaid</title>
      <PageHeader title="Achievements" subtitle={data ? `${unlocked.length} of ${data.length} unlocked. Each one is earned from your real activity and pays bonus XP.` : undefined} />
      {error ? <ErrorNote message={error.message} onRetry={reload} /> : null}
      {!data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-28 rounded-[1.125rem]" />
          ))}
        </div>
      ) : (
        <div className="space-y-10">
          <Section title="Unlocked" items={unlocked.sort((a, b) => (b.unlocked_at ?? "").localeCompare(a.unlocked_at ?? ""))} />
          <Section title="In progress" items={locked} />
        </div>
      )}
    </div>
  );
}

function Section({ title, items }: { title: string; items: Achievement[] }) {
  if (!items.length) return null;
  return (
    <section aria-labelledby={`ach-${title}`}>
      <h2 id={`ach-${title}`} className="mb-3 text-[13px] font-semibold tracking-wide text-muted uppercase">
        {title} <span className="text-faint">· {items.length}</span>
      </h2>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((a) => {
          const done = !!a.unlocked_at;
          return (
            <li key={a.code} className={clsx("panel flex gap-4 p-4", done && "border-white/10")}>
              <Medal icon={a.icon} tier={a.tier} locked={!done} size={52} />
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-display font-semibold">{a.name}</p>
                  <span className="shrink-0 text-[10px] font-semibold tracking-wider uppercase" style={{ color: TIER[a.tier].color }}>
                    {TIER[a.tier].label}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted">{a.description}</p>
                {done ? (
                  <p className="mt-2 text-[11px] text-faint">
                    Unlocked {relative(a.unlocked_at!)} · <span className="text-xp">+{a.xp} XP</span>
                  </p>
                ) : (
                  <div className="mt-2.5">
                    <ProgressBar value={a.progress} max={a.target} height={6} label={`${a.name} progress`} />
                    <p className="num mt-1 text-[11px] text-faint">
                      {num(a.progress)} / {num(a.target)} · +{a.xp} XP
                    </p>
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
