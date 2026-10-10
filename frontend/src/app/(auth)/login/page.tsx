"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Form";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Email and password log in form. */
export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  // Already logged in: go straight to the dashboard.
  useEffect(() => {
    if (user) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  // Back here after logging out or because the session expired: say so.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("logged_out")) {
      toast.success("You have been logged out", { id: "logged-out" });
    } else if (params.has("expired")) {
      toast.info("Your session has expired. Please log in again.", { id: "session-expired" });
    }
  }, []);

  /** Log in, then open the dashboard. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await login(email.trim(), password);
      toast.success("Welcome back");
      router.replace("/dashboard");
    } catch (error) {
      toast.error(errorMessage(error));
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="text-xl font-semibold">Log in</h1>
      <p className="mt-1 text-sm text-zinc-500">Use the email and password you registered with.</p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-sm text-emerald-700 hover:underline">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" loading={busy} className="w-full">
          Log in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-zinc-500">
        No account yet?{" "}
        <Link href="/register" className="font-medium text-emerald-700 hover:underline">
          Create one
        </Link>
      </p>
    </>
  );
}
