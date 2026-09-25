"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Check, Copy, LogOut, Plus, RotateCcw, Trophy, UserPlus } from "lucide-react";
import { useState } from "react";
import { Avatar } from "@/components/game/bits";
import { NamedIcon } from "@/components/game/icons";
import { ChallengeCard } from "@/components/party/challenge-card";
import { ChallengeDialog } from "@/components/party/party-dialogs";
import { Leaderboard } from "@/components/party/leaderboard";
import { useToasts } from "@/components/game/toasts";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, EmptyState, ErrorNote, Skeleton } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { ApiError, post } from "@/lib/api";
import { minutesLabel, num, relative } from "@/lib/format";
import { useRealtime } from "@/lib/realtime";
import { invalidate, useResource } from "@/lib/store";
import type { PartyDetail } from "@/lib/types";

export default function PartyPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: p, error, reload } = useResource<PartyDetail>(`/api/parties/${id}`);
  const [challengeOpen, setChallengeOpen] = useState(false);
  const [invitee, setInvitee] = useState("");
  const [copied, setCopied] = useState(false);
  const [pulse, setPulse] = useState<string | null>(null);
  const { push } = useToasts();
  const live = useRealtime((e) => {
    if (e.type === "party_activity") setPulse(`${e.display_name} just made progress`);
    if (e.type === "challenge_progress" && String(e.party_id) === id) setPulse("Challenge progress updated");
  });

  if (error && !p) return <ErrorNote message={error.status === 404 ? "This party doesn't exist or you're not a member." : error.message} onRetry={reload} />;
  if (!p) return <Skeleton className="h-96 rounded-[1.125rem]" />;
  const owner = p.role === "owner";

  const invite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await post(`/api/parties/${p.id}/invites`, { username: invitee.trim() });
      push({ kind: "info", title: `Invite sent to @${invitee.trim()}` });
      setInvitee("");
    } catch (err) {
      push({ kind: "error", title: err instanceof ApiError ? err.message : "Couldn't send the invite." });
    }
  };
  const copy = async () => {
    if (!p.invite_code) return;
    await navigator.clipboard?.writeText(p.invite_code).catch(() => undefined);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  const rotate = async () => {
    await post(`/api/parties/${p.id}/invite-code`);
    invalidate(`/api/parties/${p.id}`);
  };
  const leave = async () => {
    if (!window.confirm(owner && p.member_count > 1 ? "Leave the party? Leadership passes to the longest-standing member." : "Leave the party?")) return;
    await post(`/api/parties/${p.id}/leave`);
    invalidate("/api/parties", "/api/me/summary");
    router.push("/party");
  };

  return (
    <div>
      <title>{`${p.name} · StudyRaid`}</title>
      <Link href="/party" className="text-sm text-muted hover:text-fg">
        ← Parties
      </Link>

      <section className="panel relative mt-4 overflow-hidden p-5 sm:p-7">
        <div className="pointer-events-none absolute -top-24 right-0 size-80 rounded-full blur-3xl" style={{ background: `oklch(0.5 0.14 ${p.hue} / 0.18)` }} aria-hidden="true" />
        <div className="relative flex flex-wrap items-center gap-5">
          <span className="flex size-16 items-center justify-center rounded-2xl" style={{ background: `oklch(0.5 0.13 ${p.hue} / 0.25)`, color: `oklch(0.84 0.12 ${p.hue})`, boxShadow: `inset 0 0 0 1px oklch(0.7 0.12 ${p.hue} / 0.4)` }}>
            <NamedIcon name={p.icon} className="size-8" />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-2xl font-bold sm:text-3xl">{p.name}</h1>
            <p className="mt-1 text-sm text-muted">{p.description}</p>
          </div>
          <dl className="grid w-full grid-cols-3 gap-3 sm:w-auto">
            {[
              ["Members", String(p.member_count)],
              ["XP this week", num(p.weekly_xp)],
              ["Party XP", num(p.party_xp)],
            ].map(([k, v]) => (
              <div key={k} className="rounded-2xl border border-line bg-white/[0.02] px-4 py-3">
                <dt className="text-[11px] text-faint">{k}</dt>
                <dd className="font-display num text-lg font-bold">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <div className="mt-5 grid gap-5 lg:grid-cols-12">
        <div className="min-w-0 space-y-5 lg:col-span-8">
          <Card>
            <CardHeader
              title="Challenges"
              icon={<Trophy className="size-4" />}
              action={
                owner ? (
                  <Button size="sm" variant="secondary" onClick={() => setChallengeOpen(true)} disabled={p.challenges.length >= 3}>
                    <Plus className="size-3.5" /> New challenge
                  </Button>
                ) : null
              }
            />
            <div className="space-y-3 px-5 pb-5">
              {p.challenges.length ? (
                p.challenges.map((c) => <ChallengeCard key={c.id} ch={c} />)
              ) : (
                <EmptyState title="No challenge running" body={owner ? "Set a shared goal for the week." : "The party leader can start one."} />
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="Contribution this week" subtitle={`Since ${new Date(p.week_starts_at).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}`} />
            <ul className="px-3 pb-4">
              {p.members.map((m) => (
                <li key={m.user_id} className="flex items-center gap-3 rounded-xl px-2 py-2.5">
                  <Avatar name={m.display_name} hue={m.avatar_hue} size={34} />
                  <div className="w-28 min-w-0 sm:w-36">
                    <p className="truncate text-sm font-medium">
                      {m.display_name} {m.role === "owner" ? <span className="ml-1 text-[11px] text-xp">Leader</span> : null}
                    </p>
                    <p className="num truncate text-[11px] text-faint">
                      {m.weekly_quests} quests · {minutesLabel(m.weekly_focus_minutes)}
                    </p>
                  </div>
                  <div className="h-2 min-w-10 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
                    <div className="fill-xp h-full rounded-full" style={{ width: `${m.weekly_share * 100}%` }} />
                  </div>
                  <p className="num w-20 text-right text-sm">
                    <span className="font-semibold">{num(m.weekly_xp)}</span> <span className="text-xs text-faint">XP</span>
                  </p>
                </li>
              ))}
            </ul>
          </Card>

          {p.past_challenges.length ? (
            <Card>
              <CardHeader title="Past challenges" />
              <div className="grid gap-3 px-5 pb-5 sm:grid-cols-2">
                {p.past_challenges.map((c) => (
                  <ChallengeCard key={c.id} ch={c} compact />
                ))}
              </div>
            </Card>
          ) : null}
        </div>

        <div className="min-w-0 space-y-5 lg:col-span-4">
          <Card>
            <CardHeader
              title="Live activity"
              action={
                <span className="flex items-center gap-1.5 text-[11px] text-faint">
                  <span className={`size-1.5 rounded-full ${live ? "animate-pulse bg-ok" : "bg-faint"}`} /> {live ? "Live" : "Offline"}
                </span>
              }
            />
            {pulse ? <p className="mx-5 mb-2 rounded-lg bg-brand/10 px-3 py-2 text-xs text-brand">{pulse}</p> : null}
            <ul className="max-h-[340px] overflow-y-auto px-3 pb-4">
              {p.activity.map((a) => (
                <li key={a.id} className="flex items-start gap-3 rounded-xl px-2 py-2">
                  <Avatar name={a.display_name} hue={a.avatar_hue} size={26} />
                  <p className="min-w-0 flex-1 text-sm">
                    <span className="font-medium">{a.display_name}</span> <span className="text-muted">{a.text}</span>
                    <span className="block text-[11px] text-faint">{relative(a.at)}</span>
                  </p>
                  {a.xp ? <span className="num shrink-0 text-xs font-semibold text-xp">+{a.xp}</span> : null}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <CardHeader title="Leaderboard" />
            <Leaderboard scope={String(p.id)} />
          </Card>

          <Card className="p-5">
            <p className="text-[13px] font-semibold tracking-wide text-muted uppercase">Invite</p>
            <form onSubmit={invite} className="mt-3 flex gap-2">
              <Input aria-label="Username to invite" placeholder="username" value={invitee} onChange={(e) => setInvitee(e.target.value)} />
              <Button type="submit" variant="secondary" disabled={invitee.trim().length < 3} aria-label="Send invite">
                <UserPlus className="size-4" />
              </Button>
            </form>
            {p.invite_code ? (
              <div className="mt-4">
                <p className="text-xs text-faint">Or share the invite code</p>
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 rounded-xl border border-line bg-bg-2 px-3 py-2.5 font-mono text-sm tracking-[0.25em]">{p.invite_code}</code>
                  <Button variant="ghost" onClick={copy} aria-label="Copy invite code">
                    {copied ? <Check className="size-4 text-ok" /> : <Copy className="size-4" />}
                  </Button>
                  <Button variant="ghost" onClick={rotate} aria-label="Generate a new code">
                    <RotateCcw className="size-4" />
                  </Button>
                </div>
              </div>
            ) : null}
            <button onClick={leave} className="mt-5 inline-flex items-center gap-2 text-xs text-faint hover:text-danger">
              <LogOut className="size-3.5" /> Leave party
            </button>
          </Card>
        </div>
      </div>
      {owner ? <ChallengeDialog open={challengeOpen} onClose={() => setChallengeOpen(false)} partyId={p.id} /> : null}
    </div>
  );
}
