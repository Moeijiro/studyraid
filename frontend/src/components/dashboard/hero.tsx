import { Clock3, Flame, ScrollText, Sparkles } from "lucide-react";
import { LevelRing, XpBar } from "@/components/game/xp-bar";
import { rankTitle } from "@/lib/game";
import { minutesLabel, num, plural } from "@/lib/format";
import type { Summary } from "@/lib/types";

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Burning the midnight oil";
  if (h < 12) return "Good morning";
  if (h < 18) return "Welcome back";
  return "Good evening";
}

export function Hero({ s }: { s: Summary }) {
  const { level } = s;
  const doneToday = s.completed_today.length;
  const totalToday = doneToday + s.today_quests.length;
  const week = s.week.slice(-7);
  return (
    <section className="panel relative overflow-hidden p-5 sm:p-7" aria-labelledby="hero-title">
      <div className="pointer-events-none absolute -top-24 -left-16 size-72 rounded-full bg-brand/15 blur-3xl" aria-hidden="true" />
      <div className="relative grid gap-7 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:items-center">
        <div className="flex items-center gap-5 sm:gap-6">
          <LevelRing level={level.level} progress={level.progress} size={104} stroke={7} />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted">{greeting()},</p>
            <h1 id="hero-title" className="font-display truncate text-2xl font-bold sm:text-[32px] sm:leading-tight">
              {s.user.display_name}.
            </h1>
            <p className="mt-1 text-xs font-semibold tracking-[0.18em] text-brand uppercase">
              {rankTitle(level.level)} · Level {level.level}
            </p>
            <XpBar className="mt-4" progress={level.progress} height={12} label={`Level ${level.level} progress`} />
            <div className="num mt-2 flex flex-wrap justify-between gap-x-4 text-xs text-muted">
              <span>
                <span className="font-semibold text-fg">{num(level.xp_into_level)}</span> / {num(level.xp_for_level)} XP
              </span>
              <span>
                {num(level.xp_for_level - level.xp_into_level)} XP to Level {level.level + 1}
              </span>
            </div>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-ember/20 bg-ember/[0.06] p-4">
            <dt className="flex items-center gap-1.5 text-xs text-muted">
              <Flame className="size-3.5 text-ember" /> Streak
            </dt>
            <dd className="font-display num mt-1 text-2xl font-bold">
              {s.streak.current} <span className="text-sm font-medium text-muted">{s.streak.current === 1 ? "day" : "days"}</span>
            </dd>
            <div className="mt-2 flex gap-1" aria-label="Last 7 days">
              {week.map((d) => (
                <span key={d.date} title={d.date} className={`h-1.5 flex-1 rounded-full ${d.xp > 0 ? "bg-ember" : "bg-white/10"}`} />
              ))}
            </div>
            <p className="mt-2 text-[11px] text-faint">
              {s.streak.at_risk ? "Do one quest today to keep it" : `Longest ${s.streak.longest}`}
            </p>
          </div>
          <Stat icon={<Sparkles className="size-3.5 text-xp" />} label="XP this week" value={num(s.weekly_xp)} note={`${num(level.total_xp)} total`} />
          <Stat icon={<Clock3 className="size-3.5 text-brand-2" />} label="Focus today" value={minutesLabel(s.focus.today_minutes)} note={`${plural(s.focus.today_sessions, "session")} · ${minutesLabel(s.focus.week_minutes)} this week`} />
          <Stat icon={<ScrollText className="size-3.5 text-ok" />} label="Today's quests" value={`${doneToday}/${totalToday || 0}`} note={totalToday ? `${Math.round((doneToday / totalToday) * 100)}% cleared` : "Nothing due today"} />
        </dl>
      </div>
    </section>
  );
}

function Stat({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white/[0.02] p-4">
      <dt className="flex items-center gap-1.5 text-xs text-muted">
        {icon} {label}
      </dt>
      <dd className="font-display num mt-1 text-2xl font-bold">{value}</dd>
      <p className="mt-2 truncate text-[11px] text-faint">{note}</p>
    </div>
  );
}
