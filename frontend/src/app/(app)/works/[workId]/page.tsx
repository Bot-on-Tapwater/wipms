"use client";

import { Pencil, Trash2, UserPlus, X } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Can } from "@/components/Can";
import { ActionButton } from "@/components/ui/ActionButton";
import { Badge, PaymentStatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/ui/Card";
import { Select } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, Loading } from "@/components/ui/States";
import { Tabs } from "@/components/ui/Tabs";
import { ApprovalsTab } from "@/components/works/ApprovalsTab";
import { ImagesTab } from "@/components/works/ImagesTab";
import { LabourersTab } from "@/components/works/LabourersTab";
import { PaymentsTab } from "@/components/works/PaymentsTab";
import { WorkFormModal } from "@/components/works/WorkForm";
import { approvalCount } from "@/components/works/WorksTable";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { choiceLabel, formatMoney } from "@/lib/format";
import { notify } from "@/lib/notify";
import type { Message, Project, Work } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useChoices } from "@/lib/useChoices";

const TABS = [
  { id: "labourers", label: "Labourers" },
  { id: "approvals", label: "Approvals & comments" },
  { id: "images", label: "Proof of work" },
  { id: "payments", label: "Payments" },
];

/** One work: its details, labourers, approvals, photos and payments. */
export default function WorkPage() {
  const { workId } = useParams<{ workId: string }>();
  const router = useRouter();
  const { can } = useAuth();
  const { task_categories } = useChoices();
  const [tab, setTab] = useState("labourers");
  const [editing, setEditing] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const work = useApi<Work>(`/works/${workId}`);
  const project = useApi<Project>(work.data ? `/projects/${work.data.project_id}` : null);

  if (work.loading) {
    return <Loading />;
  }
  if (work.error || !work.data) {
    return <ErrorState message={work.error || "Work not found"} onRetry={work.reload} />;
  }
  const current = work.data;
  // Once money has been sent the work can no longer be changed.
  const locked = current.payment_status !== "pending";
  const projectHref = `/projects/${current.project_id}`;

  return (
    <>
      <PageHeader
        title={current.title}
        back={{ href: projectHref, label: project.data?.name || "Project" }}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span>{choiceLabel(task_categories, current.category)}</span>
            <PaymentStatusBadge status={current.payment_status} />
            <Badge tone={approvalCount(current) === 4 ? "green" : "gray"}>
              {approvalCount(current)} of 4 approvals
            </Badge>
          </span>
        }
        actions={
          !locked && (
            <>
              <Can permission="works.edit">
                <Button variant="secondary" onClick={() => setEditing(true)} disabled={!project.data}>
                  <Pencil className="size-4" aria-hidden />
                  Edit
                </Button>
              </Can>
              {!current.payment_requested && (
                <Can permission="works.delete">
                  <ActionButton
                    variant="danger"
                    confirm={`Delete "${current.title}"? This cannot be undone.`}
                    confirmLabel="Delete work"
                    action={() => api.delete<Message>(`/works/${current.id}`)}
                    success="Work deleted"
                    onDone={() => router.push(projectHref)}
                  >
                    <Trash2 className="size-4" aria-hidden />
                    Delete
                  </ActionButton>
                </Can>
              )}
            </>
          )
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total cost" value={formatMoney(current.total_cost)} />
        <Stat label="Labour" value={formatMoney(current.cost_labor)} />
        <Stat label="Overhead" value={formatMoney(current.cost_overhead)} />
        <Stat label="Retention" value={formatMoney(current.retention_money)} />
      </div>

      <div className="mb-6 grid gap-6 md:grid-cols-2">
        <Card
          title="Subcontractor"
          actions={
            can("works.assign_subcontractor") &&
            !locked && (
              <Button variant="secondary" size="sm" onClick={() => setAssigning(true)} disabled={!project.data}>
                <UserPlus className="size-4" aria-hidden />
                {current.assigned_subcontractor ? "Change" : "Assign"}
              </Button>
            )
          }
        >
          {current.assigned_subcontractor ? (
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-zinc-900">
                  {current.assigned_subcontractor.full_name}
                </p>
                <p className="truncate text-xs text-zinc-500">{current.assigned_subcontractor.email}</p>
              </div>
              {can("works.assign_subcontractor") && !locked && (
                <ActionButton
                  variant="ghost"
                  size="sm"
                  aria-label="Remove subcontractor"
                  confirm={`Remove ${current.assigned_subcontractor.full_name} from this work?`}
                  confirmLabel="Remove"
                  action={() => api.delete<Work>(`/works/${current.id}/subcontractor`)}
                  success="Subcontractor removed"
                  onDone={work.setData}
                >
                  <X className="size-4" aria-hidden />
                </ActionButton>
              )}
            </div>
          ) : (
            <p className="text-sm text-zinc-400">Not assigned</p>
          )}
        </Card>
        <Card title="Description">
          <p className={`whitespace-pre-line text-sm ${current.description ? "text-zinc-700" : "text-zinc-400"}`}>
            {current.description || "No description"}
          </p>
        </Card>
      </div>

      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === "labourers" && <LabourersTab work={current} locked={locked} />}
      {tab === "approvals" && <ApprovalsTab work={current} locked={locked} onChange={work.setData} />}
      {tab === "images" && <ImagesTab work={current} />}
      {tab === "payments" && <PaymentsTab work={current} onChange={work.setData} />}

      {project.data && (
        <>
          <WorkFormModal
            open={editing}
            project={project.data}
            work={current}
            onClose={() => setEditing(false)}
            onSaved={(saved) => {
              setEditing(false);
              work.setData(saved);
            }}
          />
          <Modal open={assigning} onClose={() => setAssigning(false)} title="Assign subcontractor">
            <AssignSubcontractorForm
              work={current}
              project={project.data}
              onCancel={() => setAssigning(false)}
              onDone={(saved) => {
                setAssigning(false);
                work.setData(saved);
              }}
            />
          </Modal>
        </>
      )}
    </>
  );
}

interface AssignSubcontractorFormProps {
  work: Work;
  project: Project;
  onCancel: () => void;
  onDone: (work: Work) => void;
}

/** Form to give the work to one of the project's subcontractors. */
function AssignSubcontractorForm({ work, project, onCancel, onDone }: AssignSubcontractorFormProps) {
  const [subcontractorId, setSubcontractorId] = useState(work.assigned_subcontractor?.id || "");
  const [busy, setBusy] = useState(false);
  const options = project.subcontractors.map((person) => ({ value: person.id, label: person.full_name }));

  /** Assign the chosen subcontractor (PUT /works/{id}/subcontractor). */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const saved = await notify(
      api.put<Work>(`/works/${work.id}/subcontractor`, { subcontractor_id: subcontractorId }),
      "Subcontractor assigned",
    );
    setBusy(false);
    if (saved) {
      onDone(saved);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Select
        label="Subcontractor"
        required
        options={options}
        placeholder="Choose a subcontractor"
        hint={options.length === 0 ? "Add subcontractors to the project first." : "Only subcontractors on this project are listed."}
        value={subcontractorId}
        onChange={(event) => setSubcontractorId(event.target.value)}
      />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy} disabled={!subcontractorId}>
          Assign
        </Button>
      </div>
    </form>
  );
}
