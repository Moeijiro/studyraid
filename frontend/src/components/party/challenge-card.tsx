import clsx from "clsx";
import { CircleCheck, CircleX, Timer, Trophy } from "lucide-react";
import { Avatar } from "@/components/game/bits";
import { ProgressBar } from "@/components/game/xp-bar";
import { num, relative } from "@/lib/format";
import type { Challenge } from "@/lib/types";

export function ChallengeCard({ ch, compact }: { ch: Challenge; compact?: boolean }) {
  const pct = Math.min(100, Math.round((ch.progress / ch.target) * 100));
  const top = ch.contributions.filter((c) => c.value > 0);
  const max = Math.max(1, ...top.map((c) => c.value));
  return (
    <div className={clsx("min-w-0 rounded-2xl border p-4 sm:p-5", ch.status === "active" ? "border-xp/20 bg-xp/[0.035]" : "border-line bg-white/[0.015]")}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-semibold">
            {ch.status === "completed" ? <CircleCheck className="size-4 text-ok" /> : ch.status === "failed" ? <CircleX className="size-4 text-faint" /> : <Trophy className="size-4 text-xp" />}
            <span className="truncate">{ch.title}</span>
          </p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-faint">
            <Timer className="size-3" />
            {ch.status === "active" ? `Ends ${relative(ch.ends_at)}` : ch.status === "completed" && ch.completed_at ? `Cleared ${relative(ch.completed_at)}` : `Ended ${relative(ch.ends_at)}`}
            <span>· +{ch.reward_xp} XP each</span>
          </p>
        </div>
        <p className="num shrink-0 text-right">
          <span className="font-display text-xl font-bold">{pct}%</span>
        </p>
      </div>
      <div className="mt-3">
        <ProgressBar value={ch.progress} max={ch.target} height={10} color={ch.status === "failed" ? "var(--color-faint)" : "linear-gradient(90deg,#f0a93b,#f6c35b)"} label={`${ch.title}: ${ch.progress} of ${ch.target}`} />
      </div>
      <p className="num mt-2 text-xs text-muted">
        {num(ch.progress)} / {num(ch.target)} {ch.unit}
      </p>
      {!compact && top.length ? (
        <ul className="mt-4 space-y-2">
          {top.map((c) => (
            <li key={c.user_id} className="flex items-center gap-2.5 text-sm">
              <Avatar name={c.display_name} hue={c.avatar_hue} size={22} />
              <span className="w-16 truncate text-muted sm:w-20">{c.display_name}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
                <span className="block h-full rounded-full bg-xp/70" style={{ width: `${(c.value / max) * 100}%` }} />
              </span>
              <span className="num w-12 text-right text-xs text-muted">{num(c.value)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
