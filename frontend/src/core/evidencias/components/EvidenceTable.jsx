import Pagination from "@/shared/components/Pagination";
import { getEvidenceStatus } from "@/presets/shared/evidenceConfig";
import { useMemo, useState } from "react";

const pageSize = 8;

const statusStyles = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
};

function EvidenceTable({ config, rows = [] }) {
  const [currentPage, setCurrentPage] = useState(1);
  const hasForestLots = rows.some((row) => row.lote_forestal_id);
  const columns = hasForestLots
    ? [
        ...config.getTableColumns(),
        { key: "lote_forestal", label: "Lote forestal", resolver: (item) => item.lote_forestal_id || "-" },
      ]
    : config.getTableColumns();
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = useMemo(() => rows.slice((safeCurrentPage - 1) * pageSize, safeCurrentPage * pageSize), [rows, safeCurrentPage]);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-black text-[var(--text-main)]">Evidencias registradas</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Mostrando {visibleRows.length} de {rows.length} evidencias.</p>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto rounded-2xl border border-[var(--border)]">
        <table className="min-w-[1100px] w-full text-center text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--bg-surface)] text-center text-xs uppercase tracking-wide text-[var(--text-muted)]">
              {columns.map((column) => <th key={column.key} className="px-3 py-3 text-center">{column.label}</th>)}
              <th className="px-3 py-3 text-center">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((item) => {
              const status = getEvidenceStatus(item);
              return (
                <tr key={item.id} className="border-b border-[#C9D6CF] text-[#1F2937] hover:bg-[var(--bg-surface)]">
                  {columns.map((column) => (
                    <td key={column.key} className="px-3 py-3 text-center">
                      {column.key === "estado" ? (
                        <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${statusStyles[status.tone]}`}>
                          {status.label}
                        </span>
                      ) : column.key === "archivo" ? (
                        item.archivo_url ? <a className="font-semibold text-[#00689B] underline" href={item.archivo_url} target="_blank" rel="noreferrer">Ver</a> : "-"
                      ) : (
                        column.resolver(item)
                      )}
                    </td>
                  ))}
                  <td className="px-3 py-3 text-center">
                    <div className="flex flex-wrap justify-center gap-2">
                      {item.archivo_url ? <a className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1 text-xs font-bold text-[#475467]" href={item.archivo_url} target="_blank" rel="noreferrer">Ver</a> : null}
                      {item.archivo_url ? <a className="rounded-full border border-[var(--primary-dark)] bg-[var(--success-bg)] px-3 py-1 text-xs font-bold text-[var(--primary-dark)]" href={item.archivo_url} download>Descargar</a> : null}
                      <button type="button" disabled title="Disponible en la siguiente fase backend." className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-bold text-slate-400">Vincular</button>
                      <button type="button" disabled title="Disponible en la siguiente fase backend." className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-bold text-slate-400">Revisada</button>
                      <button type="button" disabled title="Disponible en la siguiente fase backend." className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-bold text-slate-400">Incompleta</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Pagination currentPage={safeCurrentPage} onPageChange={setCurrentPage} pageSize={pageSize} totalItems={rows.length} itemLabel="evidencias" />
    </section>
  );
}

export default EvidenceTable;
