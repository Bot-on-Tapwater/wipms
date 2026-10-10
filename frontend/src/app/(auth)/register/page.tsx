"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Form";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useChoices } from "@/lib/useChoices";
import { useForm } from "@/lib/useForm";

/** Sign up form. The new user is logged in straight after. */
export default function RegisterPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const { roles } = useChoices();
  const [busy, setBusy] = useState(false);
  const form = useForm({
    first_name: "",
    last_name: "",
    email: "",
    phone_number: "",
    role: "",
    password: "",
    re_enter_password: "",
  });

  useEffect(() => {
    if (user) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  // Super admins are created from the command line, not here.
  const roleOptions = roles.filter((role) => role.value !== "super-admin");

  /** Create the account (POST /auth/register), then log in with it. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/register", form.values);
      await login(form.values.email.trim(), form.values.password);
      toast.success("Account created. Welcome to WIPMS!");
      router.replace("/dashboard");
    } catch (error) {
      toast.error(errorMessage(error));
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="text-xl font-semibold">Create an account</h1>
      <p className="mt-1 text-sm text-zinc-500">
        Your role decides what you can do in WIPMS.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="First name"
            required
            autoComplete="given-name"
            {...form.field("first_name")}
          />
          <Input
            label="Last name"
            required
            autoComplete="family-name"
            {...form.field("last_name")}
          />
        </div>
        <Input
          label="Email"
          type="email"
          required
          autoComplete="email"
          {...form.field("email")}
        />
        <Input
          label="Phone number"
          required
          inputMode="numeric"
          placeholder="2547XXXXXXXX"
          hint="Starts with 254, e.g. 254712345678"
          {...form.field("phone_number")}
        />
        <Select
          label="Role"
          required
          options={roleOptions}
          placeholder="Choose your role"
          {...form.field("role")}
        />
        <Input
          label="Password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          hint="At least 8 characters"
          {...form.field("password")}
        />
        <Input
          label="Repeat password"
          type="password"
          required
          autoComplete="new-password"
          {...form.field("re_enter_password")}
        />
        <Button type="submit" loading={busy} className="w-full">
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-zinc-500">
        Already registered?{" "}
        <Link
          href="/login"
          className="font-medium text-emerald-700 hover:underline"
        >
          Log in
        </Link>
      </p>
    </>
  );
}
