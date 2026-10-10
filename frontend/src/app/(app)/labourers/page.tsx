"use client";

import { Pencil, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Can } from "@/components/Can";
import { LabourerFormModal } from "@/components/labourers/LabourerForm";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass } from "@/components/ui/Form";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { Table, Td } from "@/components/ui/Table";
import { useAuth } from "@/lib/auth";
import { choiceLabel, formatMoney } from "@/lib/format";
import type { Labourer } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useChoices } from "@/lib/useChoices";

/** Registered labourers with a search box and forms to add or edit them. */
export default function LabourersPage() {
  const { can } = useAuth();
  const { labourer_titles } = useChoices();
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Labourer | null>(null);
  const { data: labourers, error, loading, reload } = useApi<Labourer[]>("/labourers");

  const text = search.trim().toLowerCase();
  const shown = (labourers || []).filter(
    (labourer) =>
      labourer.name.toLowerCase().includes(text) ||
      labourer.national_id_number.startsWith(text) ||
      labourer.phone_number.includes(text),
  );

  /** Close the form and reload the list after a labourer is saved. */
  function handleSaved() {
    setCreating(false);
    setEditing(null);
    reload();
  }

  return (
    <>
      <PageHeader
        title="Labourers"
        description="People you have registered. Labourers are added to works from the work page."
        actions={
          <Can permission="labourers.create">
            <Button onClick={() => setCreating(true)}>
              <Plus className="size-4" aria-hidden />
              New labourer
            </Button>
          </Can>
        }
      />

      <Card>
        <div className="relative mb-4 w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
          <input
            className={`${controlClass} pl-9`}
            placeholder="Search by name, ID or phone"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search labourers"
          />
        </div>

        {loading && <Loading />}
        {error && <ErrorState message={error} onRetry={reload} />}
        {labourers && shown.length === 0 && (
          <EmptyState title={text ? "No labourer matches your search" : "No labourers yet"} />
        )}
        {shown.length > 0 && (
          <Table
            headers={[
              "Name",
              "ID number",
              "Title",
              "Phone",
              "Daily rate",
              "Overhead",
              "Paid days",
              ...(can("labourers.edit") ? [""] : []),
            ]}
          >
            {shown.map((labourer) => (
              <tr key={labourer.id}>
                <Td className="font-medium text-zinc-900">{labourer.name}</Td>
                <Td>{labourer.national_id_number}</Td>
                <Td>{choiceLabel(labourer_titles, labourer.title)}</Td>
                <Td>{labourer.phone_number}</Td>
                <Td>{formatMoney(labourer.daily_rate)}</Td>
                <Td>{formatMoney(labourer.overhead_cost)}</Td>
                <Td>{labourer.project_lifetime_approved_working_days}</Td>
                {can("labourers.edit") && (
                  <Td>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Edit ${labourer.name}`}
                      onClick={() => setEditing(labourer)}
                    >
                      <Pencil className="size-4" aria-hidden />
                    </Button>
                  </Td>
                )}
              </tr>
            ))}
          </Table>
        )}
      </Card>

      <LabourerFormModal open={creating} onClose={() => setCreating(false)} onSaved={handleSaved} />
      <LabourerFormModal
        open={editing !== null}
        labourer={editing || undefined}
        onClose={() => setEditing(null)}
        onSaved={handleSaved}
      />
    </>
  );
}
