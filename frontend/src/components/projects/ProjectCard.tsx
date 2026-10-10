"use client";

import { MapPin } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { useAuth } from "@/lib/auth";
import { formatMoney } from "@/lib/format";
import type { Project } from "@/lib/types";

/** Clickable summary of a project, used on the projects page and dashboard. */
export function ProjectCard({ project }: { project: Project }) {
  const { can } = useAuth();
  const supervisors = project.contractor_supervisors.length + project.consultant_supervisors.length;

  return (
    <Link
      href={`/projects/${project.id}`}
      className="block rounded-xl border border-zinc-200 bg-white p-4 transition hover:border-emerald-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-zinc-900">{project.name}</h3>
        {project.is_completed ? <Badge tone="green">Completed</Badge> : <Badge tone="blue">Active</Badge>}
      </div>
      <p className="mt-1 flex items-center gap-1 text-sm text-zinc-500">
        <MapPin className="size-3.5" aria-hidden />
        {project.location}
      </p>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-2 text-xs text-zinc-500">
        <span>
          {supervisors} supervisor{supervisors === 1 ? "" : "s"} · {project.subcontractors.length} subcontractor
          {project.subcontractors.length === 1 ? "" : "s"}
        </span>
        {can("projects.view_wallet") && (
          <span className="text-sm font-medium text-zinc-900">{formatMoney(project.wallet_balance)}</span>
        )}
      </div>
    </Link>
  );
}
