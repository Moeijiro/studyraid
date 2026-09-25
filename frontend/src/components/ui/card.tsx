import clsx from "clsx";

export function Card({ className, children, as: Tag = "section", ...rest }: React.HTMLAttributes<HTMLElement> & { as?: "section" | "div" | "article" | "li" }) {
  return (
    <Tag className={clsx("panel", className)} {...rest}>
      {children}
    </Tag>
  );
}

export function CardHeader({ title, icon, action, subtitle }: { title: React.ReactNode; icon?: React.ReactNode; action?: React.ReactNode; subtitle?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 px-5 pt-4 pb-3">
      <div className="min-w-0">
        <h2 className="flex items-center gap-2 text-[13px] font-semibold tracking-wide text-muted uppercase">
          {icon ? <span className="text-faint">{icon}</span> : null}
          {title}
        </h2>
        {subtitle ? <p className="mt-1 text-xs text-faint">{subtitle}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded-lg bg-white/[0.05]", className)} aria-hidden="true" />;
}

export function EmptyState({ icon, title, body, action }: { icon?: React.ReactNode; title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      {icon ? <div className="mb-3 flex size-11 items-center justify-center rounded-2xl border border-line bg-white/[0.03] text-faint">{icon}</div> : null}
      <p className="font-medium">{title}</p>
      {body ? <p className="mt-1 max-w-xs text-sm text-muted">{body}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-danger/25 bg-danger/[0.07] px-4 py-3 text-sm text-danger">
      <span>{message}</span>
      {onRetry ? (
        <button onClick={onRetry} className="shrink-0 underline underline-offset-4">
          Retry
        </button>
      ) : null}
    </div>
  );
}
