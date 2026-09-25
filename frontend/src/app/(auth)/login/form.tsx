"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorNote } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/field";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Info = { demo: { email: string; password: string } | null; registration: boolean };

function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export function LoginForm() {
  const { login, status } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [info, setInfo] = useState<Info | null>(null);
  const next = safeNext(params.get("next"));

  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, router, next]);

  useEffect(() => {
    fetch("/api/system/info")
      .then((r) => (r.ok ? r.json() : null))
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  const submit = async (e: React.FormEvent, creds?: { email: string; password: string }) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login(creds?.email ?? email, creds?.password ?? password);
      router.replace(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Can't reach the server. Is the API running on :8000?");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="w-full max-w-sm animate-rise">
      <h1 className="font-display text-3xl font-bold">Welcome back</h1>
      <p className="mt-2 text-sm text-muted">Sign in to continue your run.</p>

      {info?.demo ? (
        <button
          type="button"
          onClick={(e) => submit(e, info.demo!)}
          disabled={pending}
          className="panel panel-hover mt-6 flex w-full items-center gap-3 p-4 text-left"
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <Sparkles className="size-5" />
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-semibold">Enter the demo</span>
            <span className="block truncate text-xs text-muted">
              {info.demo.email} · {info.demo.password}
            </span>
          </span>
        </button>
      ) : null}

      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <Field label="Email" htmlFor="email">
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" htmlFor="password">
          <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error ? <ErrorNote message={error} /> : null}
        <Button type="submit" size="lg" className="w-full" loading={pending}>
          Sign in
        </Button>
      </form>
      {info?.registration !== false ? (
        <p className="mt-6 text-center text-sm text-muted">
          New here?{" "}
          <Link href="/register" className="font-medium text-brand hover:underline">
            Create an account
          </Link>
        </p>
      ) : null}
    </div>
  );
}
