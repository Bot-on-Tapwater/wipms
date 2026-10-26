import { EmptyState } from "@/components/ui/States";
import type { StatsBucket } from "@/lib/types";
import { formatMeasure, measureValue, type Measure } from "./measure";

interface BarListProps {
  items: StatsBucket[];
  measure: Measure;
  active: string; // key of the bar the page is filtered by, or ""
  onSelect: (key: string) => void;
}

/** Horizontal bars, one per group. Clicking a bar filters the page by it; clicking it again clears it. */
export function BarList({ items, measure, active, onSelect }: BarListProps) {
  if (items.length === 0) {
    return <EmptyState title="Nothing to show" />;
  }
  const largest = Math.max(...items.map((item) => measureValue(item, measure)));

  return (
    <ul className="-mx-2 space-y-1">
      {items.map((item) => {
        const value = measureValue(item, measure);
        const width = largest > 0 ? (value / largest) * 100 : 0;
        const selected = item.key === active;
        return (
          <li key={item.key}>
            <button
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(selected ? "" : item.key)}
              className={`w-full rounded-lg px-2 py-1.5 text-left transition-colors ${
                selected ? "bg-emerald-50" : "hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-baseline justify-between gap-3 text-sm">
                <span className={`truncate ${selected ? "font-medium text-emerald-800" : "text-zinc-700"}`}>
                  {item.label}
                </span>
                <span className="shrink-0 font-medium tabular-nums text-zinc-900">{formatMeasure(value, measure)}</span>
              </span>
              <span className="mt-1 block h-2 rounded-full bg-zinc-100">
                <span
                  className={`block h-2 rounded-full ${active && !selected ? "bg-zinc-300" : "bg-emerald-600"}`}
                  style={{ width: `${width}%` }}
                />
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
