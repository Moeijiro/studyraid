"use client";

import { monthDay, num } from "@/lib/format";
import type { Heatmap as HeatmapData } from "@/lib/types";

// One hue, dark to bright: magnitude only. Frozen days get the ice color and
// are named in the legend, so the meaning never depends on color alone.
const LEVELS = ["rgb(255 255 255 / 0.045)", "oklch(0.40 0.09 285)", "oklch(0.52 0.14 285)", "oklch(0.64 0.17 285)", "oklch(0.78 0.14 285)"];
const FROZEN = "oklch(0.72 0.09 230)";
const DAYS = ["Mon", "", "Wed", "", "Fri", "", ""];

export function Heatmap({ data, maxCell = 18 }: { data: HeatmapData; maxCell?: number }) {
  const weeks: HeatmapData["days"][] = [];
  data.days.forEach((d, i) => {
    if (i % 7 === 0) weeks.push([]);
    weeks[weeks.length - 1].push(d);
  });
  const gap = 3;
  // Month labels sit over the first week of each month; one that would crowd the
  // previous label is dropped.
  const months: { index: number; label: string }[] = [];
  weeks.forEach((w, i) => {
    const label = new Date(`${w[0].date}T12:00:00`).toLocaleDateString("en-US", { month: "short" });
    const prev = months[months.length - 1];
    const newMonth = i === 0 || new Date(`${w[0].date}T12:00:00`).getMonth() !== new Date(`${weeks[i - 1][0].date}T12:00:00`).getMonth();
    if (newMonth && (!prev || i - prev.index >= 3)) months.push({ index: i, label });
  });
  const active = data.days.filter((d) => d.active).length;

  return (
    <div>
      <div className="flex gap-2" style={{ maxWidth: weeks.length * (maxCell + gap) + 32 }}>
        <div className="grid shrink-0 pt-[18px]" style={{ gap, gridTemplateRows: "repeat(7, minmax(0, 1fr))" }} aria-hidden="true">
          {DAYS.map((d, i) => (
            <span key={i} className="flex items-center text-[10px] leading-none text-faint">
              {d}
            </span>
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <div className="relative mb-1.5 h-3" aria-hidden="true">
            {months.map((m) => (
              <span key={`${m.label}-${m.index}`} className="absolute text-[10px] text-faint" style={{ left: `${(m.index / weeks.length) * 100}%` }}>
                {m.label}
              </span>
            ))}
          </div>
          <div className="grid" style={{ gap, gridTemplateColumns: `repeat(${weeks.length}, minmax(0, 1fr))` }} role="img" aria-label={`Activity over ${weeks.length} weeks: ${active} active days`}>
            {weeks.map((w, i) => (
              <div key={i} className="grid content-start" style={{ gap, gridTemplateRows: "repeat(7, auto)" }}>
                {w.map((d) => (
                  <span
                    key={d.date}
                    title={`${monthDay(d.date)} · ${d.frozen ? "streak freeze" : `${num(d.xp)} XP`}`}
                    className="aspect-square w-full rounded-[3px] transition-transform hover:scale-125"
                    style={{ background: d.frozen ? FROZEN : LEVELS[d.level] }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[11px] text-faint">
        <span>
          <span className="num text-muted">{active}</span> active days
        </span>
        <span className="flex items-center gap-1.5">
          Less
          {LEVELS.map((c, i) => (
            <span key={i} className="size-2.5 rounded-[3px]" style={{ background: c }} />
          ))}
          More
          <span className="ml-2 size-2.5 rounded-[3px]" style={{ background: FROZEN }} /> Freeze
        </span>
      </div>
    </div>
  );
}
