"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/notify";
import type { Project, Work } from "@/lib/types";
import { useChoices } from "@/lib/useChoices";
import { useForm } from "@/lib/useForm";

interface WorkFormModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: (work: Work) => void;
  project: Project;
  work?: Work; // set when editing
}

/** Create a work (POST /works) or edit one (PATCH /works/{id}). */
export function WorkFormModal({ open, onClose, onSaved, project, work }: WorkFormModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={work ? "Edit work" : "New work"}>
      <WorkForm project={project} work={work} onCancel={onClose} onSaved={onSaved} />
    </Modal>
  );
}

interface WorkFormProps {
  project: Project;
  work?: Work;
  onCancel: () => void;
  onSaved: (work: Work) => void;
}

/** The fields and buttons inside the work modal. */
function WorkForm({ project, work, onCancel, onSaved }: WorkFormProps) {
  const { user, can } = useAuth();
  const { task_categories } = useChoices();
  const [busy, setBusy] = useState(false);
  const form = useForm({
    title: work?.title || "",
    category: work?.category || "",
    cost_labor: work?.cost_labor || "",
    cost_overhead: work?.cost_overhead || "0",
    description: work?.description || "",
    assigned_subcontractor_id: "",
  });

  // A subcontractor who creates a work is assigned to it automatically.
  const canPickSubcontractor =
    !work && user?.role !== "subcontractor" && can("works.assign_subcontractor");
  const subcontractorOptions = project.subcontractors.map((person) => ({
    value: person.id,
    label: person.full_name,
  }));

  /** Save the work and pass the saved record back. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const { assigned_subcontractor_id, ...values } = form.values;
    const request = work
      ? api.patch<Work>(`/works/${work.id}`, values)
      : api.post<Work>("/works", {
          ...values,
          project_id: project.id,
          assigned_subcontractor_id: assigned_subcontractor_id || null,
        });
    const saved = await notify(request, work ? "Work updated" : "Work created");
    setBusy(false);
    if (saved) {
      onSaved(saved);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input label="Title" required maxLength={255} placeholder="e.g. Ground floor walling" {...form.field("title")} />
      <Select
        label="Category"
        required
        options={task_categories}
        placeholder="Choose a category"
        {...form.field("category")}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Labour cost (KES)"
          type="number"
          min="0"
          step="0.01"
          required
          inputMode="decimal"
          {...form.field("cost_labor")}
        />
        <Input
          label="Overhead cost (KES)"
          type="number"
          min="0"
          step="0.01"
          inputMode="decimal"
          {...form.field("cost_overhead")}
        />
      </div>
      {work && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Changing the cost withdraws the cost approval and any payment request.
        </p>
      )}
      {canPickSubcontractor && (
        <Select
          label="Subcontractor"
          options={subcontractorOptions}
          placeholder="Not assigned yet"
          hint={subcontractorOptions.length === 0 ? "Add subcontractors to the project first." : undefined}
          {...form.field("assigned_subcontractor_id")}
        />
      )}
      <Textarea label="Description" hint="Optional" {...form.field("description")} />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy}>
          {work ? "Save changes" : "Create work"}
        </Button>
      </div>
    </form>
  );
}
