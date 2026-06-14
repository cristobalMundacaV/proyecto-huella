import { useMemo, useState } from "react";
import { formatNumber } from "@/shared/utils/formatters";

function FactorCatalog({ config, factors = [], onCreate }) {
  const [filters, setFilters] = useState({ categoria: "", module: "", unidad: "", fuente: "", activo: "", validation: "" });
  const filtered = useMemo(() => factors.filter((factor) => {
    if (filters.categoria && factor.categoria !== filters.categoria) return false;
    if (filters.module && factor.module !== filters.module) return false;
    if (filters.unidad && !String(factor.unidad || "").toLowerCase().includes(filters.unidad.toLowerCase())) return false;
    if (filters.fuente && !String(factor.fuente || "").toLowerCase().includes(filters.fuente.toLowerCase())) return false;
    if (filters.activo && String(Boolean(factor.activo)) !== filters.activo) return false;
    if (filters.validation && String(Boolean(factor.metadata?.requires_validation)) !== filters.validation) return false;
    return true;
  }), [factors, filters]);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-premium)]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-black text-[var(--text-main)]">Catalogo de factores</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{filtered.length} factores visibles</p>
        </div>
        <button onClick={onCreate} className="rounded-2xl bg-[var(--primary)] px-4 py-3 text-sm font-black text-white">Nuevo factor</button>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <select className="input-factor" value={filters.categoria} onChange={(e) => setFilters((x) => ({ ...x, categoria: e.target.value }))}><option value="">Categoria</option>{config.categories.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select className="input-factor" value={filters.module} onChange={(e) => setFilters((x) => ({ ...x, module: e.target.value }))}><option value="">Modulo</option>{config.modules.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <input className="input-factor" placeholder="Unidad" value={filters.unidad} onChange={(e) => setFilters((x) => ({ ...x, unidad: e.target.value }))} />
        <input className="input-factor" placeholder="Fuente" value={filters.fuente} onChange={(e) => setFilters((x) => ({ ...x, fuente: e.target.value }))} />
        <select className="input-factor" value={filters.activo} onChange={(e) => setFilters((x) => ({ ...x, activo: e.target.value }))}><option value="">Activo</option><option value="true">Activo</option><option value="false">Inactivo</option></select>
        <select className="input-factor" value={filters.validation} onChange={(e) => setFilters((x) => ({ ...x, validation: e.target.value }))}><option value="">Validacion</option><option value="true">Requiere validacion</option><option value="false">Validado</option></select>
      </div>
      <div className="mt-5 overflow-x-auto rounded-2xl border border-[var(--border)]">
        <table className="min-w-[1000px] w-full text-sm">
          <thead className="bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
            <tr><th className="px-4 py-3 text-left">Categoria</th><th className="px-4 py-3 text-left">Actividad</th><th className="px-4 py-3 text-left">Unidad</th><th className="px-4 py-3 text-right">Factor</th><th className="px-4 py-3 text-left">Fuente</th><th className="px-4 py-3 text-left">Anio</th><th className="px-4 py-3 text-left">Alcance</th><th className="px-4 py-3 text-left">Estado</th><th className="px-4 py-3 text-left">Acciones</th></tr>
          </thead>
          <tbody>
            {filtered.map((factor) => (
              <tr key={factor.id} className="border-t border-[var(--border)]">
                <td className="px-4 py-3">{factor.categoria}</td><td className="px-4 py-3 font-semibold">{factor.actividad}</td><td className="px-4 py-3">{factor.unidad}</td><td className="px-4 py-3 text-right font-black text-sky-700">{formatNumber(factor.factor_emision, 6)}</td><td className="px-4 py-3">{factor.fuente}</td><td className="px-4 py-3">{factor.anio}</td><td className="px-4 py-3">{factor.alcance || "-"}</td><td className="px-4 py-3">{factor.metadata?.requires_validation ? "Requiere validacion" : factor.activo ? "Activo" : "Inactivo"}</td><td className="px-4 py-3 text-[var(--text-muted)]">Disponible</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <style>{`.input-factor{border:1px solid var(--border);background:var(--bg-surface);border-radius:1rem;padding:.75rem 1rem;font-size:.875rem;color:var(--text-main);}`}</style>
    </section>
  );
}

export default FactorCatalog;
