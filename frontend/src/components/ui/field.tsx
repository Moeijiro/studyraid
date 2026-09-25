import clsx from "clsx";
import { forwardRef, useId } from "react";

const control =
  "w-full rounded-xl border border-line-2 bg-bg-2 px-3.5 text-sm text-fg placeholder:text-faint transition-colors outline-none hover:border-white/20 focus:border-brand/70 focus:ring-2 focus:ring-brand/25 aria-[invalid=true]:border-danger/60";

export function Field({ label, hint, error, children, htmlFor }: { label: string; hint?: string; error?: string; children: React.ReactNode; htmlFor?: string }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-[13px] font-medium text-muted">
        {label}
      </label>
      {children}
      {error ? <p className="text-xs text-danger">{error}</p> : hint ? <p className="text-xs text-faint">{hint}</p> : null}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...rest }, ref) {
  return <input ref={ref} className={clsx(control, "h-11", className)} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...rest }, ref) {
  return <textarea ref={ref} className={clsx(control, "min-h-20 py-2.5", className)} {...rest} />;
});

export function Select({ className, children, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={clsx(control, "h-11 appearance-none bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 20 20%22 fill=%22%2374738a%22><path d=%22M5.5 7.5l4.5 4.5 4.5-4.5%22 stroke=%22%2374738a%22 stroke-width=%221.6%22 fill=%22none%22/></svg>')] bg-[length:18px] bg-[right_10px_center] bg-no-repeat pr-9", className)} {...rest}>
      {children}
    </select>
  );
}

/** Segmented control (radio group) for small option sets. */
export function Segmented<T extends string | number>({
  value,
  options,
  onChange,
  label,
  size = "md",
}: {
  value: T;
  options: { value: T; label: React.ReactNode; color?: string }[];
  onChange: (v: T) => void;
  label: string;
  size?: "sm" | "md";
}) {
  const id = useId();
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl border border-line bg-bg-2 p-1 scrollbar-none">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={String(o.value)}
            id={`${id}-${o.value}`}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={clsx(
              "shrink-0 rounded-lg font-medium transition-colors",
              size === "sm" ? "h-7 px-2.5 text-xs" : "h-8 px-3 text-[13px]",
              active ? "bg-panel-3 text-fg shadow-[inset_0_1px_0_rgb(255_255_255/0.06)]" : "text-muted hover:text-fg",
            )}
            style={active && o.color ? { color: o.color } : undefined}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={clsx("relative h-6 w-11 shrink-0 rounded-full border transition-colors", checked ? "border-brand/50 bg-brand/80" : "border-line-2 bg-white/[0.06]")}
    >
      <span className={clsx("absolute top-0.5 size-[18px] rounded-full bg-white shadow transition-transform", checked ? "translate-x-[22px]" : "translate-x-0.5")} />
    </button>
  );
}
