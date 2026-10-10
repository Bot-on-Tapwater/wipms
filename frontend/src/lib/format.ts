// Helpers for showing money, dates and labels the same way everywhere.

import type { Choice } from "./types";

const moneyFormat = new Intl.NumberFormat("en-KE", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** "1500" -> "KES 1,500.00" */
export function formatMoney(value: string | number | null | undefined): string {
  const amount = Number(value || 0);
  return `KES ${moneyFormat.format(amount)}`;
}

/** ISO date -> "7 Oct 2026" */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleDateString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** ISO date -> "7 Oct 2026, 14:05" */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "main-contractor" or "tile_laying" -> "Main contractor" / "Tile laying" */
export function humanize(value: string): string {
  const text = value.replace(/[_-]/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Label for a choice value, e.g. a labourer title or task category. */
export function choiceLabel(choices: Choice[] | undefined, value: string): string {
  const match = choices?.find((choice) => choice.value === value);
  return match ? match.label : humanize(value);
}
