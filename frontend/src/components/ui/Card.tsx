interface CardProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

/** White box with an optional title row. Most page sections are cards. */
export function Card({ title, description, actions, className = "", children }: CardProps) {
  return (
    <section className={`rounded-xl border border-zinc-200 bg-white ${className}`}>
      {(title || actions) && (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-100 px-4 py-3 sm:px-5">
          <div>
            {title && <h2 className="font-semibold text-zinc-900">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-zinc-500">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

interface StatProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
}

/** A small labelled number, e.g. "Wallet balance  KES 50,000.00". */
export function Stat({ label, value, hint }: StatProps) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-zinc-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-zinc-500">{hint}</p>}
    </div>
  );
}
