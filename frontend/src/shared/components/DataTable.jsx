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
    <section className="rounded-3xl bg-slate-900 border border-slate-800 p-4 sm:p-6">
      <h2 className="text-xl font-semibold mb-4">Datos procesados</h2>

      <div className="overflow-x-auto">
        <table className="min-w-[720px] w-full text-sm">
          <thead className="text-slate-400 border-b border-slate-800">
            <tr>
              <th className="text-left py-3">Empresa</th>
              <th className="text-left py-3">Actividad</th>
              <th className="text-right py-3">Cantidad</th>
              <th className="text-right py-3">Factor</th>
              <th className="text-right py-3">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, index) => (
              <tr key={index} className="border-b border-slate-800/60">
                <td className="py-3">{row.empresa}</td>
                <td className="py-3">{row.actividad}</td>
                <td className="py-3 text-right">
                  {formatNumber(row.cantidad)}
                </td>
                <td className="py-3 text-right">
                  {formatNumber(row.factor_emision, 4)}
                </td>
                <td className="py-3 text-right font-semibold text-emerald-300">
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
