import { AlertTriangle, Target } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";

function PresetCriticalDrivers({ drivers }) {
  return (
    <section className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-2 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
            Fuentes criticas
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Lectura prioritaria</h2>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-black text-rose-700">
          <AlertTriangle size={14} />
          {formatNumber(drivers.concentration || 0, 1)}% concentracion
        </span>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-4">
        <Driver label="Categoria critica" value={drivers.category} />
        <Driver label="Modulo critico" value={drivers.module} />
        <Driver label="Fuente critica" value={drivers.source} />
        <Driver label="Concentracion" value={`${formatNumber(drivers.concentration || 0, 1)}%`} />
      </div>

      <div className="mt-5 flex gap-3 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sky-800">
        <Target className="mt-0.5 shrink-0" size={20} />
        <p className="text-sm font-semibold leading-6">{drivers.recommendation}</p>
      </div>
    </section>
  );
}

function Driver({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 break-words text-lg font-black text-[var(--text-main)]">{value || "Sin datos"}</p>
    </div>
  );
}

export default PresetCriticalDrivers;
