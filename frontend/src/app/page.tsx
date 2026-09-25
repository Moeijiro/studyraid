import type { Metadata } from "next";
import Link from "next/link";
import { CalendarCheck, Flame, Hourglass, Swords, Trophy, Zap } from "lucide-react";
import { Logo } from "@/components/game/logo";
import { ButtonLink } from "@/components/ui/button";

export const metadata: Metadata = { title: { absolute: "StudyRaid: homework, but it's a quest" } };

const FEATURES = [
  { icon: Zap, title: "Quests, not to-dos", body: "Homework becomes quests with a difficulty, a deadline and an XP reward the server works out." },
  { icon: Flame, title: "Streaks that forgive", body: "One meaningful thing a day keeps the streak. Coins buy a freeze for the day life gets in the way." },
  { icon: Hourglass, title: "Focus mode", body: "A calm full-screen timer. Only time that actually passed counts." },
  { icon: Swords, title: "Parties", body: "Small groups with shared weekly goals and live progress. Competition is optional." },
  { icon: Trophy, title: "Achievements", body: "Unlocked by what you actually do: Night Owl, Boss Slayer, No Days Off." },
  { icon: CalendarCheck, title: "Honest stats", body: "XP by day, focus time, completion rate and your most productive weekday." },
];

export default function Landing() {
  return (
    <div className="app-backdrop min-h-dvh">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Logo />
        <nav className="flex items-center gap-2">
          <Link href="/login" className="rounded-xl px-3 py-2 text-sm text-muted hover:text-fg">
            Sign in
          </Link>
          <ButtonLink href="/register" size="sm">
            Get started
          </ButtonLink>
        </nav>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-5 sm:px-8">
        <section className="pt-14 pb-16 text-center sm:pt-24">
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-white/[0.03] px-3 py-1 text-xs text-muted">
            <span className="size-1.5 rounded-full bg-xp" /> Season 1 · study together
          </p>
          <h1 className="font-display mx-auto mt-6 max-w-3xl text-4xl font-bold text-balance sm:text-6xl sm:leading-[1.05]">
            Homework, but it&apos;s a <span className="text-brand">quest</span>.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base text-pretty text-muted sm:text-lg">
            StudyRaid turns assignments, revision and goals into quests. Earn XP, keep your streak, focus without distractions and take on challenges with friends.
          </p>
          <div className="mt-9 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
            <ButtonLink href="/login" size="lg">
              Try the demo
            </ButtonLink>
            <ButtonLink href="/register" size="lg" variant="secondary">
              Create an account
            </ButtonLink>
          </div>
        </section>
        <section aria-label="Features" className="grid gap-4 pb-24 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="panel p-6">
              <span className="flex size-10 items-center justify-center rounded-xl bg-brand/12 text-brand">
                <Icon className="size-5" />
              </span>
              <h2 className="font-display mt-4 text-lg font-semibold">{title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
