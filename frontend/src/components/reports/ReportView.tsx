import { Card, Stat } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { Table, Td } from "@/components/ui/Table";
import { formatDateTime } from "@/lib/format";
import type { Report } from "@/lib/types";

/** Shows a report returned by GET /reports/{type}?format=json. */
export function ReportView({ report }: { report: Report }) {
  return (
    <Card
      title={report.title}
      description={`Generated ${formatDateTime(report.generated_at)} by ${report.generated_by}`}
    >
      {report.filters.length > 0 && (
        <p className="mb-4 text-sm text-zinc-600">
          {report.filters.map((item) => `${item.label}: ${item.value}`).join(" · ")}
        </p>
      )}
      {report.summary.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {report.summary.map((item) => (
            <Stat key={item.label} label={item.label} value={item.value} />
          ))}
        </div>
      )}
      {report.rows.length === 0 ? (
        <EmptyState title="Nothing to show for these filters" />
      ) : (
        <Table headers={report.columns}>
          {report.rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <Td key={cellIndex}>{cell}</Td>
              ))}
            </tr>
          ))}
        </Table>
      )}
    </Card>
  );
}
