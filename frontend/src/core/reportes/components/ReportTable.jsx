import { useMemo, useState } from "react";

import Pagination from "@/shared/components/Pagination";

const rowsPerPage = 10;

function ReportTable({ report, reportConfig }) {
  const [currentPage, setCurrentPage] = useState(1);
  const columns = reportConfig.tableColumns || [];
  const totalRows = report.rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = useMemo(
    () => report.rows.slice((safeCurrentPage - 1) * rowsPerPage, safeCurrentPage * rowsPerPage),
    [report.rows, safeCurrentPage]
  );

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[0_18px_45px_var(--shadow)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">Detalle del reporte</h2>
      <p className="mt-1 text-sm text-[var(--text-muted)]">{totalRows} registros encontrados.</p>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-[var(--border)]">
        <table className="w-full min-w-[1050px]">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
              {columns.map((column) => (
                <th key={column.key} className={`px-4 py-3 ${column.align === "right" ? "text-right" : "text-left"}`}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, index) => (
              <tr key={`${row.id || index}-${row.fecha || "sin-fecha"}`} className="border-b border-[#E2E8F0] text-[#1F2937] hover:bg-[var(--bg-surface)]">
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-3 ${column.align === "right" ? "text-right" : "text-left"} ${column.key === "emisiones" ? "font-black text-[#075985]" : ""}`}>
                    {column.resolver(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination currentPage={safeCurrentPage} itemLabel="registros" onPageChange={setCurrentPage} pageSize={rowsPerPage} totalItems={totalRows} />
    </section>
  );
}

export default ReportTable;
