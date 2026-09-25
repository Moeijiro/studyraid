"use client";

// Chart building blocks. Single-series charts carry no legend (the card title
// names the series); axes and grid stay recessive; every mark has a tooltip.

import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { num } from "@/lib/format";

const GRID = "rgb(255 255 255 / 0.05)";

type TipProps = { active?: boolean; payload?: { value: number; payload: Record<string, unknown> }[]; label?: string | number };

export function ChartTooltip({ active, payload, format, labelFor }: TipProps & { format: (v: number) => string; labelFor: (p: Record<string, unknown>) => string }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="rounded-lg border border-line-2 bg-panel-2/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="text-faint">{labelFor(p.payload)}</p>
      <p className="num mt-0.5 text-sm font-semibold text-fg">{format(p.value)}</p>
    </div>
  );
}

export function Bars<T extends Record<string, unknown>>({
  data,
  x,
  y,
  height = 200,
  color = "var(--color-brand)",
  highlight,
  format = (v) => num(v),
  tick,
  labelFor,
  yWidth = 36,
}: {
  data: T[];
  x: keyof T & string;
  y: keyof T & string;
  height?: number;
  color?: string;
  highlight?: (row: T) => boolean;
  format?: (v: number) => string;
  tick?: (v: string) => string;
  labelFor?: (row: T) => string;
  yWidth?: number;
}) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data as Record<string, unknown>[]} margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barCategoryGap="22%">
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey={String(x)} tickLine={false} axisLine={false} tickFormatter={tick} interval="preserveStartEnd" minTickGap={8} />
          <YAxis width={yWidth} tickLine={false} axisLine={false} tickFormatter={(v: number) => (v >= 1000 ? `${Math.round(v / 100) / 10}k` : String(v))} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: "rgb(255 255 255 / 0.04)" }}
            content={<ChartTooltip format={format} labelFor={(p) => (labelFor ? labelFor(p as T) : String(p[x]))} />}
          />
          <Bar dataKey={String(y)} radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false}>
            {data.map((row, i) => (
              <Cell key={i} fill={highlight && !highlight(row) ? "color-mix(in oklch, var(--color-brand) 45%, var(--color-panel))" : color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AreaTrend<T extends Record<string, unknown>>({
  data,
  x,
  y,
  height = 220,
  color = "#8f7cff",
  format = (v) => num(v),
  tick,
  labelFor,
}: {
  data: T[];
  x: keyof T & string;
  y: keyof T & string;
  height?: number;
  color?: string;
  format?: (v: number) => string;
  tick?: (v: string) => string;
  labelFor?: (row: T) => string;
}) {
  const id = `area-${y}`;
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data as Record<string, unknown>[]} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey={String(x)} tickLine={false} axisLine={false} tickFormatter={tick} interval="preserveStartEnd" minTickGap={24} />
          <YAxis width={36} tickLine={false} axisLine={false} allowDecimals={false} tickFormatter={(v: number) => (v >= 1000 ? `${Math.round(v / 100) / 10}k` : String(v))} />
          <Tooltip
            cursor={{ stroke: "rgb(255 255 255 / 0.18)", strokeWidth: 1 }}
            content={<ChartTooltip format={format} labelFor={(p) => (labelFor ? labelFor(p as T) : String(p[x]))} />}
          />
          <Area type="monotone" dataKey={String(y)} stroke={color} strokeWidth={2} fill={`url(#${id})`} activeDot={{ r: 4, stroke: "var(--color-panel)", strokeWidth: 2 }} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
