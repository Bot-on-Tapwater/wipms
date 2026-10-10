"use client";

// Paying for a work:
//   1. someone requests payment,
//   2. the contractor supervisor and the main contractor both approve,
//   3. labourers and the subcontractor are paid from the project wallet,
//   4. later the subcontractor's retention money is requested and released.

import { Check, Circle } from "lucide-react";
import { toast } from "sonner";
import { ActionButton } from "@/components/ui/ActionButton";
import { Card, Stat } from "@/components/ui/Card";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { PaymentRecordsTable } from "@/components/payments/PaymentRecordsTable";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { PaymentOutcome, PaymentRecord, PaymentSummary, Work } from "@/lib/types";
import { useApi } from "@/lib/useApi";

interface PaymentsTabProps {
  work: Work;
  onChange: (work: Work) => void;
}

/** Payment steps of a work, its money summary and its payment records. */
export function PaymentsTab({ work, onChange }: PaymentsTabProps) {
  const { can } = useAuth();
  const canView = can("payments.view");
  const summary = useApi<PaymentSummary>(canView ? `/works/${work.id}/payment-summary` : null);
  const records = useApi<PaymentRecord[]>(canView ? "/payments/records" : null, { work_id: work.id });

  /** Pass the updated work up and reload the summary and records. */
  function handleWorkUpdated(updated: Work) {
    onChange(updated);
    summary.reload();
    records.reload();
  }

  /** Warn about failed payments after a payout, then refresh. */
  function handlePayoutDone(outcome: PaymentOutcome) {
    if (outcome.payments_failed > 0) {
      toast.warning(`${outcome.payments_failed} payment(s) failed. Use "Retry failed payments" to try again.`);
    }
    handleWorkUpdated(outcome.work);
  }

  const pending = work.payment_status === "pending";
  const waitingForApproval = pending && work.payment_requested;
  const hasSubcontractor = work.assigned_subcontractor !== null;

  const steps = [
    { label: "Payment requested", done: work.payment_requested || !pending, when: work.payment_requested_at },
    { label: "Approved by contractor supervisor", done: work.contractor_supervisor_payment_approval || !pending },
    { label: "Approved by main contractor", done: work.main_contractor_payment_approval || !pending },
    { label: "Paid out", done: work.payment_status === "paid", when: work.payment_completed_at },
  ];
  if (hasSubcontractor) {
    steps.push(
      { label: "Retention requested", done: work.retention_payment_requested || work.retention_paid },
      { label: "Retention paid", done: work.retention_paid },
    );
  }

  const approveWarning = "Once both payment approvals are given, money is sent from the project wallet straight away.";

  return (
    <div className="space-y-6">
      <Card title="Payment progress">
        <ol className="space-y-3">
          {steps.map((step) => (
            <li key={step.label} className="flex items-center gap-3 text-sm">
              {step.done ? (
                <Check className="size-5 rounded-full bg-emerald-100 p-0.5 text-emerald-700" aria-hidden />
              ) : (
                <Circle className="size-5 text-zinc-300" aria-hidden />
              )}
              <span className={step.done ? "text-zinc-900" : "text-zinc-500"}>{step.label}</span>
              {step.done && step.when && <span className="text-xs text-zinc-400">{formatDateTime(step.when)}</span>}
            </li>
          ))}
        </ol>

        {work.payment_status === "approved" && (
          <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Some payments failed. They can be retried once the problem (for example the phone number) is fixed.
          </p>
        )}

        <div className="mt-5 flex flex-wrap gap-2">
          {pending && !work.payment_requested && can("payments.request") && (
            <ActionButton
              action={() => api.post<Work>(`/works/${work.id}/payment-request`)}
              success="Payment requested"
              onDone={handleWorkUpdated}
            >
              Request payment
            </ActionButton>
          )}
          {waitingForApproval &&
            !work.contractor_supervisor_payment_approval &&
            can("payments.approve_as_contractor_supervisor") && (
              <ActionButton
                confirm={approveWarning}
                confirmLabel="Approve payment"
                action={() =>
                  api.post<PaymentOutcome>(`/works/${work.id}/payment-approvals`, {
                    approval_type: "contractor_supervisor",
                  })
                }
                success={(outcome) => outcome.message}
                onDone={handlePayoutDone}
              >
                Approve payment (contractor supervisor)
              </ActionButton>
            )}
          {waitingForApproval &&
            !work.main_contractor_payment_approval &&
            can("payments.approve_as_main_contractor") && (
              <ActionButton
                confirm={approveWarning}
                confirmLabel="Approve payment"
                action={() =>
                  api.post<PaymentOutcome>(`/works/${work.id}/payment-approvals`, {
                    approval_type: "main_contractor",
                  })
                }
                success={(outcome) => outcome.message}
                onDone={handlePayoutDone}
              >
                Approve payment (main contractor)
              </ActionButton>
            )}
          {work.payment_status === "approved" && can("payments.approve_as_main_contractor") && (
            <ActionButton
              confirm="Retry every failed payment for this work?"
              confirmLabel="Retry"
              action={() => api.post<PaymentOutcome>(`/works/${work.id}/payments/retry`)}
              success={(outcome) => outcome.message}
              onDone={handlePayoutDone}
            >
              Retry failed payments
            </ActionButton>
          )}
          {hasSubcontractor &&
            work.payment_status === "paid" &&
            !work.retention_payment_requested &&
            !work.retention_paid &&
            can("payments.request_retention") && (
              <ActionButton
                variant="secondary"
                action={() => api.post<Work>(`/works/${work.id}/retention-request`)}
                success="Retention money requested"
                onDone={handleWorkUpdated}
              >
                Request retention money
              </ActionButton>
            )}
          {work.retention_payment_requested && !work.retention_paid && can("payments.approve_retention") && (
            <ActionButton
              confirm="Pay the retention money to the subcontractor from the project wallet?"
              confirmLabel="Pay retention"
              action={() => api.post<PaymentOutcome>(`/works/${work.id}/retention-approval`)}
              success={(outcome) => outcome.message}
              onDone={handlePayoutDone}
            >
              Approve retention payment
            </ActionButton>
          )}
        </div>
      </Card>

      {canView && (
        <Card title="Breakdown" description="Who gets what from the total cost.">
          {summary.loading && <Loading />}
          {summary.error && <ErrorState message={summary.error} onRetry={summary.reload} />}
          {summary.data && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Stat label="Total cost" value={formatMoney(summary.data.total_cost)} />
              <Stat label="Due to labourers" value={formatMoney(summary.data.total_labour_due)} />
              <Stat
                label="Due to subcontractor"
                value={formatMoney(summary.data.subcontractor_amount)}
                hint="Total cost minus labour and retention"
              />
              <Stat label="Retention money" value={formatMoney(summary.data.retention_money)} hint="Held back, released later" />
              <Stat label="Paid to labourers so far" value={formatMoney(summary.data.total_labourers_paid_out)} />
              <Stat
                label="Wallet money available"
                value={formatMoney(summary.data.usable_wallet_balance)}
                hint="Usable share of the project wallet"
              />
            </div>
          )}
        </Card>
      )}

      {canView && (
        <Card title="Payment records">
          {records.loading && <Loading />}
          {records.error && <ErrorState message={records.error} onRetry={records.reload} />}
          {records.data && records.data.length === 0 && <EmptyState title="No payments sent yet" />}
          {records.data && records.data.length > 0 && <PaymentRecordsTable records={records.data} />}
        </Card>
      )}
    </div>
  );
}
