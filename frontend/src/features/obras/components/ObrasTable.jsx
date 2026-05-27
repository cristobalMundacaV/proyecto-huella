import { useEffect, useMemo, useState } from "react";

import Pagination from "@/shared/components/Pagination";
import { formatNumber } from "@/shared/utils/formatters";

function ObrasTable({ loading, obras, onOpenDetail, onSelectObra, selectedObra }) {
  const pageSize = 8;
  const [currentPage, setCurrentPage] = useState(1);

  const handleRowKeyDown = (event, codigoObra) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectObra(codigoObra);
    }
  };

  const totalPages = Math.max(1, Math.ceil((obras?.length || 0) / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const visibleObras = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * pageSize;
    return (obras || []).slice(startIndex, startIndex + pageSize);
  }, [obras, safeCurrentPage]);

  useEffect(() => {
    setCurrentPage(1);
  }, [obras]);

  const getEvidenceCount = (obra) =>
    obra.evidencias_count ?? obra.evidencias?.length ?? 0;

  return (
    <section className="premium-card premium-card-interactive slide-up rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <h2 className="mb-4 text-xl font-semibold text-[var(--text-main)]">Obras registradas</h2>

      <div className="premium-table-wrapper overflow-x-auto">
        <table className="premium-table min-w-[940px] w-full table-fixed text-sm">
          <colgroup>
            <col className="w-[15%]" />
            <col className="w-[22%]" />
            <col className="w-[22%]" />
            <col className="w-[18%]" />
            <col className="w-[10%]" />
            <col className="w-[13%]" />
          </colgroup>
          <thead className="border-b border-[var(--border)] text-[var(--text-muted)]">
            <tr>
              <th className="px-4 py-3 text-center">Código</th>
              <th className="px-4 py-3 text-left">Obra / proyecto</th>
              <th className="px-4 py-3 text-left">Constructora</th>
              <th className="px-4 py-3 text-right">Emisiones</th>
              <th className="px-4 py-3 text-center">Evidencias</th>
              <th className="px-4 py-3 text-center">Estado</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan="6" className="py-8 text-center text-slate-400">
                  Cargando obras...
                </td>
              </tr>
            )}

            {!loading && obras.length === 0 && (
              <tr>
                <td colSpan="6" className="py-8 text-center text-slate-400">
                  <p>Aún no hay obras registradas.</p>
                  <p className="mt-1 text-sm">
                    Crea una obra para comenzar a medir emisiones por materiales, transporte, maquinaria, energía y residuos.
                  </p>
                </td>
              </tr>
            )}

            {visibleObras.map((obra) => {
              const isSelected = obra.codigo_obra === selectedObra?.codigo_obra;
              const evidenceCount = getEvidenceCount(obra);

              return (
                <tr
                  key={obra.codigo_obra}
                  onClick={() => onSelectObra(obra.codigo_obra)}
                  onKeyDown={(event) => handleRowKeyDown(event, obra.codigo_obra)}
                  tabIndex={0}
                  aria-label={`Seleccionar obra ${obra.codigo_obra}`}
                  aria-selected={isSelected}
                  className={`cursor-pointer border-b border-[#CBD5D0] text-[var(--text-main)] transition focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/40 premium-table-row hover:bg-[var(--success-bg)]/60 ${
                    isSelected
                      ? "bg-[var(--success-bg)] ring-1 ring-[var(--primary)]/25"
                      : "hover:bg-[var(--bg-surface)] focus:bg-[var(--bg-surface)]"
                  }`}
                >
                  <td className="px-4 py-4 text-center align-middle">
                    <span className="inline-flex max-w-full items-center justify-center rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black text-[var(--primary-dark)] shadow-[0_6px_14px_rgba(15,23,42,0.04)]">
                      {obra.codigo_obra}
                    </span>
                  </td>
                  <td className="px-4 py-4 align-middle font-semibold text-[var(--text-main)]">
                    {obra.tipo_proyecto || "Obra registrada"}
                  </td>
                  <td className="px-4 py-4 align-middle text-[var(--text-main)]">
                    {obra.constructora_nombre || "Constructora activa"}
                  </td>
                  <td className="px-4 py-4 text-right align-middle font-black text-[#075985]">
                    {formatNumber(Number(obra.emisiones_kg_co2e || 0))} kg CO2e
                  </td>
                  <td className="px-4 py-4 text-center align-middle font-bold text-[var(--text-main)]">
                    {formatNumber(evidenceCount, 0)}
                  </td>
                  <td className="px-4 py-4 text-center align-middle">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenDetail(obra.codigo_obra);
                      }}
                      className={`premium-badge mx-auto inline-flex min-w-[132px] items-center justify-center rounded-full border px-3 py-1.5 text-center text-xs font-bold transition ${
                        evidenceCount > 0
                          ? "border-emerald-200 bg-[#D9F0E6] text-[var(--primary-dark)] hover:bg-[var(--success-bg)]"
                          : "border-slate-200 bg-slate-50 text-slate-500 hover:border-[var(--primary)]/30 hover:bg-[var(--success-bg)] hover:text-[var(--primary-dark)]"
                      }`}
                      aria-label={`Abrir detalle de obra ${obra.codigo_obra}`}
                    >
                      {evidenceCount > 0 ? "Con evidencias" : "En seguimiento"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={safeCurrentPage}
        itemLabel="obras"
        onPageChange={setCurrentPage}
        pageSize={pageSize}
        totalItems={obras.length}
      />
    </section>
  );
}

export default ObrasTable;
