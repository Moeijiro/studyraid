"use client";

import clsx from "clsx";
import { AnimatePresence, motion } from "motion/react";
import { Check, Clock } from "lucide-react";
import { useState } from "react";
import { DifficultyPill, SubjectTag, XpPill } from "@/components/game/bits";
import { DIFFICULTY } from "@/lib/game";
import { dueLabel, isOverdue, minutesLabel } from "@/lib/format";
import type { Quest } from "@/lib/types";
import { useQuestActions } from "./use-quest-actions";

/** Compact quest line with a one-click complete button (dashboard). */
export function QuestRow({ quest }: { quest: Quest }) {
  const { complete } = useQuestActions();
  const [burst, setBurst] = useState<number | null>(null);
  const [pending, setPending] = useState(false);
  const done = quest.status === "completed";
  const color = DIFFICULTY[quest.difficulty].color;

  const onComplete = async () => {
    setPending(true);
    const r = await complete(quest);
    setPending(false);
    if (r) setBurst(r.xp);
  };

  return (
    <li className="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-white/[0.03]">
      <span className="absolute top-3 bottom-3 left-0 w-[3px] rounded-full" style={{ background: done ? "var(--color-line-2)" : color }} aria-hidden="true" />
      <button
        onClick={onComplete}
        disabled={done || pending}
        aria-label={done ? `${quest.title} completed` : `Complete ${quest.title}`}
        className={clsx(
          "relative flex size-6 shrink-0 items-center justify-center rounded-lg border transition-all",
          done ? "border-ok/50 bg-ok/15 text-ok" : "border-line-2 text-transparent hover:border-brand hover:text-brand/60",
          pending && "animate-pulse",
        )}
      >
        <Check className="size-3.5" strokeWidth={3} />
        <AnimatePresence>
          {burst !== null ? (
            <motion.span
              key="burst"
              className="num pointer-events-none absolute -top-4 -left-1 text-sm font-bold whitespace-nowrap text-xp drop-shadow-[0_2px_6px_rgb(0_0_0/0.8)]"
              initial={{ opacity: 0, y: 0 }}
              animate={{ opacity: [0, 1, 1, 0], y: -22 }}
              transition={{ duration: 1.4 }}
              onAnimationComplete={() => setBurst(null)}
            >
              +{burst} XP
            </motion.span>
          ) : null}
        </AnimatePresence>
      </button>
      <div className="min-w-0 flex-1">
        <p className={clsx("truncate text-sm font-medium", done && "text-faint line-through decoration-faint/60")}>{quest.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <SubjectTag subject={quest.subject} />
          {!done ? <DifficultyPill difficulty={quest.difficulty} /> : null}
          {quest.status === "active" ? <span className="rounded-md bg-brand/12 px-1.5 py-0.5 text-[11px] font-medium text-brand">In progress</span> : null}
          {quest.due_at && !done ? (
            <span className={clsx("inline-flex items-center gap-1 text-[11px]", isOverdue(quest.due_at) ? "text-danger" : "text-faint")}>
              <Clock className="size-3" /> {dueLabel(quest.due_at)}
            </span>
          ) : null}
          {quest.estimated_minutes && !done ? <span className="text-[11px] text-faint">· {minutesLabel(quest.estimated_minutes)}</span> : null}
        </div>
      </div>
      <XpPill xp={done ? (quest.xp_awarded ?? 0) : quest.base_xp} muted={done} />
    </li>
  );
}
