// The three numbers the Insights charts can show: labourers, days worked
// or amount paid.

import { formatMoney } from "@/lib/format";
import type { StatsBucket } from "@/lib/types";

export type Measure = "labourers" | "days_worked" | "amount_paid";

export const MEASURES: { id: Measure; label: string }[] = [
  { id: "labourers", label: "Labourers" },
  { id: "days_worked", label: "Days worked" },
  { id: "amount_paid", label: "Amount paid" },
];

/** The number a bar stands for. */
export function measureValue(item: Pick<StatsBucket, Measure>, measure: Measure): number {
  return Number(item[measure]);
}

/** 1500 -> "1,500", or "KES 1,500.00" for money. */
export function formatMeasure(value: number, measure: Measure): string {
  if (measure === "amount_paid") {
    return formatMoney(value);
  }
  return value.toLocaleString("en-KE");
}
