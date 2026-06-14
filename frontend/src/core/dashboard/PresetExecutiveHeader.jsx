import { Building2, Download, Leaf } from "lucide-react";

function PresetExecutiveHeader({ activeConstructora, dashboardConfig, environmentalStatus, preset, onExport }) {
  return (
    <header className="overflow-hidden rounded-[28px] border border-[var(--border)] bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98)_50%,rgba(240,249,255,0.94))] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
              <Leaf size={14} />
              Preset: {preset.name}
            </span>
            <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase tracking-[0.18em] ${environmentalStatus.className}`}>
              {environmentalStatus.label}
            </span>
          </div>

          <h1 className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
            {dashboardConfig.title}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
            {dashboardConfig.subtitle}
          </p>

          <div className="mt-5 inline-flex max-w-full items-center gap-3 rounded-2xl border border-white/70 bg-white/80 px-4 py-3 shadow-[0_12px_28px_rgba(15,23,42,0.05)]">
            <Building2 className="shrink-0 text-[var(--primary-dark)]" size={20} />
            <div className="min-w-0">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
                Empresa activa
              </p>
              <p className="truncate text-base font-black text-[var(--text-main)]">
                {activeConstructora?.nombre || "Sin empresa activa"}
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onExport}
          className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(14,124,102,0.22)] transition hover:bg-[var(--primary-dark)] sm:w-fit"
        >
          <Download size={18} />
          Exportar reporte
        </button>
      </div>
    </header>
  );
}

export default PresetExecutiveHeader;
