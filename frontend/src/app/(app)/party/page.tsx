"use client";

import Link from "next/link";
import { Plus, Swords, Ticket } from "lucide-react";
import { useState } from "react";
import { NamedIcon } from "@/components/game/icons";
import { ChallengeCard } from "@/components/party/challenge-card";
import { CreatePartyDialog } from "@/components/party/party-dialogs";
import { Leaderboard } from "@/components/party/leaderboard";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, EmptyState, ErrorNote, Skeleton } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError, post } from "@/lib/api";
import { num, relative } from "@/lib/format";
import { invalidate, useResource } from "@/lib/store";
import type { Invite, PartySummary } from "@/lib/types";

type Data = { parties: PartySummary[]; invites: Invite[]; icons: string[] };

export default function PartiesPage() {
  const { data, error, reload } = useResource<Data>("/api/parties");
  const [creating, setCreating] = useState(false);
  const [code, setCode] = useState("");
  const [joinError, setJoinError] = useState<string | null>(null);

  const join = async (e: React.FormEvent) => {
    e.preventDefault();
    setJoinError(null);
    try {
      await post("/api/parties/join", { code });
      setCode("");
      invalidate("/api/parties", "/api/me/summary");
    } catch (err) {
      setJoinError(err instanceof ApiError ? err.message : "Couldn't join.");
    }
  };

  const answer = async (inv: Invite, accept: boolean) => {
    await post(`/api/parties/invites/${inv.id}/${accept ? "accept" : "decline"}`);
    invalidate("/api/parties", "/api/me/summary", "/api/notifications");
  };

  return (
    <div>
      <title>Parties · StudyRaid</title>
      <PageHeader
        title="Parties"
        subtitle="Small groups working toward shared goals. Your own progress always comes first."
        action={
          <Button onClick={() => setCreating(true)}>
            <Plus className="size-4" /> Create party
          </Button>
        }
      />
      {error ? <ErrorNote message={error.message} onRetry={reload} /> : null}

      {data?.invites.length ? (
        <div className="mb-5 space-y-2">
          {data.invites.map((inv) => (
            <div key={inv.id} className="panel flex flex-wrap items-center gap-3 border-brand/25 p-4">
              <span className="flex size-10 items-center justify-center rounded-xl" style={{ background: `oklch(0.5 0.13 ${inv.party.hue} / 0.22)`, color: `oklch(0.8 0.12 ${inv.party.hue})` }}>
                <NamedIcon name={inv.party.icon} className="size-5" />
              </span>
              <p className="text-sm">
                <span className="font-semibold">{inv.from}</span> invited you to <span className="font-semibold">{inv.party.name}</span>
                <span className="ml-2 text-xs text-faint">{relative(inv.created_at)}</span>
              </p>
              <div className="ml-auto flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => answer(inv, false)}>
                  Decline
                </Button>
                <Button size="sm" onClick={() => answer(inv, true)}>
                  Join party
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-12">
        <div className="min-w-0 space-y-5 lg:col-span-8">
          {!data ? (
            <Skeleton className="h-64 rounded-[1.125rem]" />
          ) : data.parties.length ? (
            data.parties.map((p) => (
              <Card key={p.id} as="article" className="panel-hover p-5">
                <div className="flex items-center gap-4">
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl" style={{ background: `oklch(0.5 0.13 ${p.hue} / 0.22)`, color: `oklch(0.82 0.12 ${p.hue})` }}>
                    <NamedIcon name={p.icon} className="size-6" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h2 className="font-display truncate text-lg font-semibold">
                      <Link href={`/party/${p.id}`} className="hover:underline">
                        {p.name}
                      </Link>
                    </h2>
                    <p className="truncate text-sm text-muted">{p.description || "No motto yet."}</p>
                  </div>
                  <div className="hidden text-right sm:block">
                    <p className="font-display num text-xl font-bold">{num(p.weekly_xp)}</p>
                    <p className="text-xs text-faint">XP this week</p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-faint">
                  {p.member_count} members · you&apos;re {p.role === "owner" ? "the leader" : "a member"}
                </p>
                {p.active_challenge ? (
                  <div className="mt-4">
                    <ChallengeCard ch={p.active_challenge} compact />
                  </div>
                ) : null}
                <Link href={`/party/${p.id}`} className="mt-4 inline-block text-sm font-medium text-brand hover:underline">
                  Open party →
                </Link>
              </Card>
            ))
          ) : (
            <Card>
              <EmptyState
                icon={<Swords className="size-5" />}
                title="You're not in a party yet"
                body="Create one and invite friends by username, or join with an invite code."
                action={
                  <Button onClick={() => setCreating(true)}>
                    <Plus className="size-4" /> Create party
                  </Button>
                }
              />
            </Card>
          )}
        </div>

        <div className="min-w-0 space-y-5 lg:col-span-4">
          <Card>
            <CardHeader title="Join with a code" icon={<Ticket className="size-4" />} />
            <form onSubmit={join} className="space-y-3 px-5 pb-5">
              <Input aria-label="Invite code" placeholder="e.g. K7Q2M9XD" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} className="font-mono tracking-widest uppercase" maxLength={16} />
              {joinError ? <p className="text-xs text-danger">{joinError}</p> : null}
              <Button type="submit" variant="secondary" className="w-full" disabled={code.length < 6}>
                Join party
              </Button>
            </form>
          </Card>
          {data?.parties.length ? (
            <Card>
              <CardHeader title="Friends this week" subtitle="Everyone you share a party with" />
              <Leaderboard scope="friends" />
            </Card>
          ) : null}
        </div>
      </div>
      <CreatePartyDialog open={creating} onClose={() => setCreating(false)} icons={data?.icons ?? ["sword"]} />
    </div>
  );
}
