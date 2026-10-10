"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { notify } from "@/lib/notify";
import type { Labourer } from "@/lib/types";
import { useChoices } from "@/lib/useChoices";
import { useForm } from "@/lib/useForm";

/** Starting values for the labourer fields; spread into useForm(). */
export function labourerValues(labourer?: Labourer) {
  return {
    name: labourer?.name || "",
    national_id_number: labourer?.national_id_number || "",
    title: labourer?.title || "",
    phone_number: labourer?.phone_number || "",
    daily_rate: labourer?.daily_rate || "",
    overhead_cost: labourer?.overhead_cost || "0",
  };
}

type DetailName = "title" | "phone_number" | "daily_rate" | "overhead_cost";

interface LabourerDetailFieldsProps {
  // form.field from useForm()
  field: (name: DetailName) => {
    value: string;
    onChange: React.ChangeEventHandler<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>;
  };
}

/**
 * Title, phone and pay fields shared by the labourer form and the
 * "add labourer to work" form. Name and ID inputs are added by each form.
 */
export function LabourerDetailFields({ field }: LabourerDetailFieldsProps) {
  const { labourer_titles } = useChoices();
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Title"
          required
          options={labourer_titles}
          placeholder="Choose a title"
          {...field("title")}
        />
        <Input
          label="Phone number"
          required
          inputMode="numeric"
          pattern="254[0-9]{9}"
          placeholder="2547XXXXXXXX"
          title="254 followed by 9 digits"
          hint="Payments are sent to this number."
          {...field("phone_number")}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Daily rate (KES)"
          type="number"
          min="1"
          step="0.01"
          required
          inputMode="decimal"
          {...field("daily_rate")}
        />
        <Input
          label="Overhead cost (KES)"
          type="number"
          min="0"
          step="0.01"
          inputMode="decimal"
          hint="Paid once per work, on top of the daily rate."
          {...field("overhead_cost")}
        />
      </div>
    </>
  );
}

interface LabourerFormModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: (labourer: Labourer) => void;
  labourer?: Labourer; // set when editing
}

/** Register a labourer (POST /labourers) or edit one (PATCH /labourers/{id}). */
export function LabourerFormModal({ open, onClose, onSaved, labourer }: LabourerFormModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={labourer ? "Edit labourer" : "New labourer"}>
      <LabourerFormBody labourer={labourer} onCancel={onClose} onSaved={onSaved} />
    </Modal>
  );
}

interface LabourerFormBodyProps {
  labourer?: Labourer;
  onCancel: () => void;
  onSaved: (labourer: Labourer) => void;
}

/** The fields and buttons inside the labourer modal. */
function LabourerFormBody({ labourer, onCancel, onSaved }: LabourerFormBodyProps) {
  const [busy, setBusy] = useState(false);
  const form = useForm(labourerValues(labourer));

  /** Save the labourer and pass the saved record back. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    // The national ID number identifies the person, so it cannot be changed.
    const { national_id_number, ...changes } = form.values;
    const request = labourer
      ? api.patch<Labourer>(`/labourers/${labourer.id}`, changes)
      : api.post<Labourer>("/labourers", { ...changes, national_id_number });
    const saved = await notify(request, labourer ? "Labourer updated" : "Labourer registered");
    setBusy(false);
    if (saved) {
      onSaved(saved);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Full name" required minLength={2} maxLength={100} {...form.field("name")} />
        <Input
          label="National ID number"
          required
          disabled={Boolean(labourer)}
          inputMode="numeric"
          pattern="[0-9]{5,20}"
          title="5 to 20 digits"
          hint={labourer ? "Cannot be changed." : undefined}
          {...form.field("national_id_number")}
        />
      </div>
      <LabourerDetailFields field={form.field} />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy}>
          {labourer ? "Save changes" : "Register labourer"}
        </Button>
      </div>
    </form>
  );
}
