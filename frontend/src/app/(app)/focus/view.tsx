"use client";

import clsx from "clsx";
import { AnimatePresence } from "motion/react";
import { Hourglass, Play, Timer } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Bars } from "@/components/analytics/charts";
import { SessionScreen } from "@/components/focus/session-screen";
import { useRewardFeedback, useToasts } from "@/components/game/toasts";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, EmptyState, Skeleton } from "@/components/ui/card";
import { Field, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError, post } from "@/lib/api";
import { minutesLabel, monthDay, num, plural, relative } from "@/lib/format";
import { invalidate, useResource } from "@/lib/store";
import type { Analytics, Completion, FocusSession, FocusSummary, Quest } from "@/lib/types";

type Overview = { active: FocusSession | null; summary: FocusSummary; history: FocusSession[]; server_time: string };
type FocusCompletion = Omit<Completion, "quest" | "level_before"> & { session: FocusSession };

const PRESETS = [
  { minutes: 25, label: "Pomodoro" },
  { minutes: 50, label: "Deep work" },
  { minutes: 90, label: "Marathon" },
];

export function FocusView() {
  const params = useSearchParams();
  const { data, reload, stamp } = useResource<Overview>("/api/focus");
  const { data: open } = useResource<{ items: Quest[] }>("/api/quests?status=planned&status=active&limit=100");
  const { data: stats } = useResource<Analytics>("/api/analytics/overview?days=14");
  const reward = useRewardFeedback();
  const { push } = useToasts();

  const [minutes, setMinutes] = useState(25);
  const [custom, setCustom] = useState(false);
  const [questId, setQuestId] = useState<string>(params.get("quest") ?? "");
  const [busy, setBusy] = useState(false);
  const [hidden, setHidden] = useState(false);
  // Server clock minus local clock, measured when the overview arrived.
  const offset = data?.server_time && stamp ? new Date(data.server_time).getTime() - stamp : 0;

  const active = data?.active ?? null;
  const questsById = useMemo(() => new Map((open?.items ?? []).map((q) => [q.id, q])), [open]);

  const refresh = () => {
    invalidate("/api/focus", "/api/me/summary", "/api/analytics", "/api/me/heatmap", "/api/parties", "/api/me/achievements");
    return reload();
  };

  const start = async () => {
    setBusy(true);
    try {
      await post<FocusSession>("/api/focus/sessions", { planned_minutes: minutes, quest_id: questId ? Number(questId) : null });
      setHidden(false);
      await refresh();
    } catch (e) {
      push({ kind: "error", title: e instanceof ApiError ? e.message : "Couldn't start the session." });
    } finally {
      setBusy(false);
    }
  };

  const complete = async () => {
    if (!active) return;
    setBusy(true);
    try {
      const r = await post<FocusCompletion>(`/api/focus/sessions/${active.id}/complete`);
      reward(r, `${r.session.actual_minutes}-minute focus session`);
      await refresh();
    } catch (e) {
      push({ kind: "error", title: e instanceof ApiError ? e.message : "Couldn't finish the session." });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!active) return;
    setBusy(true);
    try {
      await post(`/api/focus/sessions/${active.id}/cancel`);
      push({ kind: "info", title: "Session ended early", body: "Nothing was logged." });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const s = data?.summary;
  return (
    <div>
      <title>Focus · StudyRaid</title>
      <PageHeader title="Focus mode" subtitle="Pick a length, pick a quest, and put the phone face down. Finished sessions earn ½ XP per minute (up to 4 hours a day)." />

      <div className="grid gap-5 lg:grid-cols-12">
        <Card className="p-5 sm:p-7 lg:col-span-7">
          {active ? (
            <div className="flex flex-col items-center py-10 text-center">
              <span className="flex size-14 items-center justify-center rounded-2xl bg-brand/15 text-brand glow-brand">
                <Hourglass className="size-6" />
              </span>
              <p className="font-display mt-5 text-xl font-semibold">A session is running</p>
              <p className="mt-1 text-sm text-muted">
                {active.planned_minutes} minutes · started {relative(active.started_at)}
              </p>
              <Button className="mt-6" size="lg" onClick={() => setHidden(false)}>
                Return to session
              </Button>
            </div>
          ) : (
            <>
              <p className="text-[13px] font-semibold tracking-wide text-muted uppercase">Session length</p>
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {PRESETS.map((p) => (
                  <button
                    key={p.minutes}
                    onClick={() => (setMinutes(p.minutes), setCustom(false))}
                    aria-pressed={!custom && minutes === p.minutes}
                    className={clsx(
                      "rounded-2xl border p-4 text-left transition-colors",
                      !custom && minutes === p.minutes ? "border-brand/60 bg-brand/10" : "border-line bg-white/[0.02] hover:border-line-2",
                    )}
                  >
                    <p className="font-display num text-2xl font-bold">{p.minutes}</p>
                    <p className="text-xs text-muted">{p.label}</p>
                  </button>
                ))}
                <button
                  onClick={() => setCustom(true)}
                  aria-pressed={custom}
                  className={clsx("rounded-2xl border p-4 text-left transition-colors", custom ? "border-brand/60 bg-brand/10" : "border-line bg-white/[0.02] hover:border-line-2")}
                >
                  <p className="font-display num text-2xl font-bold">{custom ? minutes : "···"}</p>
                  <p className="text-xs text-muted">Custom</p>
                </button>
              </div>
              {custom ? (
                <div className="mt-4">
                  <label htmlFor="custom-min" className="text-xs text-muted">
                    {minutes} minutes
                  </label>
                  <input id="custom-min" type="range" min={5} max={180} step={5} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="mt-2 w-full accent-[#8f7cff]" />
                </div>
              ) : null}

              <div className="mt-6">
                <Field label="Working on" htmlFor="focus-quest" hint="Optional. Focus time is counted toward that quest's subject in analytics.">
                  <Select id="focus-quest" value={questId} onChange={(e) => setQuestId(e.target.value)}>
                    <option value="">No specific quest</option>
                    {(open?.items ?? []).map((q) => (
                      <option key={q.id} value={q.id}>
                        {q.subject} · {q.title}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>

              <div className="mt-7 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                <Button size="lg" onClick={start} loading={busy}>
                  <Play className="size-4" /> Start {minutes}-minute session
                </Button>
                <p className="text-xs text-faint">Worth {minutes >= 10 ? `+${Math.floor(minutes / 2)} XP` : "no XP (under 10 min)"}</p>
              </div>
            </>
          )}
        </Card>

        <div className="grid gap-5 sm:grid-cols-3 lg:col-span-5 lg:grid-cols-1">
          {s ? (
            <>
              <StatCard label="Today" value={minutesLabel(s.today_minutes)} note={plural(s.today_sessions, "session")} />
              <StatCard label="This week" value={minutesLabel(s.week_minutes)} note={plural(s.week_sessions, "session")} />
              <StatCard label="All time" value={`${num(Math.round(s.total_minutes / 60))}h`} note={plural(s.total_sessions, "session")} />
            </>
          ) : (
            <Skeleton className="h-64 rounded-[1.125rem] sm:col-span-3 lg:col-span-1" />
          )}
        </div>

        <Card className="lg:col-span-7">
          <CardHeader title="Focus minutes" subtitle="Last 14 days" icon={<Timer className="size-4" />} />
          <div className="px-3 pb-4">{stats ? <Bars data={stats.series} x="date" y="focus_minutes" height={200} tick={(d) => monthDay(d)} format={(v) => minutesLabel(v)} labelFor={(d) => monthDay(d.date)} color="var(--color-brand-2)" /> : <Skeleton className="h-48" />}</div>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader title="Recent sessions" />
          {data?.history.length ? (
            <ul className="max-h-[260px] overflow-y-auto px-3 pb-3">
              {data.history.map((f) => (
                <li key={f.id} className="flex items-center gap-3 rounded-xl px-2 py-2.5 text-sm">
                  <span className={clsx("size-2 rounded-full", f.status === "completed" ? "bg-ok" : "bg-faint")} aria-hidden="true" />
                  <span className="num font-medium">{minutesLabel(f.status === "completed" ? f.actual_minutes : f.actual_minutes || 0)}</span>
                  <span className="truncate text-muted">{f.status === "completed" ? (f.quest_title ?? "Focus session") : "Ended early"}</span>
                  <span className="ml-auto shrink-0 text-xs text-faint">{relative(f.started_at)}</span>
                  {f.xp_awarded ? <span className="num shrink-0 text-xs font-semibold text-xp">+{f.xp_awarded}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No sessions yet" body="Your first finished session shows up here." />
          )}
        </Card>
      </div>

      <AnimatePresence>
        {active && !hidden ? (
          <SessionScreen session={active} quest={active.quest_id ? questsById.get(active.quest_id) : undefined} offsetMs={offset} onComplete={complete} onCancel={cancel} onMinimize={() => setHidden(true)} busy={busy} />
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function StatCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card className="p-5">
      <p className="text-xs text-muted">{label}</p>
      <p className="font-display num mt-1 text-3xl font-bold">{value}</p>
      <p className="mt-1 text-xs text-faint">{note}</p>
    </Card>
  );
}
