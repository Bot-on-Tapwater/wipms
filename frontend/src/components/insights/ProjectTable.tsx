import { Table, Td } from "@/components/ui/Table";
import { formatMoney } from "@/lib/format";
import type { ProjectStats } from "@/lib/types";

interface ProjectTableProps {
  projects: ProjectStats[];
  activeProject: string;
  activeTrade: string;
  onSelectProject: (projectId: string) => void;
  onSelectTrade: (trade: string) => void;
}

/** Labourers, days and pay per project, with the trades on it. Clicking a project or a trade filters the page. */
export function ProjectTable({ projects, activeProject, activeTrade, onSelectProject, onSelectTrade }: ProjectTableProps) {
  return (
    <Table headers={["Project", "Labourers", "Days worked", "Amount paid", "Trades"]}>
      {projects.map((project) => {
        const selected = project.id === activeProject;
        return (
          <tr key={project.id} className={selected ? "bg-emerald-50/60" : undefined}>
            <Td>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelectProject(selected ? "" : project.id)}
                className="text-left"
              >
                <span className="block font-medium text-zinc-900 hover:text-emerald-700">{project.name}</span>
                <span className="block text-xs text-zinc-500">{project.location}</span>
              </button>
            </Td>
            <Td className="tabular-nums">{project.labourers}</Td>
            <Td className="tabular-nums">{project.days_worked.toLocaleString("en-KE")}</Td>
            <Td className="tabular-nums">{formatMoney(project.amount_paid)}</Td>
            <Td>
              <div className="flex max-w-md flex-wrap gap-1.5">
                {project.trades.length === 0 && <span className="text-zinc-400">-</span>}
                {project.trades.map((trade) => {
                  const tradeSelected = trade.key === activeTrade;
                  return (
                    <button
                      key={trade.key}
                      type="button"
                      aria-pressed={tradeSelected}
                      onClick={() => onSelectTrade(tradeSelected ? "" : trade.key)}
                      className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${
                        tradeSelected
                          ? "bg-emerald-600 text-white"
                          : "bg-zinc-100 text-zinc-700 hover:bg-emerald-50 hover:text-emerald-700"
                      }`}
                    >
                      {trade.label} · {trade.labourers}
                    </button>
                  );
                })}
              </div>
            </Td>
          </tr>
        );
      })}
    </Table>
  );
}
