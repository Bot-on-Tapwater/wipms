"use client";

import { MapPin, Pencil, Plus, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Can } from "@/components/Can";
import { ProjectFormModal } from "@/components/projects/ProjectForm";
import { TeamSection } from "@/components/projects/TeamSection";
import { WalletSection } from "@/components/projects/WalletSection";
import { ActionButton } from "@/components/ui/ActionButton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { WorkFormModal } from "@/components/works/WorkForm";
import { WorksTable } from "@/components/works/WorksTable";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Message, Project, Work } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** One project: its works, team and wallet, with edit and delete buttons. */
export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { can } = useAuth();
  const [editing, setEditing] = useState(false);
  const [addingWork, setAddingWork] = useState(false);
  const project = useApi<Project>(`/projects/${projectId}`);
  const works = useApi<Work[]>("/works", { project_id: projectId });

  if (project.loading) {
    return <Loading />;
  }
  if (project.error || !project.data) {
    return <ErrorState message={project.error || "Project not found"} onRetry={project.reload} />;
  }
  const current = project.data;

  return (
    <>
      <PageHeader
        title={current.name}
        back={{ href: "/projects", label: "Projects" }}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1">
              <MapPin className="size-4" aria-hidden />
              {current.location}
            </span>
            <Badge tone={current.is_completed ? "green" : "blue"}>
              {current.is_completed ? "Completed" : "Active"}
            </Badge>
          </span>
        }
        actions={
          <>
            <Can permission="projects.edit">
              <Button variant="secondary" onClick={() => setEditing(true)}>
                <Pencil className="size-4" aria-hidden />
                Edit
              </Button>
            </Can>
            <Can permission="projects.delete">
              <ActionButton
                variant="danger"
                confirm={`Delete "${current.name}" and all its works? This cannot be undone. Projects that already have payments cannot be deleted.`}
                confirmLabel="Delete project"
                action={() => api.delete<Message>(`/projects/${current.id}`)}
                success="Project deleted"
                onDone={() => router.push("/projects")}
              >
                <Trash2 className="size-4" aria-hidden />
                Delete
              </ActionButton>
            </Can>
          </>
        }
      />

      <div className="space-y-6">
        {current.description && (
          <p className="whitespace-pre-line text-sm text-zinc-600">{current.description}</p>
        )}

        <Card
          title="Works"
          description="Tasks on this project. Open one to add labourers, approve it and pay."
          actions={
            <Can permission="works.create">
              <Button size="sm" onClick={() => setAddingWork(true)}>
                <Plus className="size-4" aria-hidden />
                New work
              </Button>
            </Can>
          }
        >
          {works.loading && <Loading />}
          {works.error && <ErrorState message={works.error} onRetry={works.reload} />}
          {works.data && works.data.length === 0 && (
            <EmptyState title="No works yet">
              {can("works.create") ? "Add the first work to start tracking it." : undefined}
            </EmptyState>
          )}
          {works.data && works.data.length > 0 && <WorksTable works={works.data} />}
        </Card>

        <TeamSection project={current} onChange={project.setData} />

        <Can permission="projects.view_wallet">
          <WalletSection project={current} onChange={project.reload} />
        </Can>
      </div>

      <ProjectFormModal
        open={editing}
        project={current}
        onClose={() => setEditing(false)}
        onSaved={(saved) => {
          setEditing(false);
          project.setData(saved);
        }}
      />
      <WorkFormModal
        open={addingWork}
        project={current}
        onClose={() => setAddingWork(false)}
        onSaved={(work) => router.push(`/works/${work.id}`)}
      />
    </>
  );
}
