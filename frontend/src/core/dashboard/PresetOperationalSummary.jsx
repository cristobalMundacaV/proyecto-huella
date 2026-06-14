import { CheckCircle2, CircleDashed, Clock3 } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";

function getStatus(module) {
  if (!module.records) {
    return {
      label: "Sin datos",
      className: "border-slate-200 bg-slate-50 text-slate-600",
      icon: CircleDashed,
    };
  }

  if (module.missingFactors > 0) {
    return {
      label: "Incompleto",
      className: "border-amber-200 bg-amber-50 text-amber-700",
      icon: Clock3,
    };
  }

  return {
    label: "Correcto",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
    icon: CheckCircle2,
  };
}

function PresetOperationalSummary({ modules = [], preset }) {
  return (
    <section className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-2 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
            Resumen operativo
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">
            Modulos del preset {preset.name}
          </h2>
        </div>
        <span className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1 text-xs font-bold text-[var(--text-muted)]">
          {modules.length} modulos
        </span>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((module) => {
          const status = getStatus(module);
          const Icon = status.icon;

          return (
            <article key={module.key || module.label} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_12px_28px_rgba(15,23,42,0.04)]">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-black text-[var(--text-main)]">{module.label}</h3>
                  <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                    {module.records || 0} registros
                  </p>
                </div>
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-black ${status.className}`}>
                  <Icon size={14} />
                  {status.label}
                </span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <Metric label="Emisiones" value={`${formatNumber(module.emissions || 0, 1)} kg CO2e`} />
                <Metric label="Dato operativo" value={module.mainValue || "Sin datos"} />
                <Metric label="Sin factor" value={formatNumber(module.missingFactors || 0, 0)} />
                <Metric label="Estado" value={status.label} />
              </div>
            </article>
          );
        })}

        {!modules.length && (
          <p className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-card)] p-5 text-sm font-semibold text-[var(--text-muted)] xl:col-span-3">
            Este preset aun no tiene modulos configurados para el dashboard.
          </p>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-3">
      <p className="text-[11px] font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 break-words text-sm font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

export default PresetOperationalSummary;
