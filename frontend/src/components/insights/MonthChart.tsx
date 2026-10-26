"use client";

import { useState } from "react";
import { EmptyState } from "@/components/ui/States";
import { Tabs } from "@/components/ui/Tabs";
import type { MonthStats } from "@/lib/types";

type MonthMeasure = "labourers" | "days_worked" | "registered";

const MONTH_MEASURES: { id: MonthMeasure; label: string }[] = [
  { id: "labourers", label: "Labourers working" },
  { id: "days_worked", label: "Days worked" },
  { id: "registered", label: "Newly registered" },
];

/** "2026-10" -> "Oct 2026" */
export function monthLabel(month: string): string {
  const [year, number] = month.split("-").map(Number);
  return new Date(year, number - 1, 1).toLocaleDateString("en-KE", { month: "short", year: "numeric" });
}

interface MonthChartProps {
  months: MonthStats[];
  active: string; // "2026-10" when the page is filtered to that month, or ""
  onSelect: (month: string) => void;
}

/** One column per month. Clicking a column filters the page to that month; clicking it again clears it. */
export function MonthChart({ months, active, onSelect }: MonthChartProps) {
  const [measure, setMeasure] = useState<MonthMeasure>("labourers");

  if (months.length === 0) {
    return <EmptyState title="Nothing to show" />;
  }
  const largest = Math.max(...months.map((month) => month[measure]));

  return (
    <>
      <Tabs tabs={MONTH_MEASURES} active={measure} onChange={(id) => setMeasure(id as MonthMeasure)} />
      <div className="overflow-x-auto">
        <div className="flex min-w-max items-end gap-2">
          {months.map((month) => {
            const value = month[measure];
            const height = largest > 0 ? (value / largest) * 100 : 0;
            const selected = month.month === active;
            return (
              <button
                key={month.month}
                type="button"
                aria-pressed={selected}
                title={`${monthLabel(month.month)}: ${value.toLocaleString("en-KE")}`}
                onClick={() => onSelect(selected ? "" : month.month)}
                className={`flex w-14 flex-col items-center gap-1 rounded-lg px-1 pb-1 pt-2 transition-colors ${
                  selected ? "bg-emerald-50" : "hover:bg-zinc-50"
                }`}
              >
                <span className="text-xs font-medium tabular-nums text-zinc-900">{value.toLocaleString("en-KE")}</span>
                <span className="flex h-32 w-6 items-end rounded-md bg-zinc-100">
                  <span
                    className={`block w-full rounded-md ${active && !selected ? "bg-zinc-300" : "bg-emerald-600"}`}
                    style={{ height: `${height}%` }}
                  />
                </span>
                <span className={`text-xs ${selected ? "font-medium text-emerald-800" : "text-zinc-500"}`}>
                  {monthLabel(month.month)}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}
