"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Form";
import { PageHeader } from "@/components/ui/PageHeader";
import { Loading } from "@/components/ui/States";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { notify } from "@/lib/notify";
import type { TokenPair, User } from "@/lib/types";
import { useChoices } from "@/lib/useChoices";
import { useForm } from "@/lib/useForm";

// Roles nobody can switch to from their profile.
const LOCKED_ROLES = ["super-admin", "main-contractor"];

/** The logged in user's details and password forms. */
export default function ProfilePage() {
  const { user } = useAuth();
  if (!user) {
    return <Loading />;
  }
  return (
    <>
      <PageHeader title="My profile" description={`${user.email} · member since ${formatDate(user.created_at)}`} />
      <div className="grid gap-6 lg:grid-cols-2">
        <DetailsCard user={user} />
        <PasswordCard />
      </div>
    </>
  );
}

/** Form to edit the user's name, phone number and role. */
function DetailsCard({ user }: { user: User }) {
  const { reload } = useAuth();
  const { roles } = useChoices();
  const [busy, setBusy] = useState(false);
  const form = useForm({
    first_name: user.first_name,
    last_name: user.last_name,
    phone_number: user.phone_number,
    role: user.role,
  });

  // Keep the current role in the list so the select can show it.
  const roleOptions = roles.filter((role) => !LOCKED_ROLES.includes(role.value) || role.value === user.role);

  /** Save the details (PATCH /users/me), then reload the user's permissions. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const { role, ...details } = form.values;
    // Only send the role when it changed: changing it has extra rules.
    const body = role === user.role ? details : { ...details, role };
    const saved = await notify(api.patch<User>("/users/me", body), "Profile updated");
    setBusy(false);
    if (saved) {
      await reload(); // the role decides the permissions, so load them again
    }
  }

  return (
    <Card title="Details">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="First name" required autoComplete="given-name" {...form.field("first_name")} />
          <Input label="Last name" required autoComplete="family-name" {...form.field("last_name")} />
        </div>
        <Input
          label="Phone number"
          required
          inputMode="numeric"
          pattern="254[0-9]{9}"
          title="254 followed by 9 digits"
          hint="Starts with 254, e.g. 254712345678"
          {...form.field("phone_number")}
        />
        <Select
          label="Role"
          required
          options={roleOptions}
          disabled={LOCKED_ROLES.includes(user.role)}
          hint="You can only change your role while you are not on any project."
          {...form.field("role")}
        />
        <div className="flex justify-end">
          <Button type="submit" loading={busy}>
            Save changes
          </Button>
        </div>
      </form>
    </Card>
  );
}

/** Form to change the user's password. */
function PasswordCard() {
  const { storeTokens } = useAuth();
  const [busy, setBusy] = useState(false);
  const form = useForm({ current_password: "", new_password: "", re_enter_password: "" });

  /** Change the password (POST /auth/change-password) and keep the new tokens. */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    const tokens = await notify(api.post<TokenPair>("/auth/change-password", form.values), "Password changed");
    setBusy(false);
    if (tokens) {
      // Changing the password logs out other sessions; this one gets new tokens.
      storeTokens(tokens);
      form.reset();
    }
  }

  return (
    <Card title="Change password">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Current password"
          type="password"
          required
          autoComplete="current-password"
          {...form.field("current_password")}
        />
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
          minLength={8}
          autoComplete="new-password"
          {...form.field("re_enter_password")}
        />
        <div className="flex justify-end">
          <Button type="submit" loading={busy}>
            Change password
          </Button>
        </div>
      </form>
    </Card>
  );
}
