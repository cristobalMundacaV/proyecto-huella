import { useMemo, useState } from "react";

import Pagination from "@/shared/components/Pagination";
import { formatNumber } from "@/shared/utils/formatters";

const PAGE_SIZE = 8;

function FactorCatalog({ config, factors = [], onCreate, onEdit, onToggleActive }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState({
    categoria: "",
    module: "",
    unidad: "",
    fuente: "",
    activo: "",
    validation: "",
  });

  const filtered = useMemo(() => {
    return factors.filter((factor) => {
      if (filters.categoria && factor.categoria !== filters.categoria) return false;
      if (filters.module && factor.module !== filters.module) return false;
      if (filters.unidad && !String(factor.unidad || "").toLowerCase().includes(filters.unidad.toLowerCase())) return false;
      if (filters.fuente && !String(factor.fuente || "").toLowerCase().includes(filters.fuente.toLowerCase())) return false;
      if (filters.activo && String(Boolean(factor.activo)) !== filters.activo) return false;
      if (filters.validation && String(Boolean(factor.metadata?.requires_validation)) !== filters.validation) return false;
      return true;
    });
  }, [factors, filters]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const visibleRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const updateFilter = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
    setCurrentPage(1);
  };

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-premium)]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-black text-[var(--text-main)]">Catálogo de factores</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {filtered.length} factores visibles · {PAGE_SIZE} por página
          </p>
        </div>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-2xl bg-[var(--primary)] px-4 py-3 text-sm font-black text-white"
        >
          Nuevo factor
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <select className="input-factor" value={filters.categoria} onChange={(event) => updateFilter("categoria", event.target.value)}>
          <option value="">Categoría</option>
          {config.categories.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>

        <select className="input-factor" value={filters.module} onChange={(event) => updateFilter("module", event.target.value)}>
          <option value="">Módulo</option>
          {config.modules.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>

        <input className="input-factor" placeholder="Unidad" value={filters.unidad} onChange={(event) => updateFilter("unidad", event.target.value)} />
        <input className="input-factor" placeholder="Fuente" value={filters.fuente} onChange={(event) => updateFilter("fuente", event.target.value)} />

        <select className="input-factor" value={filters.activo} onChange={(event) => updateFilter("activo", event.target.value)}>
          <option value="">Activo</option>
          <option value="true">Activo</option>
          <option value="false">Inactivo</option>
        </select>

        <select className="input-factor" value={filters.validation} onChange={(event) => updateFilter("validation", event.target.value)}>
          <option value="">Validación</option>
          <option value="true">Requiere validación</option>
          <option value="false">Validado</option>
        </select>
      </div>

      <div className="mt-5 overflow-x-auto rounded-2xl border border-[var(--border)]">
        <table className="w-full min-w-[1100px] text-center text-sm">
          <thead className="bg-[var(--bg-surface)] text-center text-xs uppercase tracking-wide text-[var(--text-muted)]">
            <tr>
              <th className="px-4 py-3 text-center">Categoría</th>
              <th className="px-4 py-3 text-center">Actividad</th>
              <th className="px-4 py-3 text-center">Unidad</th>
              <th className="px-4 py-3 text-center">Factor</th>
              <th className="px-4 py-3 text-center">Fuente</th>
              <th className="px-4 py-3 text-center">Año</th>
              <th className="px-4 py-3 text-center">Alcance</th>
              <th className="px-4 py-3 text-center">Estado</th>
              <th className="px-4 py-3 text-center">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((factor) => (
              <tr key={factor.id} className="border-t border-[var(--border)]">
                <td className="px-4 py-3 text-center">{factor.categoria}</td>
                <td className="px-4 py-3 text-center font-semibold">{factor.actividad}</td>
                <td className="px-4 py-3 text-center">{factor.unidad}</td>
                <td className="px-4 py-3 text-center font-black text-sky-700">{formatNumber(factor.factor_emision, 6)}</td>
                <td className="px-4 py-3 text-center">{factor.fuente}</td>
                <td className="px-4 py-3 text-center">{factor.anio}</td>
                <td className="px-4 py-3 text-center">{factor.alcance || "-"}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-black ${factor.activo
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-slate-200 bg-slate-100 text-slate-600"
                    }`}>
                    {factor.metadata?.requires_validation ? "Requiere validación" : factor.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => onEdit?.(factor)}
                      className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black text-sky-700"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => onToggleActive?.(factor)}
                      className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-black text-amber-700"
                    >
                      {factor.activo ? "Desactivar" : "Activar"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {!visibleRows.length && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-sm font-semibold text-[var(--text-muted)]">
                  No hay factores que coincidan con los filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={safePage}
        onPageChange={setCurrentPage}
        pageSize={PAGE_SIZE}
        totalItems={filtered.length}
        itemLabel="factores"
      />

      <style>{`
        .input-factor {
          border: 1px solid var(--border);
          background: var(--bg-surface);
          border-radius: 1rem;
          padding: .75rem 1rem;
          font-size: .875rem;
          color: var(--text-main);
          text-align: center;
        }
      `}</style>
    </section>
  );
}

export default FactorCatalog;