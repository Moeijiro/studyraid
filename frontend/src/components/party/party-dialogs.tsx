"use client";

import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { NamedIcon } from "@/components/game/icons";
import { Button } from "@/components/ui/button";
import { ErrorNote } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Segmented } from "@/components/ui/field";
import { ApiError, post } from "@/lib/api";
import { invalidate } from "@/lib/store";
import type { Challenge, PartyDetail } from "@/lib/types";

const HUES = [265, 205, 150, 30, 330, 95];

export function CreatePartyDialog({ open, onClose, icons }: { open: boolean; onClose: () => void; icons: string[] }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [icon, setIcon] = useState("sword");
  const [hue, setHue] = useState(265);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 2) return setError("Name your party (at least 2 characters).");
    setPending(true);
    setError(null);
    try {
      const party = await post<PartyDetail>("/api/parties", { name: name.trim(), description, icon, hue });
      invalidate("/api/parties", "/api/me/summary");
      onClose();
      router.push(`/party/${party.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the party.");
    } finally {
      setPending(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Create a party">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Name" htmlFor="p-name">
          <Input id="p-name" maxLength={40} placeholder="Night Library" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Motto" htmlFor="p-desc" hint="Optional">
          <Input id="p-desc" maxLength={200} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <fieldset>
          <legend className="text-[13px] font-medium text-muted">Crest</legend>
          <div className="mt-2 grid grid-cols-6 gap-2">
            {icons.map((i) => (
              <button
                type="button"
                key={i}
                onClick={() => setIcon(i)}
                aria-pressed={icon === i}
                aria-label={i}
                className={clsx("flex aspect-square items-center justify-center rounded-xl border transition-colors", icon === i ? "border-transparent" : "border-line text-muted hover:border-line-2")}
                style={icon === i ? { background: `oklch(0.5 0.13 ${hue} / 0.25)`, color: `oklch(0.82 0.12 ${hue})`, boxShadow: `inset 0 0 0 1px oklch(0.7 0.12 ${hue} / 0.6)` } : undefined}
              >
                <NamedIcon name={i} className="size-5" />
              </button>
            ))}
          </div>
          <div className="mt-3 flex gap-2" role="radiogroup" aria-label="Color">
            {HUES.map((h) => (
              <button
                type="button"
                key={h}
                role="radio"
                aria-checked={hue === h}
                aria-label={`Hue ${h}`}
                onClick={() => setHue(h)}
                className={clsx("size-7 rounded-full transition-transform", hue === h && "scale-110 ring-2 ring-white/70 ring-offset-2 ring-offset-panel")}
                style={{ background: `oklch(0.62 0.15 ${h})` }}
              />
            ))}
          </div>
        </fieldset>
        {error ? <ErrorNote message={error} /> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            Create party
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

const METRICS = [
  { value: "quests_completed" as const, label: "Quests", unit: "quests", placeholder: 25, hint: "Quests completed by members" },
  { value: "focus_minutes" as const, label: "Focus", unit: "minutes", placeholder: 600, hint: "Minutes of finished focus sessions" },
  { value: "xp" as const, label: "XP", unit: "XP", placeholder: 3000, hint: "XP earned by members" },
];

export function ChallengeDialog({ open, onClose, partyId }: { open: boolean; onClose: () => void; partyId: number }) {
  const [metric, setMetric] = useState<Challenge["metric"]>("quests_completed");
  const [target, setTarget] = useState("25");
  const [days, setDays] = useState(7);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const m = METRICS.find((x) => x.value === metric)!;
  const suggested = metric === "quests_completed" ? `Complete ${target || m.placeholder} quests` : metric === "focus_minutes" ? `Study ${Math.round(Number(target || m.placeholder) / 60)} hours together` : `Earn ${target || m.placeholder} XP together`;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await post(`/api/parties/${partyId}/challenges`, { title: (title.trim() || suggested).slice(0, 80), metric, target: Number(target), duration_days: days });
      invalidate("/api/parties", "/api/me/summary");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't start the challenge.");
    } finally {
      setPending(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Start a party challenge">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <p className="text-[13px] font-medium text-muted">Goal</p>
          <Segmented label="Metric" value={metric} onChange={(v) => (setMetric(v), setTarget(String(METRICS.find((x) => x.value === v)!.placeholder)))} options={METRICS.map((x) => ({ value: x.value, label: x.label }))} />
          <p className="text-xs text-faint">{m.hint}. Only activity after each member joined counts.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={`Target (${m.unit})`} htmlFor="c-target">
            <Input id="c-target" type="number" inputMode="numeric" value={target} onChange={(e) => setTarget(e.target.value)} />
          </Field>
          <div className="space-y-1.5">
            <p className="text-[13px] font-medium text-muted">Duration</p>
            <Segmented label="Duration" value={days} onChange={setDays} options={[3, 7, 14].map((d) => ({ value: d, label: `${d} days` }))} />
          </div>
        </div>
        <Field label="Title" htmlFor="c-title" hint={`Leave empty for "${suggested}"`}>
          <Input id="c-title" maxLength={80} placeholder={suggested} value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        {error ? <ErrorNote message={error} /> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            Start challenge
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
