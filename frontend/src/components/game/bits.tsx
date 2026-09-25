import clsx from "clsx";
import { Coins, Flame, Snowflake } from "lucide-react";
import { DIFFICULTY, subjectHue, TIER } from "@/lib/game";
import { num } from "@/lib/format";
import type { Difficulty, Tier } from "@/lib/types";
import { NamedIcon } from "./icons";

export function Avatar({ name, hue, size = 32, ring }: { name: string; hue: number; size?: number; ring?: boolean }) {
  return (
    <span
      className={clsx("inline-flex shrink-0 items-center justify-center rounded-full font-display font-semibold text-white/95 select-none", ring && "ring-2 ring-bg")}
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.42),
        background: `linear-gradient(135deg, oklch(0.62 0.15 ${hue}), oklch(0.45 0.13 ${(hue + 40) % 360}))`,
      }}
      aria-hidden="true"
    >
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

export function AvatarStack({ people, max = 5, size = 26 }: { people: { name: string; hue: number }[]; max?: number; size?: number }) {
  const shown = people.slice(0, max);
  return (
    <div className="flex -space-x-2">
      {shown.map((p, i) => (
        <span key={`${p.name}-${i}`} title={p.name}>
          <Avatar name={p.name} hue={p.hue} size={size} ring />
        </span>
      ))}
      {people.length > max ? (
        <span className="inline-flex items-center justify-center rounded-full bg-panel-3 text-[11px] text-muted ring-2 ring-bg" style={{ width: size, height: size }}>
          +{people.length - max}
        </span>
      ) : null}
    </div>
  );
}

export function DifficultyPill({ difficulty, className }: { difficulty: Difficulty; className?: string }) {
  const d = DIFFICULTY[difficulty];
  return (
    <span
      className={clsx("inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase", className)}
      style={{ color: d.color, background: `color-mix(in oklch, ${d.color} 13%, transparent)` }}
    >
      <span className="size-1.5 rotate-45 rounded-[1px]" style={{ background: d.color }} aria-hidden="true" />
      {d.label}
    </span>
  );
}

export function SubjectTag({ subject }: { subject: string }) {
  const hue = subjectHue(subject);
  return (
    <span className="inline-flex max-w-[11rem] items-center gap-1.5 truncate rounded-md border border-line px-1.5 py-0.5 text-[11px] text-muted">
      <span className="size-1.5 shrink-0 rounded-full" style={{ background: `oklch(0.72 0.13 ${hue})` }} aria-hidden="true" />
      <span className="truncate">{subject}</span>
    </span>
  );
}

export function XpPill({ xp, muted }: { xp: number; muted?: boolean }) {
  return (
    <span className={clsx("num inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[12px] font-semibold", muted ? "bg-white/[0.04] text-muted" : "bg-xp/10 text-xp")}>
      +{num(xp)} XP
    </span>
  );
}

export function CoinCount({ coins, className }: { coins: number; className?: string }) {
  return (
    <span className={clsx("num inline-flex items-center gap-1.5 font-semibold text-xp", className)}>
      <Coins className="size-4" aria-hidden="true" />
      {num(coins)}
      <span className="sr-only">coins</span>
    </span>
  );
}

export function StreakBadge({ days, active, frozen }: { days: number; active: boolean; frozen?: boolean }) {
  const Icon = frozen ? Snowflake : Flame;
  return (
    <span className={clsx("num inline-flex items-center gap-1.5 font-semibold", days > 0 ? (active ? "text-ember" : "text-ember/70") : "text-faint")}>
      <Icon className={clsx("size-4", days > 0 && active && "drop-shadow-[0_0_6px_rgb(255_138_76/0.7)]")} aria-hidden="true" />
      {days}
      <span className="sr-only">day streak</span>
    </span>
  );
}

export function Medal({ icon, tier, locked, size = 44 }: { icon: string; tier: Tier; locked?: boolean; size?: number }) {
  const color = TIER[tier].color;
  return (
    <span
      className={clsx("relative inline-flex shrink-0 items-center justify-center rounded-2xl", locked && "opacity-45 grayscale")}
      style={{
        width: size,
        height: size,
        background: locked ? "rgb(255 255 255 / 0.04)" : `radial-gradient(120% 120% at 30% 20%, color-mix(in oklch, ${color} 32%, transparent), color-mix(in oklch, ${color} 8%, transparent))`,
        boxShadow: locked ? "inset 0 0 0 1px rgb(255 255 255 / 0.08)" : `inset 0 0 0 1px color-mix(in oklch, ${color} 45%, transparent)`,
        color: locked ? "var(--color-faint)" : color,
      }}
    >
      <NamedIcon name={icon} className="size-[46%]" />
    </span>
  );
}
