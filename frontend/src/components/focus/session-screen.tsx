"use client";

import { motion } from "motion/react";
import { Minimize2, Sparkles, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import type { FocusSession, Quest } from "@/lib/types";

function fmt(total: number) {
  const s = Math.max(0, Math.ceil(total));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/**
 * The immersive timer. The countdown is derived from the server's start time and
 * the clock offset measured when the session loaded, so a sleeping tab or a
 * wrong local clock can't change how long the session lasts.
 */
export function SessionScreen({
  session,
  quest,
  offsetMs,
  onComplete,
  onCancel,
  onMinimize,
  busy,
}: {
  session: FocusSession;
  quest?: Quest;
  offsetMs: number;
  onComplete: () => void;
  onCancel: () => void;
  onMinimize: () => void;
  busy: boolean;
}) {
  const total = session.planned_minutes * 60;
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(t);
  }, []);
  const elapsed = (now + offsetMs - new Date(session.started_at).getTime()) / 1000;
  const remaining = total - elapsed;
  const done = remaining <= 15; // the server accepts completion up to 20 s early
  const progress = Math.min(1, Math.max(0, elapsed / total));

  useEffect(() => {
    document.title = done ? "Session complete · StudyRaid" : `${fmt(remaining)} · Focus`;
  }, [done, remaining]);

  const size = 300;
  const r = 138;
  const c = 2 * Math.PI * r;

  return (
    <motion.div
      className="fixed inset-0 z-[55] flex flex-col items-center justify-center bg-[#07070b] px-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      role="dialog"
      aria-modal="true"
      aria-label="Focus session"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(40rem_28rem_at_50%_45%,rgb(143_124_255/0.12),transparent_70%)]" />
      <button onClick={onMinimize} className="absolute top-5 right-5 inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-faint hover:bg-white/[0.05] hover:text-fg">
        <Minimize2 className="size-4" /> Minimize
      </button>

      <p className="relative text-xs font-semibold tracking-[0.3em] text-faint uppercase">{done ? "Session complete" : "Focusing"}</p>
      <p className="relative mt-3 max-w-md text-center text-lg text-muted">{quest ? quest.title : "Deep work"}</p>

      <div className="relative mt-10" style={{ width: size, height: size }}>
        <motion.div
          className="absolute inset-6 rounded-full bg-brand/10 blur-2xl"
          animate={{ opacity: [0.4, 0.8, 0.4], scale: [0.96, 1.02, 0.96] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden="true"
        />
        <svg width={size} height={size} className="relative -rotate-90" aria-hidden="true">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(255 255 255 / 0.06)" strokeWidth={6} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={done ? "var(--color-xp)" : "url(#focus-grad)"}
            strokeWidth={6}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - progress)}
            style={{ transition: "stroke-dashoffset 0.25s linear" }}
          />
          <defs>
            <linearGradient id="focus-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#8f7cff" />
              <stop offset="100%" stopColor="#6aa6ff" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display num text-6xl font-bold tracking-tight sm:text-7xl" aria-live="off">
            {done ? fmt(0) : fmt(remaining)}
          </span>
          <span className="mt-2 text-sm text-faint">of {session.planned_minutes} minutes</span>
        </div>
      </div>

      <div className="relative mt-12 flex flex-col items-center gap-3 sm:flex-row">
        {done ? (
          <Button size="lg" onClick={onComplete} loading={busy} className="min-w-52">
            <Sparkles className="size-4" /> Claim {session.planned_minutes >= 10 ? `+${Math.floor(session.planned_minutes / 2)} XP` : "session"}
          </Button>
        ) : (
          <Button size="lg" variant="secondary" onClick={onCancel} disabled={busy} className="min-w-52">
            <Square className="size-3.5" /> End early
          </Button>
        )}
      </div>
      <p className="relative mt-5 max-w-sm text-center text-xs text-faint">
        {done ? "Nice work. Claim it to log the time and keep your streak." : "Ending early logs nothing. Only finished sessions count toward XP and your streak."}
      </p>
    </motion.div>
  );
}
