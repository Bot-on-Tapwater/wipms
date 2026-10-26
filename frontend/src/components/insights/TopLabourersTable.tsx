import { Table, Td } from "@/components/ui/Table";
import { formatMoney } from "@/lib/format";
import type { TopLabourer } from "@/lib/types";

/** Labourers who came back for the most works, and what they were paid. */
export function TopLabourersTable({ labourers }: { labourers: TopLabourer[] }) {
  return (
    <Table headers={["#", "Labourer", "Trade", "Works", "Projects", "Days worked", "Amount paid"]}>
      {labourers.map((labourer, index) => (
        <tr key={labourer.id}>
          <Td className="tabular-nums text-zinc-500">{index + 1}</Td>
          <Td className="font-medium text-zinc-900">{labourer.name}</Td>
          <Td>{labourer.trade}</Td>
          <Td className="tabular-nums">{labourer.works}</Td>
          <Td className="tabular-nums">{labourer.projects}</Td>
          <Td className="tabular-nums">{labourer.days_worked.toLocaleString("en-KE")}</Td>
          <Td className="tabular-nums">{formatMoney(labourer.amount_paid)}</Td>
        </tr>
      ))}
    </Table>
  );
}
