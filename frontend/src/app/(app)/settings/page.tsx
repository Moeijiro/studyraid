"use client";

import { Snowflake } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar, CoinCount } from "@/components/game/bits";
import { useToasts } from "@/components/game/toasts";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, ErrorNote } from "@/components/ui/card";
import { Field, Input, Select, Switch } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TIMEZONES } from "@/lib/game";
import { invalidate, useResource } from "@/lib/store";
import type { Summary, User } from "@/lib/types";

export default function SettingsPage() {
  const { user } = useAuth();
  if (!user) return null;
  return <Settings key={user.id} user={user} />;
}

function Settings({ user }: { user: User }) {
  const { setUser, logout } = useAuth();
  const router = useRouter();
  const { data: s } = useResource<Summary>("/api/me/summary");
  const { push } = useToasts();
  const [name, setName] = useState(user.display_name);
  const [tz, setTz] = useState(user.timezone);
  const [hue, setHue] = useState(user.avatar_hue);
  const [visible, setVisible] = useState(user.show_on_leaderboards);
  const [pw, setPw] = useState({ current: "", next: "" });
  const [pwError, setPwError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const u = await patch<User>("/api/me", { display_name: name, timezone: tz, avatar_hue: hue, show_on_leaderboards: visible });
      setUser(u);
      invalidate("/api/me", "/api/leaderboards", "/api/parties");
      push({ kind: "info", title: "Profile saved" });
    } catch (err) {
      push({ kind: "error", title: err instanceof ApiError ? err.message : "Couldn't save." });
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError(null);
    try {
      await post("/api/me/password", { current_password: pw.current, new_password: pw.next });
      setPw({ current: "", next: "" });
      push({ kind: "info", title: "Password changed", body: "Other devices have been signed out." });
    } catch (err) {
      setPwError(err instanceof ApiError ? err.message : "Couldn't change the password.");
    }
  };

  const buyFreeze = async () => {
    try {
      await post("/api/me/streak-freeze");
      invalidate("/api/me/summary");
      push({ kind: "info", title: "Streak freeze ready", body: "It will cover the next day you miss." });
    } catch (err) {
      push({ kind: "error", title: err instanceof ApiError ? err.message : "Couldn't buy it." });
    }
  };

  return (
    <div className="max-w-3xl">
      <title>Settings · StudyRaid</title>
      <PageHeader title="Settings" />
      <div className="space-y-5">
        <Card>
          <CardHeader title="Profile" />
          <form onSubmit={save} className="space-y-4 px-5 pb-5">
            <div className="flex items-center gap-4">
              <Avatar name={name || user.display_name} hue={hue} size={56} />
              <div className="flex-1">
                <label htmlFor="hue" className="text-[13px] font-medium text-muted">
                  Avatar color
                </label>
                <input id="hue" type="range" min={0} max={359} value={hue} onChange={(e) => setHue(Number(e.target.value))} className="mt-2 w-full accent-[#8f7cff]" />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Display name" htmlFor="s-name">
                <Input id="s-name" maxLength={40} value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <Field label="Time zone" htmlFor="s-tz" hint="Streak days follow this calendar.">
                <Select id="s-tz" value={tz} onChange={(e) => setTz(e.target.value)}>
                  {(TIMEZONES.includes(tz) ? TIMEZONES : [tz, ...TIMEZONES]).map((z) => (
                    <option key={z} value={z}>
                      {z}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <div className="flex items-center justify-between gap-4 rounded-xl border border-line bg-white/[0.02] p-4">
              <div>
                <p className="text-sm font-medium">Show me on leaderboards</p>
                <p className="text-xs text-faint">Party-mates see your weekly XP. Turn it off to study privately; you still see your own rank.</p>
              </div>
              <Switch checked={visible} onChange={setVisible} label="Show me on leaderboards" />
            </div>
            <Button type="submit" loading={saving}>
              Save profile
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title="Streak freeze" icon={<Snowflake className="size-4" />} />
          <div className="flex flex-wrap items-center gap-4 px-5 pb-5">
            <p className="flex-1 text-sm text-muted">
              A freeze covers one missed day, so the streak survives it. It costs 150 coins and you can hold two. You have <span className="font-semibold text-fg">{s?.streak.freezes ?? 0}</span>.
            </p>
            <div className="flex items-center gap-3">
              {s ? <CoinCount coins={s.coins} /> : null}
              <Button variant="secondary" onClick={buyFreeze} disabled={!s || s.coins < 150 || s.streak.freezes >= 2}>
                Buy for 150
              </Button>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Password" />
          <form onSubmit={changePassword} className="grid gap-4 px-5 pb-5 sm:grid-cols-2">
            <Field label="Current password" htmlFor="pw-current">
              <Input id="pw-current" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
            </Field>
            <Field label="New password" htmlFor="pw-next" hint="At least 10 characters">
              <Input id="pw-next" type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
            </Field>
            {pwError ? (
              <div className="sm:col-span-2">
                <ErrorNote message={pwError} />
              </div>
            ) : null}
            <div className="sm:col-span-2">
              <Button type="submit" variant="secondary" disabled={!pw.current || pw.next.length < 10}>
                Change password
              </Button>
            </div>
          </form>
        </Card>

        <Button
          variant="danger"
          onClick={async () => {
            await logout();
            router.replace("/login");
          }}
        >
          Sign out
        </Button>
      </div>
    </div>
  );
}
