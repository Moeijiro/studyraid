export const nf = new Intl.NumberFormat("en-US");

export function num(n: number) {
  return nf.format(n);
}

export function minutesLabel(m: number) {
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h}h ${r}m` : `${h}h`;
}

export function hoursLabel(m: number) {
  return `${(m / 60).toFixed(m >= 600 ? 0 : 1)}h`;
}

export function relative(iso: string, now = Date.now()) {
  const diff = (new Date(iso).getTime() - now) / 1000;
  const abs = Math.abs(diff);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (abs < 60) return diff < 0 ? "just now" : "in a moment";
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  if (abs < 86400 * 7) return rtf.format(Math.round(diff / 86400), "day");
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "Today 21:00", "Tomorrow 20:00", "Fri 18:00", "Oct 3". */
export function dueLabel(iso: string, now = new Date()) {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const delta = Math.round((day(d) - day(now)) / 86400000);
  if (delta === 0) return `Today ${time}`;
  if (delta === 1) return `Tomorrow ${time}`;
  if (delta === -1) return `Yesterday ${time}`;
  if (delta > 1 && delta < 7) return `${d.toLocaleDateString("en-US", { weekday: "short" })} ${time}`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function isOverdue(iso: string | null) {
  return !!iso && new Date(iso).getTime() < Date.now();
}

export function shortDay(isoDate: string) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString("en-US", { weekday: "short" });
}

export function monthDay(isoDate: string) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function plural(n: number, word: string) {
  return `${num(n)} ${word}${n === 1 ? "" : "s"}`;
}
