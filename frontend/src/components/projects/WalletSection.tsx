"use client";

// Project wallet: the balance, deposits and every payout from it.
// Only shown to users with projects.view_wallet.

import { Plus } from "lucide-react";
import { useState } from "react";
import { Can } from "@/components/Can";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/ui/Card";
import { Input } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { Table, Td } from "@/components/ui/Table";
import { api } from "@/lib/api";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";
import { notify } from "@/lib/notify";
import type { Project, WalletTransaction } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useForm } from "@/lib/useForm";

interface WalletSectionProps {
  project: Project;
  onChange: () => void; // reload the project after a deposit
}

/** Wallet balance, a deposit button and every wallet transaction. */
export function WalletSection({ project, onChange }: WalletSectionProps) {
  const [depositing, setDepositing] = useState(false);
  const { data: transactions, error, loading, reload } = useApi<WalletTransaction[]>(
    `/projects/${project.id}/wallet/transactions`,
  );

  return (
    <Card
      title="Wallet"
      description="Money available to pay for works on this project."
      actions={
        <Can permission="projects.fund_wallet">
          <Button size="sm" onClick={() => setDepositing(true)}>
            <Plus className="size-4" aria-hidden />
            Add funds
          </Button>
        </Can>
      }
    >
      <div className="mb-4 max-w-xs">
        <Stat label="Balance" value={formatMoney(project.wallet_balance)} />
      </div>

      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {transactions && transactions.length === 0 && <EmptyState title="No transactions yet" />}
      {transactions && transactions.length > 0 && (
        <Table headers={["Date", "Type", "Amount", "Balance after", "Reference"]}>
          {transactions.map((item) => (
            <tr key={item.id}>
              <Td>{formatDateTime(item.created_at)}</Td>
              <Td>
                <Badge tone={item.transaction_type === "deposit" ? "green" : "gray"}>
                  {humanize(item.transaction_type)}
                </Badge>
              </Td>
              <Td className="font-medium">{formatMoney(item.amount)}</Td>
              <Td>{formatMoney(item.balance_after)}</Td>
              <Td className="max-w-xs truncate">{item.reference || "-"}</Td>
            </tr>
          ))}
        </Table>
      )}

      <Modal open={depositing} onClose={() => setDepositing(false)} title="Add funds">
        <DepositForm
          projectId={project.id}
          onCancel={() => setDepositing(false)}
          onDone={() => {
            setDepositing(false);
            reload();
            onChange();
          }}
        />
      </Modal>
    </Card>
  );
}

interface DepositFormProps {
  projectId: string;
  onCancel: () => void;
  onDone: () => void;
}

/** Form to add money to the project wallet. */
function DepositForm({ projectId, onCancel, onDone }: DepositFormProps) {
  const [busy, setBusy] = useState(false);
  const form = useForm({ amount: "", reference: "" });

  /** Record the deposit (POST /projects/{id}/wallet/deposits). */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const result = await notify(
      api.post(`/projects/${projectId}/wallet/deposits`, form.values),
      `${formatMoney(form.values.amount)} added to the wallet`,
    );
    setBusy(false);
    if (result) {
      onDone();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Amount (KES)"
        type="number"
        min="1"
        step="0.01"
        required
        inputMode="decimal"
        {...form.field("amount")}
      />
      <Input
        label="Reference"
        placeholder="e.g. bank transfer number"
        hint="Optional, helps to trace the deposit later"
        {...form.field("reference")}
      />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy}>
          Add funds
        </Button>
      </div>
    </form>
  );
}
