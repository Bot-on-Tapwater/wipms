"use client";

import Link from "next/link";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { Badge } from "@/components/ui/Badge";
import { Card, Stat } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { useAuth } from "@/lib/auth";
import { formatMoney, humanize } from "@/lib/format";
import type { Permission } from "@/lib/permissions";
import type { Project, Work } from "@/lib/types";
import { useApi } from "@/lib/useApi";

interface Task {
  label: string;
  permission: Permission;
  isWaiting: (work: Work) => boolean;
}

// Things a user may need to do on a work, and when each one is waiting.
// A task only shows to users with the matching permission.
const TASKS: Task[] = [
  {
    label: "Approve work quality",
    permission: "works.approve_as_consultant",
    isWaiting: (work) => work.payment_status === "pending" && !work.consultant_approval,
  },
  {
    label: "Approve work done",
    permission: "works.approve_as_contractor_supervisor",
    isWaiting: (work) => work.payment_status === "pending" && !work.contractor_supervisor_approval,
  },
  {
    label: "Approve attendance",
    permission: "works.approve_attendance",
    isWaiting: (work) => work.payment_status === "pending" && !work.attendance_approval,
  },
  {
    label: "Approve cost",
    permission: "works.approve_cost",
    isWaiting: (work) => work.payment_status === "pending" && !work.cost_approval,
  },
  {
    label: "Approve payment",
    permission: "payments.approve_as_contractor_supervisor",
    isWaiting: (work) =>
      work.payment_status === "pending" && work.payment_requested && !work.contractor_supervisor_payment_approval,
  },
  {
    label: "Approve payment",
    permission: "payments.approve_as_main_contractor",
    isWaiting: (work) =>
      work.payment_status === "pending" && work.payment_requested && !work.main_contractor_payment_approval,
  },
  {
    label: "Retry failed payments",
    permission: "payments.approve_as_main_contractor",
    isWaiting: (work) => work.payment_status === "approved",
  },
  {
    label: "Release retention",
    permission: "payments.approve_retention",
    isWaiting: (work) => work.retention_payment_requested && !work.retention_paid,
  },
];

/** Greeting for the time of day, e.g. "Good morning". */
function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) {
    return "Good morning";
  }
  if (hour < 17) {
    return "Good afternoon";
  }
  return "Good evening";
}

/** Home page: totals, works waiting for the user and recent projects. */
export default function DashboardPage() {
  const { user, can } = useAuth();
  const projects = useApi<Project[]>("/projects");
  const works = useApi<Work[]>("/works");

  const myTasks = TASKS.filter((task) => can(task.permission));
  const waiting = (works.data || [])
    .map((work) => ({
      work,
      // The same label can come from two permissions (e.g. super admin), so remove repeats.
      labels: [...new Set(myTasks.filter((task) => task.isWaiting(work)).map((task) => task.label))],
    }))
    .filter((item) => item.labels.length > 0);

  const projectList = projects.data || [];
  const activeProjects = projectList.filter((project) => !project.is_completed).length;
  const walletTotal = projectList.reduce((sum, project) => sum + Number(project.wallet_balance), 0);
  const projectNames = new Map(projectList.map((project) => [project.id, project.name]));

  return (
    <>
      <PageHeader
        title={`${greeting()}, ${user?.first_name || ""}`}
        description={user ? `Signed in as ${humanize(user.role)}` : undefined}
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Active projects" value={projects.data ? activeProjects : "-"} />
        <Stat label="Works" value={works.data ? works.data.length : "-"} />
        <Stat label="Waiting for you" value={works.data ? waiting.length : "-"} />
        {can("projects.view_wallet") && (
          <Stat label="Money in wallets" value={projects.data ? formatMoney(walletTotal) : "-"} />
        )}
      </div>

      <div className="space-y-6">
        <Card title="Waiting for you" description="Works where you have something to do.">
          {works.loading && <Loading />}
          {works.error && <ErrorState message={works.error} onRetry={works.reload} />}
          {works.data && waiting.length === 0 && (
            <EmptyState title="You are all caught up">Nothing needs your attention right now.</EmptyState>
          )}
          {waiting.length > 0 && (
            <ul className="divide-y divide-zinc-100">
              {waiting.slice(0, 10).map(({ work, labels }) => (
                <li key={work.id}>
                  <Link
                    href={`/works/${work.id}`}
                    className="-mx-2 flex flex-wrap items-center justify-between gap-2 rounded-lg px-2 py-3 hover:bg-zinc-50"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-zinc-900">{work.title}</span>
                      <span className="block truncate text-xs text-zinc-500">
                        {projectNames.get(work.project_id) || "Project"} · {formatMoney(work.total_cost)}
                      </span>
                    </span>
                    <span className="flex flex-wrap gap-1">
                      {labels.map((label) => (
                        <Badge key={label} tone="amber">
                          {label}
                        </Badge>
                      ))}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {waiting.length > 10 && (
            <p className="mt-3 text-sm text-zinc-500">And {waiting.length - 10} more. Open a project to see all its works.</p>
          )}
        </Card>

        <Card
          title="Recent projects"
          actions={
            <Link href="/projects" className="text-sm font-medium text-emerald-700 hover:underline">
              See all
            </Link>
          }
        >
          {projects.loading && <Loading />}
          {projects.error && <ErrorState message={projects.error} onRetry={projects.reload} />}
          {projects.data && projectList.length === 0 && <EmptyState title="No projects yet" />}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projectList.slice(0, 6).map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
