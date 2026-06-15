import { useMemo, useState } from "react";

import Pagination from "@/shared/components/Pagination";
import {
  getImportErrors,
  getImportRowStatus,
  getImportWarnings,
} from "@/presets/shared/importConfig";

const PAGE_SIZE = 8;

function ImportPreviewTable({ columns = [], onRowsChange, rows = [] }) {
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);

  const visibleRows = useMemo(
    () => rows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [rows, safePage]
  );

  if (!rows.length) return null;

  function updateCell(rowNumber, column, value) {
    const nextRows = rows.map((row) =>
      row.row_number === rowNumber
        ? {
          ...row,
          data: {
            ...(row.data || {}),
            [column]: value,
          },
        }
        : row
    );

    onRowsChange?.(nextRows);
  }

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
            Previsualización editable
          </p>
          <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">
            Revisa y corrige antes de importar
          </h2>
          <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
            {rows.length} filas detectadas · {PAGE_SIZE} por página.
          </p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-[var(--border)]">
        <table className="w-full min-w-[1100px] text-center text-sm">
          <thead className="bg-[var(--bg-surface)] text-center text-xs uppercase tracking-wide text-[var(--text-muted)]">
            <tr>
              <th className="px-4 py-3 text-center">Fila</th>
              <th className="px-4 py-3 text-center">Estado</th>
              {columns.map((column) => (
                <th key={column} className="px-4 py-3 text-center">
                  {column}
                </th>
              ))}
              <th className="px-4 py-3 text-center">Mensajes</th>
            </tr>
          </thead>

          <tbody>
            {visibleRows.map((row) => {
              const status = getImportRowStatus(row);
              const messages = [...getImportErrors(row), ...getImportWarnings(row)];

              return (
                <tr key={row.row_number} className="border-t border-[var(--border)]">
                  <td className="px-4 py-3 text-center font-black">
                    {row.row_number}
                  </td>

                  <td className="px-4 py-3 text-center">
                    <span
                      className={`rounded-full border px-2.5 py-1 text-xs font-black ${status.tone === "success"
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : status.tone === "warning"
                            ? "border-amber-200 bg-amber-50 text-amber-700"
                            : "border-rose-200 bg-rose-50 text-rose-700"
                        }`}
                    >
                      {status.label}
                    </span>
                  </td>

                  {columns.map((column) => (
                    <td key={column} className="px-3 py-3 text-center">
                      <input
                        value={row.data?.[column] || ""}
                        onChange={(event) =>
                          updateCell(row.row_number, column, event.target.value)
                        }
                        className="w-full min-w-[120px] rounded-xl border border-[var(--border)] bg-white px-3 py-2 text-center text-xs font-semibold text-[var(--text-main)] outline-none transition focus:border-emerald-300 focus:ring-4 focus:ring-emerald-100"
                      />
                    </td>
                  ))}

                  <td className="px-4 py-3 text-center text-xs font-semibold text-rose-700">
                    {messages.length ? messages.join("; ") : "Lista para importar"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={safePage}
        onPageChange={setCurrentPage}
        pageSize={PAGE_SIZE}
        totalItems={rows.length}
        itemLabel="filas"
      />
    </section>
  );
}

export default ImportPreviewTable;