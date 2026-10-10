import { CircleAlert, Inbox, LoaderCircle } from "lucide-react";
import { Button } from "./Button";

/** Spinner shown while data loads. */
export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-zinc-500">
      <LoaderCircle className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

/** Error message with an optional "Try again" button. */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <CircleAlert className="size-6 text-red-500" aria-hidden />
      <p className="text-sm text-zinc-600">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

/** Shown when a list has nothing in it yet. */
export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <Inbox className="size-6 text-zinc-400" aria-hidden />
      <p className="text-sm font-medium text-zinc-700">{title}</p>
      {children && <div className="text-sm text-zinc-500">{children}</div>}
    </div>
  );
}
