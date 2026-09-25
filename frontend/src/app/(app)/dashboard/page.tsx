"use client";

import { AchievementsCard, ActivityCard, FocusCard, PartyCard, TodayQuests, Upcoming, WeeklyXp } from "@/components/dashboard/cards";
import { Hero } from "@/components/dashboard/hero";
import { ErrorNote, Skeleton } from "@/components/ui/card";
import { useResource } from "@/lib/store";
import type { Summary } from "@/lib/types";

export default function DashboardPage() {
  const { data: s, error, reload } = useResource<Summary>("/api/me/summary");

  if (error && !s) return <ErrorNote message={error.message} onRetry={reload} />;
  if (!s) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-52 rounded-[1.125rem]" />
        <div className="grid gap-5 lg:grid-cols-12">
          <Skeleton className="h-80 rounded-[1.125rem] lg:col-span-7" />
          <Skeleton className="h-80 rounded-[1.125rem] lg:col-span-5" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <title>Dashboard · StudyRaid</title>
      <Hero s={s} />
      <div className="grid gap-5 lg:grid-cols-12">
        <div className="min-w-0 lg:col-span-7">
          <TodayQuests s={s} />
        </div>
        <div className="min-w-0 lg:col-span-5">
          <WeeklyXp s={s} />
        </div>
      </div>
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-12">
        <div className="min-w-0 lg:col-span-5">
          <PartyCard s={s} />
        </div>
        <div className="min-w-0 lg:col-span-3">
          <FocusCard s={s} />
        </div>
        <div className="min-w-0 md:col-span-2 lg:col-span-4">
          <AchievementsCard s={s} />
        </div>
      </div>
      <div className="grid gap-5 lg:grid-cols-12">
        <div className="min-w-0 lg:col-span-8">
          <ActivityCard />
        </div>
        <div className="min-w-0 lg:col-span-4">
          <Upcoming s={s} />
        </div>
      </div>
    </div>
  );
}
