"use client";

import { Download, Eye, Mail, Printer } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ReportView } from "@/components/reports/ReportView";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Form";
import { PageHeader } from "@/components/ui/PageHeader";
import { api, errorMessage, type QueryValue } from "@/lib/api";
import { notify } from "@/lib/notify";
import type { Message, Project, Report } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Filter = "project_id" | "successful" | "payment_type" | "date_from" | "date_to" | "payment_status" | "is_completed";

interface ReportInfo {
  value: string; // GET /reports/{value}
  label: string;
  description: string;
  filters: Filter[];
}

const REPORTS: ReportInfo[] = [
  {
    value: "payments",
    label: "Payments",
    description: "Money sent to labourers and subcontractors.",
    filters: ["project_id", "successful", "payment_type", "date_from", "date_to"],
  },
  {
    value: "works",
    label: "Works",
    description: "Works with their costs, approvals and payment status.",
    filters: ["project_id", "payment_status", "is_completed"],
  },
  {
    value: "labourers",
    label: "Labourers",
    description: "Labourers, the works they did and what they earned.",
    filters: ["project_id"],
  },
  {
    value: "projects",
    label: "Projects",
    description: "Every project with its wallet balance and progress.",
    filters: [],
  },
];

const YES_NO = [
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];
const RESULT_OPTIONS = [
  { value: "true", label: "Successful" },
  { value: "false", label: "Failed" },
];
const PAYMENT_TYPES = [
  { value: "labourer", label: "Labourer" },
  { value: "subcontractor", label: "Subcontractor" },
  { value: "retention", label: "Retention" },
];
const PAYMENT_STATUSES = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Paying out" },
  { value: "paid", label: "Paid" },
];

const EMPTY_FILTERS: Record<Filter, string> = {
  project_id: "",
  successful: "",
  payment_type: "",
  date_from: "",
  date_to: "",
  payment_status: "",
  is_completed: "",
};

/** Prints an HTML page through a hidden frame, so no pop-up window is needed. */
function printHtml(html: string) {
  const frame = document.createElement("iframe");
  // No "allow-scripts": the report is only shown and printed, never run.
  frame.setAttribute("sandbox", "allow-same-origin allow-modals");
  frame.style.position = "fixed";
  frame.style.width = "0";
  frame.style.height = "0";
  frame.style.border = "0";
  frame.onload = () => {
    const view = frame.contentWindow;
    if (!view) {
      return;
    }
    view.addEventListener("afterprint", () => frame.remove());
    view.focus();
    view.print();
  };
  frame.srcdoc = html;
  document.body.appendChild(frame);
}

/** Saves a downloaded file on the user's device. */
function saveFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  // Give the browser a moment to start the download before freeing the file.
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

/** Choose a report and its filters, then view, print, download or email it. */
export default function ReportsPage() {
  const [type, setType] = useState("payments");
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState<string | null>(null); // which button is working
  const projects = useApi<Project[]>("/projects");

  const info = REPORTS.find((item) => item.value === type) || REPORTS[0];
  const projectOptions = (projects.data || []).map((project) => ({ value: project.id, label: project.name }));

  /** Only the filters this report understands. */
  function activeFilters(): Record<string, QueryValue> {
    const result: Record<string, QueryValue> = {};
    for (const name of info.filters) {
      result[name] = filters[name];
    }
    return result;
  }

  /** value + onChange props for one filter input. */
  function setFilter(name: Filter) {
    return {
      value: filters[name],
      onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const value = event.target.value;
        setFilters((current) => ({ ...current, [name]: value }));
      },
    };
  }

  /** Runs a report action while its button shows as busy; errors are shown in a toast. */
  async function run(action: string, task: () => Promise<void>) {
    setBusy(action);
    try {
      await task();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  /** Show the report on this page. */
  const handleView = () =>
    run("view", async () => {
      const result = await api.get<Report>(`/reports/${type}`, { ...activeFilters(), format: "json" });
      setReport(result);
      toast.success(`${result.title} ready`);
    });

  /** Print the report as an HTML page. */
  const handlePrint = () =>
    run("print", async () => {
      const html = await api.text(`/reports/${type}`, { ...activeFilters(), format: "html" });
      printHtml(html);
    });

  /** Download the report as a PDF. */
  const handleDownload = () =>
    run("pdf", async () => {
      const blob = await api.blob(`/reports/${type}`, { ...activeFilters(), format: "pdf" });
      const today = new Date().toISOString().slice(0, 10);
      saveFile(blob, `${type}-report-${today}.pdf`);
      toast.success("PDF downloaded");
    });

  /** Email the report as a PDF to the logged in user. */
  async function handleEmail() {
    setBusy("email");
    // The email endpoint takes the same filters in the body; "" means "not set".
    const body: Record<string, string | boolean | null> = { report_type: type };
    for (const [name, value] of Object.entries(activeFilters())) {
      if (value === "") {
        body[name] = null;
      } else if (name === "successful" || name === "is_completed") {
        body[name] = value === "true";
      } else {
        body[name] = String(value);
      }
    }
    await notify(api.post<Message>("/reports/email", body), (result) => result.message);
    setBusy(null);
  }

  return (
    <>
      <PageHeader title="Reports" description="View, print, download or email a report." />

      <div className="space-y-6">
        <Card>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Select
              label="Report"
              options={REPORTS}
              value={type}
              hint={info.description}
              onChange={(event) => {
                setType(event.target.value);
                setReport(null);
              }}
            />
            {info.filters.includes("project_id") && (
              <Select label="Project" options={projectOptions} placeholder="All projects" {...setFilter("project_id")} />
            )}
            {info.filters.includes("successful") && (
              <Select label="Result" options={RESULT_OPTIONS} placeholder="All payments" {...setFilter("successful")} />
            )}
            {info.filters.includes("payment_type") && (
              <Select label="Paid to" options={PAYMENT_TYPES} placeholder="Everyone" {...setFilter("payment_type")} />
            )}
            {info.filters.includes("date_from") && <Input label="From" type="date" {...setFilter("date_from")} />}
            {info.filters.includes("date_to") && <Input label="To" type="date" {...setFilter("date_to")} />}
            {info.filters.includes("payment_status") && (
              <Select
                label="Payment status"
                options={PAYMENT_STATUSES}
                placeholder="Any status"
                {...setFilter("payment_status")}
              />
            )}
            {info.filters.includes("is_completed") && (
              <Select label="Completed" options={YES_NO} placeholder="All works" {...setFilter("is_completed")} />
            )}
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <Button onClick={handleView} loading={busy === "view"} disabled={busy !== null}>
              <Eye className="size-4" aria-hidden />
              View
            </Button>
            <Button variant="secondary" onClick={handlePrint} loading={busy === "print"} disabled={busy !== null}>
              <Printer className="size-4" aria-hidden />
              Print
            </Button>
            <Button variant="secondary" onClick={handleDownload} loading={busy === "pdf"} disabled={busy !== null}>
              <Download className="size-4" aria-hidden />
              Download PDF
            </Button>
            <Button variant="secondary" onClick={handleEmail} loading={busy === "email"} disabled={busy !== null}>
              <Mail className="size-4" aria-hidden />
              Email to me
            </Button>
          </div>
        </Card>

        {report && <ReportView report={report} />}
      </div>
    </>
  );
}
