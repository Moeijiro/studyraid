"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { useId } from "react";

/** The XP bar: a gradient fill with a slow shimmer, animated when it changes. */
export function XpBar({ progress, height = 10, className, label }: { progress: number; height?: number; className?: string; label: string }) {
  const pct = Math.max(0, Math.min(1, progress)) * 100;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={clsx("relative overflow-hidden rounded-full bg-white/[0.06] shadow-[inset_0_1px_2px_rgb(0_0_0/0.4)]", className)}
      style={{ height }}
    >
      <motion.div
        className="fill-xp absolute inset-y-0 left-0 overflow-hidden rounded-full shadow-[0_0_16px_-2px_rgb(143_124_255/0.8)]"
        initial={false}
        animate={{ width: `${pct}%` }}
        transition={{ type: "spring", stiffness: 90, damping: 20 }}
      >
        <span className="animate-shimmer absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/25 to-transparent" aria-hidden="true" />
      </motion.div>
    </div>
  );
}

export function ProgressBar({ value, max, color = "var(--color-brand)", height = 8, label }: { value: number; max: number; color?: string; height?: number; label: string }) {
  const pct = max > 0 ? Math.min(1, value / max) * 100 : 0;
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} className="relative overflow-hidden rounded-full bg-white/[0.06]" style={{ height }}>
      <motion.div className="absolute inset-y-0 left-0 rounded-full" style={{ background: color }} initial={false} animate={{ width: `${pct}%` }} transition={{ type: "spring", stiffness: 90, damping: 20 }} />
    </div>
  );
}

/** Circular level indicator used in the dashboard hero and sidebar. */
export function LevelRing({ level, progress, size = 88, stroke = 6 }: { level: number; progress: number; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  // Unique per instance: a shared id would resolve to a copy inside a hidden sidebar and not paint.
  const gradient = `lvl-${useId().replace(/:/g, "")}`;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <defs>
          <linearGradient id={gradient} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#8f7cff" />
            <stop offset="100%" stopColor="#6aa6ff" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(255 255 255 / 0.07)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`url(#${gradient})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={false}
          animate={{ strokeDashoffset: c * (1 - Math.max(0, Math.min(1, progress))) }}
          transition={{ type: "spring", stiffness: 80, damping: 20 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[9px] font-semibold tracking-[0.18em] text-faint uppercase">Level</span>
        <span className="font-display num text-2xl leading-none font-bold" style={{ fontSize: size * 0.3 }}>
          {level}
        </span>
      </div>
    </div>
  );
}
