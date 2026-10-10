"use client";

// The four approvals a work needs before it can be paid, and the two
// supervisor comments.

import { Check, Circle } from "lucide-react";
import { useState } from "react";
import { ActionButton } from "@/components/ui/ActionButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Textarea } from "@/components/ui/Form";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/notify";
import type { Permission } from "@/lib/permissions";
import type { Work } from "@/lib/types";

interface ApprovalInfo {
  type: string; // approval_type sent to POST /works/{id}/approvals
  label: string;
  who: string;
  isGiven: (work: Work) => boolean;
  permission: Permission;
}

const APPROVALS: ApprovalInfo[] = [
  {
    type: "consultant",
    label: "Work quality (consultant)",
    who: "Consultant supervisor",
    isGiven: (work) => work.consultant_approval,
    permission: "works.approve_as_consultant",
  },
  {
    type: "contractor_supervisor",
    label: "Work done (contractor supervisor)",
    who: "Contractor supervisor",
    isGiven: (work) => work.contractor_supervisor_approval,
    permission: "works.approve_as_contractor_supervisor",
  },
  {
    type: "attendance",
    label: "Labourer attendance",
    who: "Contractor supervisor",
    isGiven: (work) => work.attendance_approval,
    permission: "works.approve_attendance",
  },
  {
    type: "cost",
    label: "Cost",
    who: "Main contractor",
    isGiven: (work) => work.cost_approval,
    permission: "works.approve_cost",
  },
];

interface CommentInfo {
  path: string; // POST /works/{id}/comments/{path}
  label: string;
  text: (work: Work) => string;
  permission: Permission;
}

const COMMENTS: CommentInfo[] = [
  {
    path: "contractor-supervisor",
    label: "Contractor supervisor comment",
    text: (work) => work.contractor_supervisor_comments,
    permission: "works.comment_as_contractor_supervisor",
  },
  {
    path: "consultant-supervisor",
    label: "Consultant supervisor comment",
    text: (work) => work.consultant_supervisor_comments,
    permission: "works.comment_as_consultant_supervisor",
  },
];

interface ApprovalsTabProps {
  work: Work;
  locked: boolean;
  onChange: (work: Work) => void;
}

/** The approvals of a work with their buttons, and the supervisor comments. */
export function ApprovalsTab({ work, locked, onChange }: ApprovalsTabProps) {
  const { can } = useAuth();

  return (
    <div className="space-y-6">
      <Card title="Approvals" description="All four are needed before payment can be approved.">
        <ul className="divide-y divide-zinc-100">
          {APPROVALS.map((info) => {
            const given = info.isGiven(work);
            return (
              <li key={info.type} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="flex items-center gap-3">
                  {given ? (
                    <Check className="size-5 rounded-full bg-emerald-100 p-0.5 text-emerald-700" aria-hidden />
                  ) : (
                    <Circle className="size-5 text-zinc-300" aria-hidden />
                  )}
                  <div>
                    <p className="text-sm font-medium text-zinc-900">{info.label}</p>
                    <p className="text-xs text-zinc-500">
                      {given ? "Approved" : "Waiting"} · {info.who}
                    </p>
                  </div>
                </div>
                {can(info.permission) && !locked && (
                  <ActionButton
                    size="sm"
                    variant={given ? "secondary" : "primary"}
                    action={() =>
                      api.post<Work>(`/works/${work.id}/approvals`, { approval_type: info.type, approved: !given })
                    }
                    success={given ? "Approval withdrawn" : "Approved"}
                    onDone={onChange}
                  >
                    {given ? "Withdraw" : "Approve"}
                  </ActionButton>
                )}
              </li>
            );
          })}
        </ul>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {COMMENTS.map((info) => (
          <CommentCard
            key={info.path}
            info={info}
            work={work}
            canEdit={can(info.permission)}
            onChange={onChange}
          />
        ))}
      </div>
    </div>
  );
}

interface CommentCardProps {
  info: CommentInfo;
  work: Work;
  canEdit: boolean;
  onChange: (work: Work) => void;
}

/** One supervisor comment. Saving replaces the previous comment. */
function CommentCard({ info, work, canEdit, onChange }: CommentCardProps) {
  const current = info.text(work);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(current);
  const [busy, setBusy] = useState(false);

  /** Save the comment (POST /works/{id}/comments/...). */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const updated = await notify(
      api.post<Work>(`/works/${work.id}/comments/${info.path}`, { comment: text }),
      "Comment saved",
    );
    setBusy(false);
    if (updated) {
      setEditing(false);
      onChange(updated);
    }
  }

  return (
    <Card
      title={info.label}
      actions={
        canEdit &&
        !editing && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setText(current);
              setEditing(true);
            }}
          >
            {current ? "Edit" : "Add comment"}
          </Button>
        )
      }
    >
      {editing ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <Textarea
            label="Comment"
            required
            rows={4}
            maxLength={5000}
            value={text}
            onChange={(event) => setText(event.target.value)}
            hint="This replaces the current comment."
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" loading={busy}>
              Save
            </Button>
          </div>
        </form>
      ) : (
        <p className={`whitespace-pre-line text-sm ${current ? "text-zinc-700" : "text-zinc-400"}`}>
          {current || "No comment yet"}
        </p>
      )}
    </Card>
  );
}
