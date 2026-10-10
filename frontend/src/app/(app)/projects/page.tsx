"use client";

import { Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Can } from "@/components/Can";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { ProjectFormModal } from "@/components/projects/ProjectForm";
import { Button } from "@/components/ui/Button";
import { controlClass } from "@/components/ui/Form";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { useAuth } from "@/lib/auth";
import type { Project } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** Projects with a search box and a form to create one. */
export default function ProjectsPage() {
  const { can } = useAuth();
  const router = useRouter();
  const [onlyMine, setOnlyMine] = useState(false);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const { data: projects, error, loading, reload } = useApi<Project[]>("/projects", {
    only_mine: onlyMine,
  });

  const text = search.trim().toLowerCase();
  const shown = (projects || []).filter(
    (project) =>
      project.name.toLowerCase().includes(text) || project.location.toLowerCase().includes(text),
  );

  return (
    <>
      <PageHeader
        title="Projects"
        description="Construction sites and the works under them."
        actions={
          <Can permission="projects.create">
            <Button onClick={() => setCreating(true)}>
              <Plus className="size-4" aria-hidden />
              New project
            </Button>
          </Can>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
          <input
            className={`${controlClass} pl-9`}
            placeholder="Search by name or location"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search projects"
          />
        </div>
        {can("projects.view_all") && (
          <label className="flex items-center gap-2 text-sm text-zinc-600">
            <input
              type="checkbox"
              checked={onlyMine}
              onChange={(event) => setOnlyMine(event.target.checked)}
              className="size-4 accent-emerald-600"
            />
            Only projects I am part of
          </label>
        )}
      </div>

      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {projects && shown.length === 0 && (
        <EmptyState title={text ? "No project matches your search" : "No projects yet"}>
          {!text && can("projects.create") && "Create your first project to get started."}
          {!text && !can("projects.create") && "Projects you are added to will show here."}
        </EmptyState>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      <ProjectFormModal
        open={creating}
        onClose={() => setCreating(false)}
        onSaved={(project) => router.push(`/projects/${project.id}`)}
      />
    </>
  );
}
