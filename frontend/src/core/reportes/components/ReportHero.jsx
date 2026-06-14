import { Building2, Filter } from "lucide-react";

function ReportHero({ activeConstructora, filters, onOpenFilters, preset, report, reportConfig }) {
  const periodLabel = buildPeriodLabel(filters);
  const statusLabel = report.rows.length ? "Periodo con datos" : "Sin datos del periodo";

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(236,253,245,0.92))] p-5 shadow-[var(--shadow-premium)] sm:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
              <Building2 size={14} />
              {activeConstructora?.nombre || "Empresa activa"}
            </span>
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-sky-700">
              Preset: {preset.name}
            </span>
            <span className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
              {periodLabel}
            </span>
          </div>

          <h1 className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
            {reportConfig.title}
          </h1>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
            {reportConfig.subtitle}
          </p>
          <p className="mt-5 max-w-4xl text-base leading-7 text-[var(--text-main)]">
            {report.executiveSummary}
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <span className={`rounded-2xl border px-4 py-3 text-sm font-black ${report.rows.length ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}`}>
            {statusLabel}
          </span>
          <button
            type="button"
            onClick={onOpenFilters}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-5 py-3 text-sm font-black text-emerald-700 shadow-[0_12px_24px_rgba(15,23,42,0.06)]"
          >
            <Filter size={18} />
            Filtros
          </button>
        </div>
      </div>

      {report.insights?.length > 0 && (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {report.insights.slice(0, 4).map((insight) => (
            <div key={insight} className="rounded-2xl border border-[var(--border)] bg-white/80 p-4 text-sm font-semibold leading-6 text-[var(--text-main)]">
              {insight}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function buildPeriodLabel(filters) {
  if (filters.fecha_inicio && filters.fecha_fin) return `${filters.fecha_inicio} a ${filters.fecha_fin}`;
  if (filters.fecha_inicio) return `Desde ${filters.fecha_inicio}`;
  if (filters.fecha_fin) return `Hasta ${filters.fecha_fin}`;
  return "Periodo completo";
}

export default ReportHero;
