"use client";

import { useState } from "react";
import { PaymentRecordsTable } from "@/components/payments/PaymentRecordsTable";
import { Card, Stat } from "@/components/ui/Card";
import { Select } from "@/components/ui/Form";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { formatMoney } from "@/lib/format";
import type { PaymentRecord, Project } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const RESULT_OPTIONS = [
  { value: "true", label: "Successful" },
  { value: "false", label: "Failed" },
];

/** Every payment record, filtered by project and by successful or failed. */
export default function PaymentsPage() {
  const [projectId, setProjectId] = useState("");
  const [result, setResult] = useState("");
  const projects = useApi<Project[]>("/projects");
  const records = useApi<PaymentRecord[]>("/payments/records", { project_id: projectId, successful: result });

  const list = records.data || [];
  const paid = list.filter((record) => record.successful);
  const totalPaid = paid.reduce((sum, record) => sum + Number(record.amount_paid), 0);
  const failedOpen = list.filter((record) => !record.successful && !record.is_retried).length;
  const projectOptions = (projects.data || []).map((project) => ({ value: project.id, label: project.name }));

  return (
    <>
      <PageHeader title="Payments" description="Every payment sent to labourers and subcontractors." />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:max-w-xl">
        <Select
          label="Project"
          options={projectOptions}
          placeholder="All projects"
          value={projectId}
          onChange={(event) => setProjectId(event.target.value)}
        />
        <Select
          label="Result"
          options={RESULT_OPTIONS}
          placeholder="All payments"
          value={result}
          onChange={(event) => setResult(event.target.value)}
        />
      </div>

      {records.data && (
        <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
          <Stat label="Payments shown" value={list.length} />
          <Stat label="Amount paid" value={formatMoney(totalPaid)} />
          <Stat label="Failed, not retried" value={failedOpen} hint={failedOpen ? "Retry them from the work page" : undefined} />
        </div>
      )}

      <Card>
        {records.loading && <Loading />}
        {records.error && <ErrorState message={records.error} onRetry={records.reload} />}
        {records.data && list.length === 0 && <EmptyState title="No payments found" />}
        {list.length > 0 && <PaymentRecordsTable records={list} showWork />}
      </Card>
    </>
  );
}
