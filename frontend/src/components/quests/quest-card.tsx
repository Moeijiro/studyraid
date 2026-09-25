"use client";

import clsx from "clsx";
import { Check, Clock, Ellipsis, Hourglass, Pencil, Play, Trash2, Flag } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { DifficultyPill, SubjectTag, XpPill } from "@/components/game/bits";
import { Button } from "@/components/ui/button";
import { DIFFICULTY } from "@/lib/game";
import { dueLabel, isOverdue, minutesLabel, relative } from "@/lib/format";
import type { Quest } from "@/lib/types";
import { useQuestActions } from "./use-quest-actions";

export function QuestCard({ quest, onEdit }: { quest: Quest; onEdit: (q: Quest) => void }) {
  const { complete, start, abandon, remove } = useQuestActions();
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const open = quest.status === "planned" || quest.status === "active";
  const color = DIFFICULTY[quest.difficulty].color;
  const legendary = quest.difficulty === "legendary" && open;

  useEffect(() => {
    if (!menu) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setMenu(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setMenu(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [menu]);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setMenu(false);
    await fn();
    setBusy(false);
  };

  return (
    <article
      className={clsx("panel panel-hover group relative overflow-visible p-4", !open && "opacity-80", legendary && "border-legendary/25")}
      style={legendary ? { boxShadow: "0 0 0 1px rgb(255 181 71 / 0.12), 0 18px 40px -24px rgb(255 181 71 / 0.35)" } : undefined}
    >
      <span className="absolute top-4 bottom-4 left-0 w-[3px] rounded-r-full" style={{ background: open ? color : "var(--color-line-2)" }} aria-hidden="true" />
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <DifficultyPill difficulty={quest.difficulty} />
            {quest.priority === "high" && open ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ember">
                <Flag className="size-3" /> High
              </span>
            ) : null}
            {quest.status === "failed" || quest.status === "expired" ? (
              <span className="rounded-md bg-danger/10 px-1.5 py-0.5 text-[11px] font-medium text-danger capitalize">{quest.status}</span>
            ) : null}
          </div>
          <h3 className={clsx("mt-2 text-[15px] leading-snug font-semibold", quest.status === "completed" && "text-muted line-through decoration-faint/50")}>{quest.title}</h3>
          {quest.description && open ? <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-faint">{quest.description}</p> : null}
        </div>
        <XpPill xp={quest.status === "completed" ? (quest.xp_awarded ?? 0) : quest.base_xp} muted={!open} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[11px] text-faint">
        <SubjectTag subject={quest.subject} />
        {quest.due_at && open ? (
          <span className={clsx("inline-flex items-center gap-1", isOverdue(quest.due_at) ? "font-medium text-danger" : "")}>
            <Clock className="size-3" /> {isOverdue(quest.due_at) ? "Overdue · " : ""}
            {dueLabel(quest.due_at)}
          </span>
        ) : null}
        {quest.estimated_minutes && open ? <span>· {minutesLabel(quest.estimated_minutes)}</span> : null}
        {quest.closed_at && !open ? <span>{quest.status === "completed" ? "Completed" : "Closed"} {relative(quest.closed_at)}</span> : null}
      </div>

      {open ? (
        <div className="mt-4 flex items-center gap-2">
          {quest.status === "planned" ? (
            <Button size="sm" variant="secondary" onClick={() => run(() => start(quest))} disabled={busy}>
              <Play className="size-3.5" /> Start
            </Button>
          ) : null}
          <Button size="sm" onClick={() => run(() => complete(quest))} loading={busy}>
            <Check className="size-3.5" strokeWidth={3} /> Complete
          </Button>
          <div ref={ref} className="relative ml-auto">
            <button onClick={() => setMenu((m) => !m)} aria-label={`More actions for ${quest.title}`} aria-expanded={menu} className="inline-flex size-8 items-center justify-center rounded-lg text-faint hover:bg-white/[0.06] hover:text-fg">
              <Ellipsis className="size-4" />
            </button>
            {menu ? (
              <div className="panel absolute right-0 bottom-10 z-20 w-48 p-1.5 sm:top-9 sm:bottom-auto">
                <Link href={`/focus?quest=${quest.id}`} className="flex h-9 items-center gap-2.5 rounded-lg px-3 text-sm text-muted hover:bg-white/[0.05] hover:text-fg">
                  <Hourglass className="size-4" /> Focus on this
                </Link>
                <button onClick={() => (setMenu(false), onEdit(quest))} className="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-sm text-muted hover:bg-white/[0.05] hover:text-fg">
                  <Pencil className="size-4" /> Edit
                </button>
                <button onClick={() => run(() => abandon(quest))} className="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-sm text-muted hover:bg-white/[0.05] hover:text-fg">
                  <Flag className="size-4" /> Give up
                </button>
                <button onClick={() => run(() => remove(quest))} className="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-sm text-danger hover:bg-danger/10">
                  <Trash2 className="size-4" /> Delete
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </article>
  );
}
