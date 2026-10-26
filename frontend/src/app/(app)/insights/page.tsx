"use client";

import { X } from "lucide-react";
import { useState } from "react";
import { BarList } from "@/components/insights/BarList";
import { MEASURES, type Measure } from "@/components/insights/measure";
import { MonthChart, monthLabel } from "@/components/insights/MonthChart";
import { ProjectTable } from "@/components/insights/ProjectTable";
import { TopLabourersTable } from "@/components/insights/TopLabourersTable";
import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Form";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { Tabs } from "@/components/ui/Tabs";
import { useAuth } from "@/lib/auth";
import { choiceLabel, formatDate, formatMoney } from "@/lib/format";
import type { Choice, LabourStats } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useChoices } from "@/lib/useChoices";

type FilterName = "project_id" | "trade" | "gender" | "age_group" | "date_from" | "date_to";
type Filters = Record<FilterName, string>;

const NO_FILTERS: Filters = { project_id: "", trade: "", gender: "", age_group: "", date_from: "", date_to: "" };

const FILTER_LABELS: Record<FilterName, string> = {
  project_id: "Project",
  trade: "Trade",
  gender: "Gender",
  age_group: "Age",
  date_from: "From",
  date_to: "To",
};

const NOT_GIVEN: Choice = { value: "not_given", label: "Not given" };

const AGE_GROUPS: Choice[] = [
  { value: "18-24", label: "18-24" },
  { value: "25-34", label: "25-34" },
  { value: "35-44", label: "35-44" },
  { value: "45-54", label: "45-54" },
  { value: "55+", label: "55+" },
  NOT_GIVEN,
];

/** First and last day of a month: "2026-10" -> 2026-10-01 to 2026-10-31. */
function monthRange(month: string): { date_from: string; date_to: string } {
  const [year, number] = month.split("-").map(Number);
  const lastDay = new Date(year, number, 0).getDate();
  return { date_from: `${month}-01`, date_to: `${month}-${String(lastDay).padStart(2, "0")}` };
}

/** Labourers by trade, project, gender and age group, with days worked and pay. Every chart filters the page. */
export default function InsightsPage() {
  const { can } = useAuth();
  const { labourer_titles, genders } = useChoices();
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [measure, setMeasure] = useState<Measure>("labourers");
  const stats = useApi<LabourStats>(can("stats.view") ? "/stats/labourers" : null, filters);

  const data = stats.data;
  const projectOptions = (data?.projects || []).map((project) => ({ value: project.id, label: project.name }));
  const genderOptions = [...genders, NOT_GIVEN];
  const activeMonth =
    data?.by_month.find((month) => {
      const range = monthRange(month.month);
      return range.date_from === filters.date_from && range.date_to === filters.date_to;
    })?.month || "";
  const activeFilters = (Object.keys(filters) as FilterName[]).filter((name) => filters[name]);

  /** Set one filter, or clear it with "". */
  const handleFilter = (name: FilterName, value: string) => {
    setFilters((current) => ({ ...current, [name]: value }));
  };

  /** Filter to a month, or clear the dates with "". */
  const handleMonth = (month: string) => {
    setFilters((current) => ({ ...current, ...(month ? monthRange(month) : { date_from: "", date_to: "" }) }));
  };

  /** The value of a filter as words, for the chips above the charts. */
  const filterText = (name: FilterName): string => {
    const value = filters[name];
    if (name === "project_id") {
      return choiceLabel(projectOptions, value);
    }
    if (name === "trade") {
      return choiceLabel(labourer_titles, value);
    }
    if (name === "gender") {
      return choiceLabel(genderOptions, value);
    }
    if (name === "date_from" || name === "date_to") {
      return formatDate(value);
    }
    return choiceLabel(AGE_GROUPS, value);
  };

  if (!can("stats.view")) {
    return (
      <>
        <PageHeader title="Insights" />
        <Card>
          <EmptyState title="Insights are for the main contractor and the super admin" />
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Insights"
        description={
          data?.scope === "all"
            ? "Labourers across every project: trades, days worked and pay."
            : "Labourers on your projects: trades, days worked and pay."
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Select
          label="Project"
          options={projectOptions}
          placeholder="All projects"
          value={filters.project_id}
          onChange={(event) => handleFilter("project_id", event.target.value)}
        />
        <Select
          label="Trade"
          options={labourer_titles}
          placeholder="All trades"
          value={filters.trade}
          onChange={(event) => handleFilter("trade", event.target.value)}
        />
        <Select
          label="Gender"
          options={genderOptions}
          placeholder="Everyone"
          value={filters.gender}
          onChange={(event) => handleFilter("gender", event.target.value)}
        />
        <Select
          label="Age group"
          options={AGE_GROUPS}
          placeholder="All ages"
          value={filters.age_group}
          onChange={(event) => handleFilter("age_group", event.target.value)}
        />
        <Input
          label="From"
          type="date"
          value={filters.date_from}
          onChange={(event) => handleFilter("date_from", event.target.value)}
        />
        <Input
          label="To"
          type="date"
          value={filters.date_to}
          onChange={(event) => handleFilter("date_to", event.target.value)}
        />
      </div>

      {activeFilters.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {activeFilters.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => handleFilter(name, "")}
              className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100"
            >
              {FILTER_LABELS[name]}: {filterText(name)}
              <X className="size-3.5" aria-label="Remove filter" />
            </button>
          ))}
          <Button variant="ghost" size="sm" onClick={() => setFilters(NO_FILTERS)}>
            Clear all
          </Button>
        </div>
      )}

      {stats.loading && (
        <Card>
          <Loading />
        </Card>
      )}
      {stats.error && (
        <Card>
          <ErrorState message={stats.error} onRetry={stats.reload} />
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Projects" value={data.totals.projects} />
            <Stat label="Registered" value={data.totals.registered} hint="New labourers in this period" />
            <Stat label="Labourers working" value={data.totals.labourers} />
            <Stat label="Days worked" value={data.totals.days_worked.toLocaleString("en-KE")} />
            <Stat label="Amount paid" value={formatMoney(data.totals.amount_paid)} />
          </div>

          {data.totals.labourers === 0 && data.totals.registered === 0 ? (
            <Card>
              <EmptyState title="No labourers for these filters">
                {activeFilters.length > 0 ? "Try removing a filter." : "Labourers show here once they are added to works."}
              </EmptyState>
            </Card>
          ) : (
            <>
              <div>
                <Tabs tabs={MEASURES} active={measure} onChange={(id) => setMeasure(id as Measure)} />
                <div className="grid gap-6 lg:grid-cols-3">
                  <Card title="By trade" description="Click a trade to filter the page.">
                    <BarList
                      items={data.by_trade}
                      measure={measure}
                      active={filters.trade}
                      onSelect={(key) => handleFilter("trade", key)}
                    />
                  </Card>
                  <Card title="By gender" description="Only counted in totals.">
                    <BarList
                      items={data.by_gender}
                      measure={measure}
                      active={filters.gender}
                      onSelect={(key) => handleFilter("gender", key)}
                    />
                  </Card>
                  <Card title="By age group" description="Only counted in totals.">
                    <BarList
                      items={data.by_age_group}
                      measure={measure}
                      active={filters.age_group}
                      onSelect={(key) => handleFilter("age_group", key)}
                    />
                  </Card>
                </div>
              </div>

              <Card
                title="Over time"
                description={
                  activeMonth ? `Showing ${monthLabel(activeMonth)}. Click it again to see every month.` : "Click a month to filter the page."
                }
              >
                <MonthChart months={data.by_month} active={activeMonth} onSelect={handleMonth} />
              </Card>

              <Card title="By project" description="Click a project or a trade to filter the page.">
                {data.by_project.length === 0 ? (
                  <EmptyState title="No projects" />
                ) : (
                  <ProjectTable
                    projects={data.by_project}
                    activeProject={filters.project_id}
                    activeTrade={filters.trade}
                    onSelectProject={(projectId) => handleFilter("project_id", projectId)}
                    onSelectTrade={(trade) => handleFilter("trade", trade)}
                  />
                )}
              </Card>

              <Card title="Most repeated labourers" description="Labourers who came back for the most works.">
                {data.top_labourers.length === 0 ? (
                  <EmptyState title="No labourers on works yet" />
                ) : (
                  <TopLabourersTable labourers={data.top_labourers} />
                )}
              </Card>
            </>
          )}

          <p className="text-xs text-zinc-500">
            Gender and age are optional for each labourer and are only shown here as totals, never next to a name.
          </p>
        </div>
      )}
    </>
  );
}
