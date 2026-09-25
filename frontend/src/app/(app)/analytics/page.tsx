"use client";

import { CalendarRange, Clock3, Flame, Percent, ScrollText, Sparkles } from "lucide-react";
import { useState } from "react";
import { AreaTrend, Bars } from "@/components/analytics/charts";
import { Heatmap } from "@/components/analytics/heatmap";
import { Card, CardHeader, EmptyState, ErrorNote, Skeleton } from "@/components/ui/card";
import { Segmented } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { subjectHue } from "@/lib/game";
import { hoursLabel, minutesLabel, monthDay, num, plural } from "@/lib/format";
import { useResource } from "@/lib/store";
import type { Analytics, Heatmap as HeatmapData } from "@/lib/types";

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data: a, error, reload } = useResource<Analytics>(`/api/analytics/overview?days=${days}`);
  const { data: heat } = useResource<HeatmapData>("/api/me/heatmap?weeks=26");

  return (
    <div>
      <title>Analytics · StudyRaid</title>
      <PageHeader
        title="Analytics"
        subtitle="Computed from your quest history, focus sessions and XP ledger."
        action={<Segmented label="Range" value={days} onChange={setDays} options={[7, 30, 90].map((d) => ({ value: d, label: `${d} days` }))} />}
      />
      {error && !a ? <ErrorNote message={error.message} onRetry={reload} /> : null}
      {!a ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-28 rounded-[1.125rem]" />
          ))}
        </div>
      ) : (
        <div className="space-y-5">
          <dl className="grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-5">
            <Kpi icon={<Sparkles className="size-4 text-xp" />} label="XP earned" value={num(a.totals.xp)} note={`${num(a.totals.avg_daily_xp)} per day`} />
            <Kpi icon={<ScrollText className="size-4 text-ok" />} label="Quests completed" value={num(a.totals.quests_completed)} note={`${a.closed_quests.failed + a.closed_quests.expired} missed`} />
            <Kpi icon={<Clock3 className="size-4 text-brand-2" />} label="Focus time" value={hoursLabel(a.totals.focus_minutes)} note={plural(a.totals.focus_sessions, "session")} />
            <Kpi icon={<Percent className="size-4 text-brand" />} label="Completion rate" value={a.completion_rate === null ? "·" : `${Math.round(a.completion_rate * 100)}%`} note="of quests closed" />
            <Kpi icon={<Flame className="size-4 text-ember" />} label="Active days" value={`${a.totals.active_days}/${a.days}`} note={a.most_productive_weekday ? `Best: ${a.most_productive_weekday.name}s` : "No activity yet"} className="col-span-2 lg:col-span-1" />
          </dl>

          <div className="grid gap-5 lg:grid-cols-12">
            <Card className="lg:col-span-8">
              <CardHeader title="XP by day" subtitle={a.best_day ? `Best day: ${monthDay(a.best_day.date)} with ${num(a.best_day.xp)} XP` : undefined} />
              <div className="px-3 pb-4">
                <AreaTrend data={a.series} x="date" y="xp" height={240} tick={monthDay} labelFor={(d) => monthDay(d.date)} format={(v) => `${num(v)} XP`} />
              </div>
            </Card>
            <Card className="lg:col-span-4">
              <CardHeader title="Most productive day" subtitle="Average XP per weekday in this range" />
              <div className="px-3 pb-4">
                <Bars
                  data={a.weekday_avg_xp}
                  x="name"
                  y="avg_xp"
                  height={240}
                  highlight={(d) => d.weekday === a.most_productive_weekday?.weekday}
                  format={(v) => `${num(v)} XP avg`}
                  labelFor={(d) => String(d.name)}
                />
              </div>
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-12">
            <Card className="lg:col-span-5">
              <CardHeader title="Subjects" subtitle={a.top_subject ? `Most studied: ${a.top_subject}` : "Complete quests to see subjects"} />
              {a.subjects.length ? (
                <ul className="space-y-3 px-5 pb-5">
                  {a.subjects.slice(0, 7).map((s) => {
                    const max = a.subjects[0].xp || 1;
                    return (
                      <li key={s.subject}>
                        <div className="flex items-baseline justify-between gap-3 text-sm">
                          <span className="flex items-center gap-2 font-medium">
                            <span className="size-2 rounded-full" style={{ background: `oklch(0.72 0.13 ${subjectHue(s.subject)})` }} aria-hidden="true" />
                            {s.subject}
                          </span>
                          <span className="num text-xs text-muted">
                            {num(s.xp)} XP · {s.quests} quests{s.focus_minutes ? ` · ${minutesLabel(s.focus_minutes)}` : ""}
                          </span>
                        </div>
                        <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/[0.05]">
                          <div className="h-full rounded-full bg-brand/80" style={{ width: `${(s.xp / max) * 100}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <EmptyState title="No completed quests in this range" />
              )}
            </Card>
            <Card className="lg:col-span-4">
              <CardHeader title="Focus minutes by day" />
              <div className="px-3 pb-4">
                <Bars data={a.series} x="date" y="focus_minutes" height={220} tick={monthDay} labelFor={(d) => monthDay(d.date)} format={(v) => minutesLabel(v)} color="var(--color-brand-2)" />
              </div>
            </Card>
            <Card className="lg:col-span-3">
              <CardHeader title="Quest outcomes" subtitle={`${a.closed_quests.completed + a.closed_quests.failed + a.closed_quests.expired} closed`} />
              <Outcomes c={a.closed_quests} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-12">
            <Card className="lg:col-span-4">
              <CardHeader title="Weekly progress" subtitle="XP per week, last 8 weeks" icon={<CalendarRange className="size-4" />} />
              <div className="px-3 pb-4">
                <Bars data={a.weekly} x="week_start" y="xp" height={200} tick={monthDay} labelFor={(d) => `Week of ${monthDay(String(d.week_start))}`} format={(v) => `${num(v)} XP`} highlight={(d) => d.week_start === a.weekly[a.weekly.length - 1].week_start} />
              </div>
            </Card>
            <Card className="min-w-0 lg:col-span-8">
              <CardHeader title="Activity heatmap" subtitle="Last 26 weeks" />
              <div className="px-5 pb-5">{heat ? <Heatmap data={heat} maxCell={22} /> : <Skeleton className="h-36" />}</div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ icon, label, value, note, className }: { icon: React.ReactNode; label: string; value: string; note: string; className?: string }) {
  return (
    <div className={`panel p-4 sm:p-5 ${className ?? ""}`}>
      <dt className="flex items-center gap-2 text-xs text-muted">
        {icon}
        {label}
      </dt>
      <dd className="font-display num mt-2 text-2xl font-bold sm:text-3xl">{value}</dd>
      <p className="mt-1 truncate text-xs text-faint">{note}</p>
    </div>
  );
}

/** Outcomes as one stacked bar plus a labelled list: state colors always come with a word. */
function Outcomes({ c }: { c: Analytics["closed_quests"] }) {
  const total = c.completed + c.failed + c.expired;
  const rows = [
    { key: "Completed", value: c.completed, color: "var(--color-ok)" },
    { key: "Expired", value: c.expired, color: "var(--color-ember)" },
    { key: "Given up", value: c.failed, color: "var(--color-faint)" },
  ];
  if (!total) return <EmptyState title="Nothing closed yet" />;
  return (
    <div className="px-5 pb-5">
      <div className="flex h-3 gap-[2px] overflow-hidden rounded-full" role="img" aria-label={rows.map((r) => `${r.key} ${r.value}`).join(", ")}>
        {rows.filter((r) => r.value).map((r) => (
          <span key={r.key} style={{ width: `${(r.value / total) * 100}%`, background: r.color }} />
        ))}
      </div>
      <ul className="mt-5 space-y-3 text-sm">
        {rows.map((r) => (
          <li key={r.key} className="flex items-center gap-2.5">
            <span className="size-2.5 rounded-[3px]" style={{ background: r.color }} aria-hidden="true" />
            <span className="text-muted">{r.key}</span>
            <span className="num ml-auto font-semibold">{r.value}</span>
            <span className="num w-10 text-right text-xs text-faint">{Math.round((r.value / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
