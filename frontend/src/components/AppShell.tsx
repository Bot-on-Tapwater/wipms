"use client";

// Layout of every page after login: a sidebar on large screens and a top bar
// with a slide-out menu on phones. Menu items the user has no permission for
// are not shown. Sends people who are not logged in to /login.

import {
  Banknote,
  Building2,
  ChartColumn,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { Loading } from "@/components/ui/States";
import { useAuth } from "@/lib/auth";
import { humanize } from "@/lib/format";
import type { Permission } from "@/lib/permissions";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  permission?: Permission;
  // Other paths that belong to this item, e.g. works belong to projects.
  alsoActiveFor?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: Building2, alsoActiveFor: ["/works"] },
  { href: "/labourers", label: "Labourers", icon: Users, permission: "labourers.view" },
  { href: "/payments", label: "Payments", icon: Banknote, permission: "payments.view" },
  { href: "/reports", label: "Reports", icon: FileText, permission: "reports.view" },
  { href: "/insights", label: "Insights", icon: ChartColumn, permission: "stats.view" },
  { href: "/profile", label: "My profile", icon: UserRound },
];

/** True when the current page belongs to this menu item. */
function isActive(item: NavItem, pathname: string): boolean {
  const paths = [item.href, ...(item.alsoActiveFor || [])];
  return paths.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

/** Menu links the user may see, their name and role, and the log out button. */
function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, can, logout } = useAuth();
  const items = NAV_ITEMS.filter((item) => !item.permission || can(item.permission));

  return (
    <div className="flex h-full flex-col">
      <nav className="flex-1 space-y-1 p-3">
        {items.map((item) => {
          const active = isActive(item, pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active ? "bg-emerald-50 text-emerald-800" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Icon className="size-4" aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-zinc-200 p-3">
        <div className="px-3 pb-2">
          <p className="truncate text-sm font-medium text-zinc-900">{user?.full_name}</p>
          <p className="truncate text-xs text-zinc-500">{user ? humanize(user.role) : ""}</p>
        </div>
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
        >
          <LogOut className="size-4" aria-hidden />
          Log out
        </button>
      </div>
    </div>
  );
}

/** Sidebar or phone menu around the page. Sends logged out users to /login. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return <Loading />;
  }

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar on large screens */}
      <aside className="hidden w-60 shrink-0 border-r border-zinc-200 bg-white lg:fixed lg:inset-y-0 lg:flex lg:flex-col">
        <div className="flex h-16 items-center px-6">
          <Logo />
        </div>
        <Navigation />
      </aside>

      {/* Top bar on phones and tablets */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-zinc-200 bg-white px-4 lg:hidden">
        <Logo />
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100"
          aria-label="Open menu"
        >
          <Menu className="size-5" />
        </button>
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-zinc-900/40" onClick={() => setMenuOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-xl">
            <div className="flex h-14 items-center justify-between px-4">
              <Logo />
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100"
                aria-label="Close menu"
              >
                <X className="size-5" />
              </button>
            </div>
            <Navigation onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}

      <main className="min-w-0 flex-1 lg:pl-60">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">{children}</div>
      </main>
    </div>
  );
}
