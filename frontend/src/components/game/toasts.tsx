"use client";

import { AnimatePresence, motion } from "motion/react";
import { Bell, ChevronsUp, Sparkles, X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { num } from "@/lib/format";
import type { AchievementBrief, RewardLine } from "@/lib/types";
import { Medal } from "./bits";

type Toast =
  | { id: number; kind: "xp"; xp: number; coins: number; title: string; lines?: RewardLine[] }
  | { id: number; kind: "achievement"; achievement: AchievementBrief }
  | { id: number; kind: "info"; title: string; body?: string }
  | { id: number; kind: "error"; title: string };

type NewToast = Toast extends infer T ? (T extends { id: number } ? Omit<T, "id"> : never) : never;

type Value = { push: (t: NewToast) => void; levelUp: (level: number) => void };

const ToastContext = createContext<Value | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [level, setLevel] = useState<number | null>(null);
  const seq = useRef(0);

  const dismiss = useCallback((id: number) => setToasts((ts) => ts.filter((t) => t.id !== id)), []);
  const push = useCallback(
    (t: NewToast) => {
      const id = ++seq.current;
      setToasts((ts) => [...ts.slice(-3), { ...t, id } as Toast]);
      window.setTimeout(() => dismiss(id), t.kind === "xp" ? 4200 : 5200);
    },
    [dismiss],
  );
  const levelUp = useCallback((lv: number) => setLevel(lv), []);
  const value = useMemo(() => ({ push, levelUp }), [push, levelUp]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-3 bottom-20 z-[60] flex flex-col items-end gap-2 sm:inset-x-auto sm:right-5 sm:bottom-5 lg:bottom-6">
        <AnimatePresence initial={false}>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ type: "spring", stiffness: 500, damping: 36 }}
              className="panel pointer-events-auto flex w-full items-start gap-3 p-3.5 sm:w-80"
            >
              <ToastBody toast={t} />
              <button onClick={() => dismiss(t.id)} className="ml-auto text-faint hover:text-fg" aria-label="Dismiss">
                <X className="size-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <LevelUpOverlay level={level} onClose={() => setLevel(null)} />
    </ToastContext.Provider>
  );
}

function ToastBody({ toast: t }: { toast: Toast }) {
  if (t.kind === "xp") {
    return (
      <>
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-xp/10 text-xp">
          <Sparkles className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="font-display num text-lg leading-tight font-bold text-xp">+{num(t.xp)} XP</p>
          <p className="truncate text-sm text-muted">{t.title}</p>
          {t.lines && t.lines.length > 1 ? (
            <p className="mt-1 text-[11px] text-faint">{t.lines.map((l) => `${l.label} ${l.xp >= 0 ? "+" : ""}${l.xp}`).join(" · ")}</p>
          ) : null}
          {t.coins ? <p className="mt-0.5 text-[11px] text-xp/80">+{t.coins} coins</p> : null}
        </div>
      </>
    );
  }
  if (t.kind === "achievement") {
    return (
      <>
        <Medal icon={t.achievement.icon} tier={t.achievement.tier} size={40} />
        <div>
          <p className="text-[11px] font-semibold tracking-wider text-faint uppercase">Achievement unlocked</p>
          <p className="font-display font-semibold">{t.achievement.name}</p>
        </div>
      </>
    );
  }
  return (
    <>
      <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${t.kind === "error" ? "bg-danger/10 text-danger" : "bg-brand/10 text-brand"}`}>
        <Bell className="size-5" />
      </span>
      <div className="min-w-0">
        <p className="font-medium">{t.title}</p>
        {"body" in t && t.body ? <p className="text-sm text-muted">{t.body}</p> : null}
      </div>
    </>
  );
}

function LevelUpOverlay({ level, onClose }: { level: number | null; onClose: () => void }) {
  return (
    <AnimatePresence>
      {level !== null ? (
        <motion.div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-6 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label={`Level ${level} reached`}
        >
          <motion.div
            className="panel relative w-full max-w-sm overflow-hidden p-8 text-center"
            initial={{ scale: 0.9, y: 12 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 22 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgb(143_124_255/0.35),transparent)]" />
            <div className="relative">
              <span className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-brand/15 text-brand glow-brand">
                <ChevronsUp className="size-7" />
              </span>
              <p className="mt-5 text-xs font-semibold tracking-[0.25em] text-faint uppercase">Level up</p>
              <p className="font-display num mt-1 text-6xl font-bold">{level}</p>
              <p className="mt-3 text-sm text-muted">New level reached. Keep the streak going.</p>
              <button autoFocus onClick={onClose} className="mt-6 h-10 w-full rounded-xl bg-brand font-medium text-brand-ink hover:bg-[#a293ff]">
                Continue
              </button>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

export function useToasts() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToasts outside ToastProvider");
  return ctx;
}

/** Shows everything a completion earned: XP, achievements, and a level-up. */
export function useRewardFeedback() {
  const { push, levelUp } = useToasts();
  return useCallback(
    (r: { xp: number; coins: number; breakdown: RewardLine[]; achievements: AchievementBrief[]; level: { level: number } }, title: string, levelBefore?: number) => {
      if (r.xp > 0) push({ kind: "xp", xp: r.xp, coins: r.coins, title, lines: r.breakdown });
      r.achievements.forEach((a) => push({ kind: "achievement", achievement: a }));
      if (levelBefore !== undefined && r.level.level > levelBefore) window.setTimeout(() => levelUp(r.level.level), 600);
    },
    [push, levelUp],
  );
}
