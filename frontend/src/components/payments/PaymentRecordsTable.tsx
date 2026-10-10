import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Table, Td } from "@/components/ui/Table";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";
import type { PaymentRecord } from "@/lib/types";

interface PaymentRecordsTableProps {
  records: PaymentRecord[];
  showWork?: boolean; // add a link to the work each payment belongs to
}

/** Every payment attempt, successful or failed. */
export function PaymentRecordsTable({ records, showWork = false }: PaymentRecordsTableProps) {
  return (
    <Table
      headers={["Date", "Recipient", "Type", "Amount", "Result", "Reference", ...(showWork ? ["Work"] : [])]}
    >
      {records.map((record) => (
        <tr key={record.id}>
          <Td>{formatDateTime(record.paid_at || record.created_at)}</Td>
          <Td>
            <p className="font-medium text-zinc-900">{record.recipient_name}</p>
            <p className="text-xs text-zinc-500">{record.recipient_phone}</p>
          </Td>
          <Td>{humanize(record.payment_type)}</Td>
          <Td className="font-medium">
            {formatMoney(record.successful ? record.amount_paid : record.amount_requested)}
          </Td>
          <Td>
            {record.successful ? (
              <Badge tone="green">Paid</Badge>
            ) : (
              <div>
                <Badge tone={record.is_retried ? "gray" : "red"}>{record.is_retried ? "Failed, retried" : "Failed"}</Badge>
                {record.failure_reason && (
                  <p className="mt-1 max-w-xs text-xs text-zinc-500">{record.failure_reason}</p>
                )}
              </div>
            )}
          </Td>
          <Td className="text-xs text-zinc-500">{record.provider_reference || "-"}</Td>
          {showWork && (
            <Td>
              <Link href={`/works/${record.work_id}`} className="text-emerald-700 hover:underline">
                Open
              </Link>
            </Td>
          )}
        </tr>
      ))}
    </Table>
  );
}
