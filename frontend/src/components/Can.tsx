"use client";

import { useAuth } from "@/lib/auth";
import type { Permission } from "@/lib/permissions";

/**
 * Shows its children only when the logged in user has the permission.
 *
 *   <Can permission="projects.create"><Button>New project</Button></Can>
 */
export function Can({ permission, children }: { permission: Permission; children: React.ReactNode }) {
  const { can } = useAuth();
  if (!can(permission)) {
    return null;
  }
  return <>{children}</>;
}
