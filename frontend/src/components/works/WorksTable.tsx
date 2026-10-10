"use client";

import Link from "next/link";
import { Badge, PaymentStatusBadge } from "@/components/ui/Badge";
import { Table, Td } from "@/components/ui/Table";
import { choiceLabel, formatMoney } from "@/lib/format";
import type { Work } from "@/lib/types";
import { useChoices } from "@/lib/useChoices";

/** Number of the four work approvals that have been given. */
export function approvalCount(work: Work): number {
  const approvals = [
    work.consultant_approval,
    work.contractor_supervisor_approval,
    work.attendance_approval,
    work.cost_approval,
  ];
  return approvals.filter(Boolean).length;
}

/** Table of works; each title links to the work page. */
export function WorksTable({ works }: { works: Work[] }) {
  const { task_categories } = useChoices();

  return (
    <Table headers={["Work", "Category", "Subcontractor", "Total cost", "Approvals", "Payment"]}>
      {works.map((work) => {
        const approved = approvalCount(work);
        return (
          <tr key={work.id} className="hover:bg-zinc-50">
            <Td>
              <Link href={`/works/${work.id}`} className="font-medium text-zinc-900 hover:text-emerald-700 hover:underline">
                {work.title}
              </Link>
            </Td>
            <Td>{choiceLabel(task_categories, work.category)}</Td>
            <Td>{work.assigned_subcontractor?.full_name || <span className="text-zinc-400">Not assigned</span>}</Td>
            <Td>{formatMoney(work.total_cost)}</Td>
            <Td>
              <Badge tone={approved === 4 ? "green" : "gray"}>{approved} of 4</Badge>
            </Td>
            <Td>
              <PaymentStatusBadge status={work.payment_status} />
            </Td>
          </tr>
        );
      })}
    </Table>
  );
}
