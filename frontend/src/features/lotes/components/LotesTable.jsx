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
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <h2 className="mb-4 text-xl font-semibold">Tabla de lotes</h2>

      <div className="overflow-x-auto">
        <table className="min-w-[980px] w-full text-sm">
          <thead className="border-b border-slate-800 text-slate-400">
            <tr>
              <th className="py-3 text-left">ID lote</th>
              <th className="py-3 text-left">Empresa</th>
              <th className="py-3 text-left">Especie</th>
              <th className="py-3 text-right">Volumen</th>
              <th className="py-3 text-right">Emisiones</th>
              <th className="py-3 text-right">CO2 almacenado</th>
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
                  className={`cursor-pointer border-b border-slate-800/60 transition focus:outline-none focus:ring-2 focus:ring-emerald-400/40 ${
                    isSelected
                      ? "bg-emerald-400/10 text-emerald-100 ring-1 ring-emerald-400/20"
                      : "hover:bg-slate-800/60 focus:bg-slate-800/60"
                  }`}
                >
                  <td className="py-3">
                    <span className="font-semibold text-emerald-300">
                      {lote.id_lote}
                    </span>
                  </td>
                  <td className="py-3">{lote.empresa_aserradero}</td>
                  <td className="py-3">{lote.especie}</td>
                  <td className="py-3 text-right">
                    {formatNumber(Number(lote.volumen_m3))} m3
                  </td>
                  <td className="py-3 text-right font-semibold text-cyan-200">
                    {formatNumber(Number(lote.emisiones_kg_co2e || 0))} kg CO2e
                  </td>
                  <td className="py-3 text-right font-semibold text-lime-200">
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
                          ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200 hover:bg-emerald-400/20"
                          : "border-slate-700 bg-slate-950 text-slate-300 hover:border-emerald-400/30 hover:bg-slate-800 hover:text-slate-100"
                      }`}
                      aria-label={`Abrir detalle del lote ${lote.id_lote}`}
                    >
                      Ver detalle
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
