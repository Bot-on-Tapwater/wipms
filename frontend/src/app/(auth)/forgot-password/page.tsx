"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Form";
import { api } from "@/lib/api";
import { notify } from "@/lib/notify";
import type { Message } from "@/lib/types";

/** Asks for an email and sends a password reset link to it. */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  /** Ask for the reset link (POST /auth/forgot-password). */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const result = await notify(
      api.post<Message>("/auth/forgot-password", { email: email.trim() }),
      (answer) => answer.message,
    );
    setBusy(false);
    if (result) {
      setSent(true);
    }
  }

  return (
    <>
      <h1 className="text-xl font-semibold">Forgot your password?</h1>
      {sent ? (
        <p className="mt-3 text-sm text-zinc-600">
          If an account exists for <strong>{email}</strong>, we have emailed a link to reset the
          password. The link expires after a while, so use it soon.
        </p>
      ) : (
        <>
          <p className="mt-1 text-sm text-zinc-500">
            Enter your email and we will send you a link to set a new password.
          </p>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Input
              label="Email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Button type="submit" loading={busy} className="w-full">
              Send reset link
            </Button>
          </form>
        </>
      )}
      <p className="mt-6 text-center text-sm">
        <Link href="/login" className="font-medium text-emerald-700 hover:underline">
          Back to log in
        </Link>
      </p>
    </>
  );
}
