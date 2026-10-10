import { AppShell } from "@/components/AppShell";

// Every page in this folder needs a logged in user.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
