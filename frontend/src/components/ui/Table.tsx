// Simple responsive table: scrolls sideways on small screens.
//
//   <Table headers={["Name", "Amount"]}>
//     <tr><Td>Jane</Td><Td>KES 100.00</Td></tr>
//   </Table>

export function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="-mx-4 overflow-x-auto sm:-mx-5">
      <table className="w-full min-w-max text-left text-sm">
        <thead>
          <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500">
            {headers.map((header, index) => (
              <th key={`${header}-${index}`} className="px-4 py-2 font-medium first:pl-4 sm:first:pl-5">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">{children}</tbody>
      </table>
    </div>
  );
}

/** One table cell, lined up with the headers. */
export function Td({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-2.5 align-middle text-zinc-700 first:pl-4 sm:first:pl-5 ${className}`}>{children}</td>;
}
