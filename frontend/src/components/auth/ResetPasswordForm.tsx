"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Form";
import { api } from "@/lib/api";
import { notify } from "@/lib/notify";
import { useForm } from "@/lib/useForm";

/** Form to set a new password with the user_id and token from the emailed link. */
export function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const userId = searchParams.get("user_id") || "";
  const token = searchParams.get("token") || "";
  const [busy, setBusy] = useState(false);
  const form = useForm({ new_password: "", re_enter_password: "" });

  /** Save the new password (POST /auth/reset-password), then go to log in. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const result = await notify(
      api.post("/auth/reset-password", { user_id: userId, token, ...form.values }),
      "Password changed. You can now log in.",
    );
    setBusy(false);
    if (result) {
      router.replace("/login");
    }
  }

  if (!userId || !token) {
    return (
      <>
        <h1 className="text-xl font-semibold">Link not valid</h1>
        <p className="mt-2 text-sm text-zinc-600">
          This reset link is incomplete. Please ask for a new one.
        </p>
        <p className="mt-6 text-sm">
          <Link href="/forgot-password" className="font-medium text-emerald-700 hover:underline">
            Request a new link
          </Link>
        </p>
      </>
    );
  }

  return (
    <>
      <h1 className="text-xl font-semibold">Choose a new password</h1>
      <p className="mt-1 text-sm text-zinc-500">You will be logged out on all other devices.</p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <Input
          label="New password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          hint="At least 8 characters"
          {...form.field("new_password")}
        />
        <Input
          label="Repeat new password"
          type="password"
          required
          autoComplete="new-password"
          {...form.field("re_enter_password")}
        />
        <Button type="submit" loading={busy} className="w-full">
          Save new password
        </Button>
      </form>
    </>
  );
}
