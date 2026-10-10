import type { PaymentStatus } from "@/lib/types";

type Tone = "gray" | "green" | "amber" | "red" | "blue";

const tones: Record<Tone, string> = {
  gray: "bg-zinc-100 text-zinc-700",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-red-50 text-red-700",
  blue: "bg-sky-50 text-sky-700",
};

/** Small coloured label, e.g. a status. */
export function Badge({ tone = "gray", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

const paymentTones: Record<PaymentStatus, Tone> = {
  pending: "amber",
  approved: "blue",
  paid: "green",
};

/** Payment status of a work: pending / approved (paying out) / paid. */
export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const label = status === "approved" ? "Paying out" : status.charAt(0).toUpperCase() + status.slice(1);
  return <Badge tone={paymentTones[status]}>{label}</Badge>;
}
