"use client";

import clsx from "clsx";
import { CircleCheck, Plus, ScrollText, Search, Swords } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { QuestCard } from "@/components/quests/quest-card";
import { QuestDialog } from "@/components/quests/quest-dialog";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorNote, Skeleton } from "@/components/ui/card";
import { Input, Segmented, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { num } from "@/lib/format";
import { useResource } from "@/lib/store";
import type { Quest } from "@/lib/types";

type Page = { items: Quest[]; total: number };
type Column = "planned" | "active" | "done";

function query(statuses: string[], search: string, subject: string, limit = 100) {
  const p = new URLSearchParams();
  statuses.forEach((s) => p.append("status", s));
  if (search) p.set("search", search);
  if (subject) p.set("subject", subject);
  p.set("limit", String(limit));
  return `/api/quests?${p}`;
}

export default function QuestsPage() {
  const [dialog, setDialog] = useState<{ open: boolean; quest?: Quest | null }>({ open: false });
  const [search, setSearch] = useState("");
  const [subject, setSubject] = useState("");
  const [tab, setTab] = useState<Column>("planned");
  const q = useDeferredValue(search.trim());

  const planned = useResource<Page>(query(["planned"], q, subject));
  const active = useResource<Page>(query(["active"], q, subject));
  const done = useResource<Page>(query(["completed", "failed", "expired"], q, subject, 12));
  const { data: subjects } = useResource<string[]>("/api/quests/subjects");

  const openTotal = (planned.data?.total ?? 0) + (active.data?.total ?? 0);
  const edit = (quest: Quest) => setDialog({ open: true, quest });

  const columns: { id: Column; title: string; icon: React.ReactNode; res: typeof planned; empty: string }[] = [
    { id: "planned", title: "Planned", icon: <ScrollText className="size-4" />, res: planned, empty: "Plan your next quest." },
    { id: "active", title: "In progress", icon: <Swords className="size-4" />, res: active, empty: "Start a quest to see it here." },
    { id: "done", title: "Recently closed", icon: <CircleCheck className="size-4" />, res: done, empty: "Completed quests land here." },
  ];

  return (
    <div>
      <title>Quests · StudyRaid</title>
      <PageHeader
        title="Quest board"
        subtitle={`${num(openTotal)} open quests. Rewards are set by difficulty and effort; bonuses for streaks and early finishes.`}
        action={
          <Button onClick={() => setDialog({ open: true, quest: null })}>
            <Plus className="size-4" /> New quest
          </Button>
        }
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-faint" aria-hidden="true" />
          <Input aria-label="Search quests" placeholder="Search quests" className="pl-10" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select aria-label="Filter by subject" className="sm:w-56" value={subject} onChange={(e) => setSubject(e.target.value)}>
          <option value="">All subjects</option>
          {(subjects ?? []).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <div className="lg:hidden">
          <Segmented
            label="Column"
            value={tab}
            onChange={setTab}
            options={columns.map((c) => ({ value: c.id, label: `${c.title} ${c.res.data ? c.res.data.total : ""}` }))}
          />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {columns.map((c) => (
          <section key={c.id} aria-labelledby={`col-${c.id}`} className={clsx("min-w-0", tab !== c.id && "hidden lg:block")}>
            <h2 id={`col-${c.id}`} className="mb-3 flex items-center gap-2 px-1 text-[13px] font-semibold tracking-wide text-muted uppercase">
              <span className="text-faint">{c.icon}</span>
              {c.title}
              <span className="num ml-auto rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[11px] text-faint">{c.res.data?.total ?? "·"}</span>
            </h2>
            {c.res.error ? <ErrorNote message={c.res.error.message} onRetry={c.res.reload} /> : null}
            {c.res.loading ? (
              <div className="space-y-3">
                <Skeleton className="h-36 rounded-[1.125rem]" />
                <Skeleton className="h-36 rounded-[1.125rem]" />
              </div>
            ) : c.res.data?.items.length ? (
              <div className="space-y-3">
                {c.res.data.items.map((quest) => (
                  <QuestCard key={quest.id} quest={quest} onEdit={edit} />
                ))}
              </div>
            ) : (
              <div className="rounded-[1.125rem] border border-dashed border-line-2">
                <EmptyState title={q || subject ? "No matches" : "Empty"} body={q || subject ? "Try another search or subject." : c.empty} />
              </div>
            )}
          </section>
        ))}
      </div>
      <QuestDialog open={dialog.open} quest={dialog.quest} onClose={() => setDialog({ open: false })} />
    </div>
  );
}
