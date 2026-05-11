import { useEffect, useMemo, useState } from "react";

import Pagination from "@/shared/components/Pagination";
import { formatNumber } from "@/shared/utils/formatters";

function LotesTable({ loading, lotes, onOpenDetail, onSelectLote, selectedLote }) {
  const pageSize = 8;
  const [currentPage, setCurrentPage] = useState(1);

  const handleRowKeyDown = (event, idLote) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectLote(idLote);
    }
  };

  const totalPages = Math.max(1, Math.ceil((lotes?.length || 0) / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const visibleLotes = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * pageSize;
    return (lotes || []).slice(startIndex, startIndex + pageSize);
  }, [lotes, safeCurrentPage]);

  useEffect(() => {
    setCurrentPage(1);
  }, [lotes]);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <h2 className="mb-4 text-xl font-semibold text-[var(--text-main)]">Lotes registrados</h2>

      <div className="overflow-x-auto">
        <table className="min-w-[980px] w-full text-sm">
          <thead className="border-b border-[var(--border)] text-[var(--text-muted)]">
            <tr>
              <th className="py-3 text-left">ID lote</th>
              <th className="py-3 text-left">Empresa</th>
              <th className="py-3 text-left">Especie</th>
              <th className="py-3 text-right">Volumen</th>
              <th className="py-3 text-right">Emisiones</th>
              <th className="py-3 text-right">Carbono almacenado</th>
              <th className="py-3 text-right">Detalle</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan="7" className="py-8 text-center text-slate-400">
                  Cargando lotes...
                </td>
              </tr>
            )}

            {!loading && lotes.length === 0 && (
              <tr>
                <td colSpan="7" className="py-8 text-center text-slate-400">
                  No hay lotes registrados.
                </td>
              </tr>
            )}

            {visibleLotes.map((lote) => {
              const isSelected = lote.id_lote === selectedLote?.id_lote;

              return (
                <tr
                  key={lote.id_lote}
                  onClick={() => onSelectLote(lote.id_lote)}
                  onKeyDown={(event) => handleRowKeyDown(event, lote.id_lote)}
                  tabIndex={0}
                  aria-label={`Seleccionar lote ${lote.id_lote}`}
                  aria-selected={isSelected}
                  className={`cursor-pointer border-b border-[#CBD5D0] text-[var(--text-main)] transition focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/40 ${
                    isSelected
                      ? "bg-[var(--success-bg)] ring-1 ring-[var(--primary)]/25"
                      : "hover:bg-[var(--bg-surface)] focus:bg-[var(--bg-surface)]"
                  }`}
                >
                  <td className="py-3">
                    <span className="font-semibold text-[var(--primary-dark)]">
                      {lote.id_lote}
                    </span>
                  </td>
                  <td className="py-3">{lote.empresa_aserradero}</td>
                  <td className="py-3">{lote.especie}</td>
                  <td className="py-3 text-right">
                    {formatNumber(Number(lote.volumen_m3))} m3
                  </td>
                  <td className="py-3 text-right font-semibold text-[#075985]">
                    {formatNumber(Number(lote.emisiones_kg_co2e || 0))} kg CO2e
                  </td>
                  <td className="py-3 text-right font-semibold text-[#3F6212]">
                    {formatNumber(Number(lote.co2_almacenado_kg || 0))} kg
                  </td>
                  <td className="py-3">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenDetail(lote.id_lote);
                      }}
                      className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold transition ${
                        isSelected
                          ? "border-[var(--primary)]/30 bg-[#D9F0E6] text-[var(--primary-dark)] hover:bg-[var(--success-bg)]"
                          : "border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)] hover:border-[var(--primary)]/30 hover:bg-[var(--success-bg)] hover:text-[var(--primary-dark)]"
                      }`}
                      aria-label={`Abrir detalle del lote ${lote.id_lote}`}
                    >
                      Revisar lote
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
        itemLabel="lotes"
        onPageChange={setCurrentPage}
        pageSize={pageSize}
        totalItems={lotes.length}
      />
    </section>
  );
}

export default LotesTable;
