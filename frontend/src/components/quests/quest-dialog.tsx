"use client";

import clsx from "clsx";
import { useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorNote } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Segmented, Select, Textarea } from "@/components/ui/field";
import { ApiError, patch, post } from "@/lib/api";
import { DIFFICULTY, previewXp, SUBJECTS } from "@/lib/game";
import { invalidate, useResource } from "@/lib/store";
import type { Difficulty, Priority, Quest } from "@/lib/types";

function toLocalInput(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultDue() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(20, 0, 0, 0);
  return toLocalInput(d.toISOString());
}

type Form = { title: string; subject: string; description: string; difficulty: Difficulty; priority: Priority; estimated_minutes: string; due: string };

function initial(quest?: Quest | null): Form {
  if (!quest) return { title: "", subject: "Mathematics", description: "", difficulty: "normal", priority: "normal", estimated_minutes: "45", due: defaultDue() };
  return {
    title: quest.title,
    subject: quest.subject,
    description: quest.description,
    difficulty: quest.difficulty,
    priority: quest.priority,
    estimated_minutes: quest.estimated_minutes ? String(quest.estimated_minutes) : "",
    due: toLocalInput(quest.due_at),
  };
}

export function QuestDialog({ open, onClose, quest }: { open: boolean; onClose: () => void; quest?: Quest | null }) {
  return (
    <Dialog open={open} onClose={onClose} title={quest ? "Edit quest" : "New quest"}>
      <QuestForm key={quest?.id ?? "new"} quest={quest} onDone={onClose} />
    </Dialog>
  );
}

function QuestForm({ quest, onDone }: { quest?: Quest | null; onDone: () => void }) {
  const { data: used } = useResource<string[]>("/api/quests/subjects");
  const [form, setForm] = useState<Form>(() => initial(quest));
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const onClose = onDone;

  const subjects = Array.from(new Set([...(used ?? []), ...SUBJECTS]));
  const minutes = form.estimated_minutes ? Number(form.estimated_minutes) : null;
  const xp = previewXp(form.difficulty, minutes);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return setError("Give the quest a name.");
    if (minutes !== null && (minutes < 5 || minutes > 600)) return setError("Estimates are between 5 and 600 minutes.");
    setPending(true);
    setError(null);
    const body = {
      title: form.title.trim(),
      subject: form.subject.trim() || "General",
      description: form.description,
      difficulty: form.difficulty,
      priority: form.priority,
      estimated_minutes: minutes,
      due_at: form.due ? new Date(form.due).toISOString() : null,
    };
    try {
      if (quest) await patch(`/api/quests/${quest.id}`, body);
      else await post("/api/quests", body);
      invalidate("/api/quests", "/api/me/summary");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the quest.");
    } finally {
      setPending(false);
    }
  };

  return (
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Quest" htmlFor="q-title">
          <Input id="q-title" placeholder="e.g. Problem set 7: integration by parts" maxLength={120} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Subject" htmlFor="q-subject">
            <Input id="q-subject" list="subjects" maxLength={40} value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
            <datalist id="subjects">
              {subjects.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
          </Field>
          <Field label="Due" htmlFor="q-due" hint="Optional">
            <Input id="q-due" type="datetime-local" value={form.due} onChange={(e) => setForm({ ...form, due: e.target.value })} />
          </Field>
        </div>
        <div className="space-y-1.5">
          <p className="text-[13px] font-medium text-muted">Difficulty</p>
          <Segmented
            label="Difficulty"
            value={form.difficulty}
            onChange={(v) => setForm({ ...form, difficulty: v })}
            options={(Object.keys(DIFFICULTY) as Difficulty[]).map((d) => ({ value: d, label: DIFFICULTY[d].label, color: DIFFICULTY[d].color }))}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Estimated minutes" htmlFor="q-min">
            <Input id="q-min" type="number" min={5} max={600} step={5} inputMode="numeric" value={form.estimated_minutes} onChange={(e) => setForm({ ...form, estimated_minutes: e.target.value })} />
          </Field>
          <Field label="Priority" htmlFor="q-priority">
            <Select id="q-priority" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value as Priority })}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </Select>
          </Field>
        </div>
        <Field label="Notes" htmlFor="q-notes" hint="Optional">
          <Textarea id="q-notes" maxLength={2000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>

        <div className={clsx("flex items-center gap-3 rounded-xl border px-4 py-3", form.difficulty === "legendary" ? "border-legendary/30 bg-legendary/[0.06]" : "border-line bg-white/[0.02]")}>
          <Sparkles className="size-5 text-xp" aria-hidden="true" />
          <div className="text-sm">
            <p>
              Base reward <span className="num font-semibold text-xp">{xp} XP</span>
            </p>
            <p className="text-xs text-faint">Streak and early-finish bonuses are added when you complete it.</p>
          </div>
        </div>

        {error ? <ErrorNote message={error} /> : null}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            {quest ? "Save changes" : "Create quest"}
          </Button>
        </div>
      </form>
  );
}
