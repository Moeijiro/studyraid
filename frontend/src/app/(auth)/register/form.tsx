"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorNote } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/field";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Errors = Partial<Record<"email" | "username" | "display_name" | "password", string>>;

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", username: "", display_name: "", password: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const validate = (): Errors => {
    const e: Errors = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Enter a valid email.";
    if (!/^[A-Za-z0-9_]{3,24}$/.test(form.username)) e.username = "3–24 letters, numbers or underscores.";
    if (!form.display_name.trim()) e.display_name = "What should we call you?";
    if (form.password.length < 10) e.password = "At least 10 characters.";
    return e;
  };

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setPending(true);
    setError(null);
    try {
      await register({ ...form, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC" });
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && Array.isArray(err.details)) {
        const fe: Errors = {};
        for (const d of err.details as { field: string; message: string }[]) fe[d.field as keyof Errors] = d.message;
        setErrors(fe);
      }
      setError(err instanceof ApiError ? err.message : "Can't reach the server.");
    } finally {
      setPending(false);
    }
  };

  const bind = (k: keyof typeof form) => ({
    value: form[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value }),
    "aria-invalid": !!errors[k],
  });

  return (
    <div className="w-full max-w-sm animate-rise">
      <h1 className="font-display text-3xl font-bold">Start your run</h1>
      <p className="mt-2 text-sm text-muted">Create an account. Your first quest is one click away.</p>
      <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
        <Field label="Display name" htmlFor="display_name" error={errors.display_name}>
          <Input id="display_name" autoComplete="nickname" {...bind("display_name")} />
        </Field>
        <Field label="Username" htmlFor="username" error={errors.username} hint="Friends invite you by this.">
          <Input id="username" autoComplete="username" {...bind("username")} />
        </Field>
        <Field label="Email" htmlFor="email" error={errors.email}>
          <Input id="email" type="email" autoComplete="email" {...bind("email")} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password}>
          <Input id="password" type="password" autoComplete="new-password" {...bind("password")} />
        </Field>
        {error ? <ErrorNote message={error} /> : null}
        <Button type="submit" size="lg" className="w-full" loading={pending}>
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        Already raiding?{" "}
        <Link href="/login" className="font-medium text-brand hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
