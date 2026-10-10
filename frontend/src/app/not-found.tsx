import Link from "next/link";
import { buttonClass } from "@/components/ui/Button";

/** Shown for any address that does not match a page. */
export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="text-sm font-medium text-emerald-700">404</p>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-zinc-500">The page you are looking for does not exist.</p>
      <Link href="/dashboard" className={buttonClass()}>
        Go to dashboard
      </Link>
    </main>
  );
}
