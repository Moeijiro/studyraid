"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, CalendarDays, Hourglass, Plus, ScrollText, Swords, Trophy } from "lucide-react";
import { Bars } from "@/components/analytics/charts";
import { Heatmap } from "@/components/analytics/heatmap";
import { AvatarStack, DifficultyPill, Medal, SubjectTag, XpPill } from "@/components/game/bits";
import { NamedIcon } from "@/components/game/icons";
import { ProgressBar } from "@/components/game/xp-bar";
import { QuestDialog } from "@/components/quests/quest-dialog";
import { QuestRow } from "@/components/quests/quest-row";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, CardHeader, EmptyState, Skeleton } from "@/components/ui/card";
import { dueLabel, minutesLabel, num, relative, shortDay } from "@/lib/format";
import { useResource } from "@/lib/store";
import type { Heatmap as HeatmapData, Summary } from "@/lib/types";

export function TodayQuests({ s }: { s: Summary }) {
  const [open, setOpen] = useState(false);
  const all = [...s.today_quests, ...s.completed_today];
  return (
    <Card className="flex h-full flex-col">
      <CardHeader
        title="Today's quests"
        icon={<ScrollText className="size-4" />}
        action={
          <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
            <Plus className="size-3.5" /> New quest
          </Button>
        }
      />
      {all.length ? (
        <ul className="px-2 pb-3">
          {all.map((q) => (
            <QuestRow key={q.id} quest={q} />
          ))}
        </ul>
      ) : (
        <EmptyState icon={<ScrollText className="size-5" />} title="A clear board" body="Nothing is due today. Plan tomorrow's work or start a focus session." />
      )}
      <Link href="/quests" className="mt-auto flex items-center justify-center gap-1.5 border-t border-line py-3 text-xs text-muted hover:text-fg">
        Open quest board <ArrowRight className="size-3.5" />
      </Link>
      <QuestDialog open={open} onClose={() => setOpen(false)} />
    </Card>
  );
}

export function WeeklyXp({ s }: { s: Summary }) {
  const today = s.week[s.week.length - 1]?.date;
  const best = Math.max(...s.week.map((d) => d.xp));
  return (
    <Card>
      <CardHeader title="Weekly XP" subtitle={`${num(s.week.reduce((a, d) => a + d.xp, 0))} XP in the last 7 days · best day ${num(best)}`} />
      <div className="px-3 pb-4">
        <Bars data={s.week} x="date" y="xp" height={210} tick={shortDay} highlight={(d) => d.date === today} labelFor={(d) => (d.date === today ? "Today" : new Date(`${d.date}T12:00`).toLocaleDateString("en-US", { weekday: "long" }))} format={(v) => `${num(v)} XP`} />
      </div>
    </Card>
  );
}

export function FocusCard({ s }: { s: Summary }) {
  return (
    <Card className="flex h-full flex-col p-5">
      <h2 className="flex items-center gap-2 text-[13px] font-semibold tracking-wide text-muted uppercase">
        <Hourglass className="size-4 text-faint" /> Focus
      </h2>
      <p className="font-display num mt-3 text-4xl font-bold">{minutesLabel(s.focus.today_minutes)}</p>
      <p className="text-sm text-muted">focused today</p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl bg-white/[0.03] p-2.5">
          <dt className="text-faint">This week</dt>
          <dd className="num mt-0.5 font-semibold">{minutesLabel(s.focus.week_minutes)}</dd>
        </div>
        <div className="rounded-xl bg-white/[0.03] p-2.5">
          <dt className="text-faint">All time</dt>
          <dd className="num mt-0.5 font-semibold">{Math.round(s.focus.total_minutes / 60)}h</dd>
        </div>
      </dl>
      <ButtonLink href="/focus" className="mt-5 w-full" size="md">
        {s.active_focus_id ? "Resume session" : "Start focus"}
      </ButtonLink>
    </Card>
  );
}

export function AchievementsCard({ s }: { s: Summary }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader
        title="Recent achievements"
        icon={<Trophy className="size-4" />}
        action={
          <Link href="/achievements" className="text-xs text-muted hover:text-fg">
            View all
          </Link>
        }
      />
      {s.recent_achievements.length ? (
        <ul className="space-y-1 px-3 pb-4">
          {s.recent_achievements.map((a) => (
            <li key={a.code} className="flex items-center gap-3 rounded-xl px-2 py-2">
              <Medal icon={a.icon} tier={a.tier} size={38} />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{a.name}</p>
                <p className="truncate text-xs text-faint">{a.description}</p>
              </div>
              <span className="ml-auto shrink-0 text-[11px] text-faint">{a.unlocked_at ? relative(a.unlocked_at) : ""}</span>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState icon={<Trophy className="size-5" />} title="No achievements yet" body="Complete your first quest to unlock First Blood." />
      )}
    </Card>
  );
}

export function PartyCard({ s }: { s: Summary }) {
  const party = s.parties.find((p) => p.active_challenge) ?? s.parties[0];
  if (!party) {
    return (
      <Card className="flex h-full flex-col">
        <CardHeader title="Party" icon={<Swords className="size-4" />} />
        <EmptyState icon={<Swords className="size-5" />} title="Study with friends" body="Create a party and take on weekly challenges together." action={<ButtonLink href="/party" size="sm" variant="secondary">Create a party</ButtonLink>} />
      </Card>
    );
  }
  const ch = party.active_challenge;
  return (
    <Card className="flex h-full flex-col p-5">
      <div className="flex items-center gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl" style={{ background: `oklch(0.5 0.13 ${party.hue} / 0.22)`, color: `oklch(0.8 0.12 ${party.hue})` }}>
          <NamedIcon name={party.icon} className="size-5" />
        </span>
        <div className="min-w-0">
          <Link href={`/party/${party.id}`} className="font-display block truncate font-semibold hover:underline">
            {party.name}
          </Link>
          <p className="num text-xs text-muted">
            {party.member_count} members · {num(party.weekly_xp)} XP this week
          </p>
        </div>
      </div>
      {ch ? (
        <div className="mt-5">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-sm font-medium">{ch.title}</p>
            <p className="num shrink-0 text-xs text-muted">ends {relative(ch.ends_at)}</p>
          </div>
          <div className="mt-3">
            <ProgressBar value={ch.progress} max={ch.target} height={10} color="linear-gradient(90deg,#f0a93b,#f6c35b)" label={`${ch.title} progress`} />
          </div>
          <div className="mt-2.5 flex items-center justify-between">
            <AvatarStack people={ch.contributions.filter((c) => c.value > 0).map((c) => ({ name: c.display_name, hue: c.avatar_hue }))} />
            <p className="num text-sm">
              <span className="font-semibold">{num(ch.progress)}</span>
              <span className="text-muted">
                {" "}
                / {num(ch.target)} {ch.unit}
              </span>
            </p>
          </div>
          <p className="mt-3 text-xs text-faint">Reward: +{ch.reward_xp} XP for every contributor</p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted">No challenge running. The leader can start one.</p>
      )}
      <ButtonLink href={`/party/${party.id}`} variant="secondary" size="sm" className="mt-5 w-full">
        Open party
      </ButtonLink>
    </Card>
  );
}

export function Upcoming({ s }: { s: Summary }) {
  return (
    <Card>
      <CardHeader title="Upcoming" icon={<CalendarDays className="size-4" />} subtitle="Due in the next 7 days" />
      {s.upcoming_quests.length ? (
        <ul className="px-3 pb-3">
          {s.upcoming_quests.map((q) => (
            <li key={q.id} className="flex items-center gap-3 rounded-xl px-2 py-2.5">
              <div className="w-14 shrink-0 text-center">
                <p className="text-[10px] font-semibold tracking-wider text-faint uppercase">{new Date(q.due_at!).toLocaleDateString("en-US", { weekday: "short" })}</p>
                <p className="font-display num text-lg leading-tight font-bold">{new Date(q.due_at!).getDate()}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{q.title}</p>
                <div className="mt-1 flex items-center gap-1.5">
                  <SubjectTag subject={q.subject} />
                  <DifficultyPill difficulty={q.difficulty} />
                </div>
              </div>
              <div className="hidden text-right sm:block">
                <XpPill xp={q.base_xp} />
                <p className="mt-1 text-[11px] text-faint">{dueLabel(q.due_at!)}</p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState icon={<CalendarDays className="size-5" />} title="Nothing scheduled" body="Quests with a due date in the next week show up here." />
      )}
    </Card>
  );
}

export function ActivityCard() {
  const { data } = useResource<HeatmapData>("/api/me/heatmap?weeks=26");
  return (
    <Card>
      <CardHeader title="Activity" subtitle="Days with a completed quest or focus session keep the streak" />
      <div className="px-5 pb-5">{data ? <Heatmap data={data} /> : <Skeleton className="h-32" />}</div>
    </Card>
  );
}
