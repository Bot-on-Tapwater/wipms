"use client";

// The people on a project: contractor supervisors, consultant supervisors
// and subcontractors. Users with the right permission can add and remove them.

import { Plus, X } from "lucide-react";
import { useState } from "react";
import { ActionButton } from "@/components/ui/ActionButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/notify";
import type { Permission } from "@/lib/permissions";
import type { Project, User, UserBrief } from "@/lib/types";
import { useApi } from "@/lib/useApi";

interface TeamInfo {
  team: string; // URL part: /projects/{id}/{team}
  label: string;
  role: string; // only users with this role can join the team
  members: (project: Project) => UserBrief[];
  assignPermission: Permission;
  unassignPermission: Permission;
}

const TEAMS: TeamInfo[] = [
  {
    team: "contractor-supervisors",
    label: "Contractor supervisors",
    role: "contractors-supervisor",
    members: (project) => project.contractor_supervisors,
    assignPermission: "projects.assign_supervisors",
    unassignPermission: "projects.assign_supervisors",
  },
  {
    team: "consultant-supervisors",
    label: "Consultant supervisors",
    role: "consultants-supervisor",
    members: (project) => project.consultant_supervisors,
    assignPermission: "projects.assign_supervisors",
    unassignPermission: "projects.assign_supervisors",
  },
  {
    team: "subcontractors",
    label: "Subcontractors",
    role: "subcontractor",
    members: (project) => project.subcontractors,
    assignPermission: "projects.assign_subcontractors",
    unassignPermission: "projects.unassign_subcontractors",
  },
];

interface TeamSectionProps {
  project: Project;
  onChange: (project: Project) => void;
}

/** The three teams of a project, with add and remove buttons. */
export function TeamSection({ project, onChange }: TeamSectionProps) {
  const { can } = useAuth();
  const [adding, setAdding] = useState<TeamInfo | null>(null);

  return (
    <Card title="Team" description="People who work on this project.">
      <div className="grid gap-6 md:grid-cols-3">
        {TEAMS.map((info) => {
          const members = info.members(project);
          // Picking people needs the list of users as well.
          const canAdd = can(info.assignPermission) && can("users.view_all");
          return (
            <div key={info.team}>
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="text-sm font-medium text-zinc-700">{info.label}</h3>
                {canAdd && (
                  <Button variant="ghost" size="sm" onClick={() => setAdding(info)}>
                    <Plus className="size-4" aria-hidden />
                    Add
                  </Button>
                )}
              </div>
              {members.length === 0 && <p className="text-sm text-zinc-400">Nobody yet</p>}
              <ul className="space-y-1">
                {members.map((member) => (
                  <li
                    key={member.id}
                    className="flex items-center justify-between gap-2 rounded-lg bg-zinc-50 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-zinc-800">{member.full_name}</p>
                      <p className="truncate text-xs text-zinc-500">{member.email}</p>
                    </div>
                    {can(info.unassignPermission) && (
                      <ActionButton
                        variant="ghost"
                        size="sm"
                        aria-label={`Remove ${member.full_name}`}
                        confirm={`Remove ${member.full_name} from this project?`}
                        confirmLabel="Remove"
                        action={() => api.delete<Project>(`/projects/${project.id}/${info.team}/${member.id}`)}
                        success={`${member.full_name} removed`}
                        onDone={onChange}
                      >
                        <X className="size-4" aria-hidden />
                      </ActionButton>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      <Modal open={adding !== null} onClose={() => setAdding(null)} title={`Add ${adding?.label.toLowerCase() || ""}`}>
        {adding && (
          <AddMembers
            project={project}
            info={adding}
            onDone={(updated) => {
              setAdding(null);
              onChange(updated);
            }}
            onCancel={() => setAdding(null)}
          />
        )}
      </Modal>
    </Card>
  );
}

interface AddMembersProps {
  project: Project;
  info: TeamInfo;
  onDone: (project: Project) => void;
  onCancel: () => void;
}

/** Pick users with the team's role and add them to the project. */
function AddMembers({ project, info, onDone, onCancel }: AddMembersProps) {
  const { data: users, error, loading, reload } = useApi<User[]>("/users", { role: info.role });
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const currentIds = info.members(project).map((member) => member.id);
  const available = (users || []).filter((user) => !currentIds.includes(user.id));

  /** Tick or untick a user. */
  function handleToggle(userId: string) {
    setSelected((current) =>
      current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId],
    );
  }

  /** Add the ticked users to the team. */
  async function handleSave() {
    setBusy(true);
    const updated = await notify(
      api.post<Project>(`/projects/${project.id}/${info.team}`, { user_ids: selected }),
      selected.length === 1 ? "1 person added" : `${selected.length} people added`,
    );
    setBusy(false);
    if (updated) {
      onDone(updated);
    }
  }

  if (loading) {
    return <Loading />;
  }
  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  return (
    <>
      {available.length === 0 ? (
        <EmptyState title="Nobody else to add">
          Everyone registered with this role is already on the project.
        </EmptyState>
      ) : (
        <ul className="max-h-80 space-y-1 overflow-y-auto">
          {available.map((user) => (
            <li key={user.id}>
              <label className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 hover:bg-zinc-50">
                <input
                  type="checkbox"
                  className="size-4 accent-emerald-600"
                  checked={selected.includes(user.id)}
                  onChange={() => handleToggle(user.id)}
                />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-zinc-800">{user.full_name}</span>
                  <span className="block truncate text-xs text-zinc-500">
                    {user.email} · {user.phone_number}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSave} loading={busy} disabled={selected.length === 0}>
          Add selected
        </Button>
      </div>
    </>
  );
}
