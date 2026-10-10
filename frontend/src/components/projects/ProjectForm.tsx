"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { notify } from "@/lib/notify";
import type { Project } from "@/lib/types";
import { useForm } from "@/lib/useForm";

interface ProjectFormModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: (project: Project) => void;
  project?: Project; // set when editing
}

/** Create a project (POST /projects) or edit one (PATCH /projects/{id}). */
export function ProjectFormModal({ open, onClose, onSaved, project }: ProjectFormModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={project ? "Edit project" : "New project"}>
      <ProjectForm project={project} onCancel={onClose} onSaved={onSaved} />
    </Modal>
  );
}

interface ProjectFormProps {
  project?: Project;
  onCancel: () => void;
  onSaved: (project: Project) => void;
}

/** The fields and buttons inside the project modal. */
function ProjectForm({ project, onCancel, onSaved }: ProjectFormProps) {
  const [busy, setBusy] = useState(false);
  const form = useForm({
    name: project?.name || "",
    location: project?.location || "",
    description: project?.description || "",
  });

  /** Save the project and pass the saved record back. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const request = project
      ? api.patch<Project>(`/projects/${project.id}`, form.values)
      : api.post<Project>("/projects", form.values);
    const saved = await notify(request, project ? "Project updated" : "Project created");
    setBusy(false);
    if (saved) {
      onSaved(saved);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input label="Name" required maxLength={255} {...form.field("name")} />
      <Input label="Location" required maxLength={255} placeholder="e.g. Kilimani, Nairobi" {...form.field("location")} />
      <Textarea label="Description" hint="Optional" {...form.field("description")} />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy}>
          {project ? "Save changes" : "Create project"}
        </Button>
      </div>
    </form>
  );
}
