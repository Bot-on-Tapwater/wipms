"use client";

// Labourers on a work: who worked, for how many days and what they are owed.

import { Pencil, Plus, X } from "lucide-react";
import { useState } from "react";
import { LabourerAutocomplete } from "@/components/labourers/LabourerAutocomplete";
import { LabourerDetailFields, labourerValues } from "@/components/labourers/LabourerForm";
import { ActionButton } from "@/components/ui/ActionButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { Table, Td } from "@/components/ui/Table";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { choiceLabel, formatMoney } from "@/lib/format";
import { notify } from "@/lib/notify";
import type { LabourerSuggestion, Message, Work, WorkLabourer } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useChoices } from "@/lib/useChoices";
import { useForm } from "@/lib/useForm";

interface LabourersTabProps {
  work: Work;
  locked: boolean; // true once payment has been processed
}

/** The labourers on a work with their days worked and amount due. */
export function LabourersTab({ work, locked }: LabourersTabProps) {
  const { can } = useAuth();
  const { labourer_titles } = useChoices();
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<WorkLabourer | null>(null);
  const { data: rows, error, loading, reload } = useApi<WorkLabourer[]>(`/works/${work.id}/labourers`);

  const canManage = can("works.manage_labourers") && !locked;
  const totalDue = (rows || []).reduce((sum, row) => sum + Number(row.amount_due), 0);

  return (
    <Card
      title="Labourers"
      description="Amount due = daily rate x days worked + overhead."
      actions={
        canManage && (
          <Button size="sm" onClick={() => setAdding(true)}>
            <Plus className="size-4" aria-hidden />
            Add labourer
          </Button>
        )
      }
    >
      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {rows && rows.length === 0 && (
        <EmptyState title="No labourers on this work yet">
          {canManage ? "Add the people who worked on it so they can be paid." : undefined}
        </EmptyState>
      )}
      {rows && rows.length > 0 && (
        <>
          <Table
            headers={[
              "Name",
              "ID number",
              "Title",
              "Phone",
              "Daily rate",
              "Days",
              "Amount due",
              ...(canManage ? [""] : []),
            ]}
          >
            {rows.map((row) => (
              <tr key={row.labourer.id}>
                <Td className="font-medium text-zinc-900">{row.labourer.name}</Td>
                <Td>{row.labourer.national_id_number}</Td>
                <Td>{choiceLabel(labourer_titles, row.labourer.title)}</Td>
                <Td>{row.labourer.phone_number}</Td>
                <Td>{formatMoney(row.labourer.daily_rate)}</Td>
                <Td>{row.days_worked}</Td>
                <Td className="font-medium">{formatMoney(row.amount_due)}</Td>
                {canManage && (
                  <Td>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={`Change days for ${row.labourer.name}`}
                        onClick={() => setEditing(row)}
                      >
                        <Pencil className="size-4" aria-hidden />
                      </Button>
                      <ActionButton
                        variant="ghost"
                        size="sm"
                        aria-label={`Remove ${row.labourer.name}`}
                        confirm={`Remove ${row.labourer.name} from this work?`}
                        confirmLabel="Remove"
                        action={() => api.delete<Message>(`/works/${work.id}/labourers/${row.labourer.id}`)}
                        success={`${row.labourer.name} removed`}
                        onDone={reload}
                      >
                        <X className="size-4" aria-hidden />
                      </ActionButton>
                    </div>
                  </Td>
                )}
              </tr>
            ))}
          </Table>
          <p className="mt-4 text-right text-sm text-zinc-600">
            Total due to labourers: <span className="font-semibold text-zinc-900">{formatMoney(totalDue)}</span>
          </p>
        </>
      )}

      <Modal open={adding} onClose={() => setAdding(false)} title="Add labourer" wide>
        <AddLabourerForm
          workId={work.id}
          onCancel={() => setAdding(false)}
          onDone={() => {
            setAdding(false);
            reload();
          }}
        />
      </Modal>
      <Modal open={editing !== null} onClose={() => setEditing(null)} title="Change days worked">
        {editing && (
          <DaysForm
            workId={work.id}
            row={editing}
            onCancel={() => setEditing(null)}
            onDone={() => {
              setEditing(null);
              reload();
            }}
          />
        )}
      </Modal>
    </Card>
  );
}

const DAYS_HINT = "Between 1 and 366.";

interface AddLabourerFormProps {
  workId: string;
  onCancel: () => void;
  onDone: () => void;
}

/**
 * Typing a name or ID number suggests labourers already in the system.
 * Picking one adds that person; otherwise a new labourer is registered.
 */
function AddLabourerForm({ workId, onCancel, onDone }: AddLabourerFormProps) {
  const { labourer_titles } = useChoices();
  const [picked, setPicked] = useState<LabourerSuggestion | null>(null);
  const [busy, setBusy] = useState(false);
  const form = useForm({ ...labourerValues(), days_worked: "1" });

  /** Add the picked labourer, or register a new one and add them to the work. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const days_worked = Number(form.values.days_worked);
    const request = picked
      ? api.post<WorkLabourer>(`/works/${workId}/labourers`, { labourer_id: picked.id, days_worked })
      : api.post<WorkLabourer>(`/works/${workId}/labourers/new`, { ...form.values, days_worked });
    const added = await notify(request, (row) => `${row.labourer.name} added`);
    setBusy(false);
    if (added) {
      onDone();
    }
  }

  const daysInput = (
    <Input
      label="Days worked"
      type="number"
      min="1"
      max="366"
      step="1"
      required
      inputMode="numeric"
      hint={DAYS_HINT}
      {...form.field("days_worked")}
    />
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {picked ? (
        <>
          <div className="flex items-start justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
            <div className="text-sm">
              <p className="font-medium text-zinc-900">{picked.name}</p>
              <p className="text-zinc-600">
                ID {picked.national_id_number} · {choiceLabel(labourer_titles, picked.title)} · {picked.phone_number}
              </p>
              <p className="text-zinc-600">
                {formatMoney(picked.daily_rate)} per day · {formatMoney(picked.overhead_cost)} overhead
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setPicked(null)}>
              Change
            </Button>
          </div>
          {daysInput}
        </>
      ) : (
        <>
          <p className="text-sm text-zinc-500">
            Start typing a name or ID number to pick someone already registered, or fill in all
            fields to register a new labourer.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <LabourerAutocomplete
              label="Full name"
              required
              minLength={2}
              maxLength={100}
              onPick={setPicked}
              {...form.field("name")}
            />
            <LabourerAutocomplete
              label="National ID number"
              required
              inputMode="numeric"
              pattern="[0-9]{5,20}"
              title="5 to 20 digits"
              onPick={setPicked}
              {...form.field("national_id_number")}
            />
          </div>
          <LabourerDetailFields field={form.field} />
          {daysInput}
        </>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy}>
          {picked ? "Add to work" : "Register and add"}
        </Button>
      </div>
    </form>
  );
}

interface DaysFormProps {
  workId: string;
  row: WorkLabourer;
  onCancel: () => void;
  onDone: () => void;
}

/** Form to change how many days a labourer worked on the work. */
function DaysForm({ workId, row, onCancel, onDone }: DaysFormProps) {
  const [busy, setBusy] = useState(false);
  const form = useForm({ days_worked: String(row.days_worked) });

  /** Save the new number of days. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const saved = await notify(
      api.patch<WorkLabourer>(`/works/${workId}/labourers/${row.labourer.id}`, {
        days_worked: Number(form.values.days_worked),
      }),
      "Days worked updated",
    );
    setBusy(false);
    if (saved) {
      onDone();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-zinc-600">{row.labourer.name}</p>
      <Input
        label="Days worked"
        type="number"
        min="1"
        max="366"
        step="1"
        required
        inputMode="numeric"
        hint={DAYS_HINT}
        {...form.field("days_worked")}
      />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy}>
          Save
        </Button>
      </div>
    </form>
  );
}
