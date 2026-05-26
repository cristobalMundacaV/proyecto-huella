import { useMemo, useState } from "react";

import Pagination from "./Pagination";
import { formatNumber } from "@/shared/utils/formatters";

function DataTable({ rows }) {
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 6;
  const totalPages = Math.max(1, Math.ceil((rows?.length || 0) / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const visibleRows = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * pageSize;
    return rows.slice(startIndex, startIndex + pageSize);
  }, [rows, safeCurrentPage]);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <h2 className="mb-4 text-xl font-semibold text-[var(--text-main)]">Datos procesados</h2>

      <div className="overflow-x-auto">
        <table className="min-w-[720px] w-full text-sm">
          <thead className="border-b border-[var(--border)] text-[var(--text-muted)]">
            <tr>
              <th className="text-left py-3">Constructora</th>
              <th className="text-left py-3">Fuente de emisión</th>
              <th className="text-right py-3">Cantidad</th>
              <th className="text-right py-3">Factor</th>
              <th className="text-right py-3">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, index) => (
              <tr key={index} className="border-b border-[#CBD5D0] text-[var(--text-main)]">
                <td className="py-3">{row.constructora}</td>
                <td className="py-3">{row.fuente_emision}</td>
                <td className="py-3 text-right">
                  {formatNumber(row.cantidad)}
                </td>
                <td className="py-3 text-right">
                  {formatNumber(row.factor_emision, 4)}
                </td>
                <td className="py-3 text-right font-semibold text-[var(--primary-dark)]">
                  {formatNumber(row.emisiones)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={safeCurrentPage}
        itemLabel="registros"
        onPageChange={setCurrentPage}
        pageSize={pageSize}
        totalItems={rows.length}
      />
    </section>
  );
}

export default DataTable;
