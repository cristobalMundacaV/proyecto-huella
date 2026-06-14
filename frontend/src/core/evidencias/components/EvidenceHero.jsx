function EvidenceHero({ activeConstructora, config, coverage, preset, rows }) {
  const status = getDocumentalStatus(rows.length, coverage);
  return (
    <section className="rounded-3xl border border-[#B7DEC9] bg-[linear-gradient(135deg,rgba(236,253,245,0.95),rgba(255,255,255,0.98))] p-5 shadow-[0_18px_45px_var(--shadow)] sm:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
              {activeConstructora?.nombre || "Empresa activa"}
            </span>
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-sky-700">
              Preset: {preset.name}
            </span>
          </div>
          <h1 className="mt-4 text-3xl font-black text-[var(--text-main)] sm:text-4xl">{config.title}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-[#344054]">{config.subtitle}</p>
        </div>
        <div className={`rounded-2xl border px-4 py-3 text-sm font-black ${status.className}`}>
          <p className="text-xs uppercase tracking-wide opacity-80">Estado documental</p>
          <p className="mt-1 text-lg">{status.label}</p>
          <p className="mt-1 max-w-xs text-sm font-semibold opacity-85">{status.detail}</p>
        </div>
      </div>
    </section>
  );
}

function getDocumentalStatus(total, coverage) {
  if (!total) return { label: "Sin evidencias", detail: "Aun no hay respaldos cargados.", className: "border-slate-200 bg-slate-50 text-slate-700" };
  if (coverage < 30) return { label: "Critico por falta de evidencia", detail: "Faltan respaldos requeridos.", className: "border-rose-200 bg-rose-50 text-rose-700" };
  if (coverage < 60) return { label: "En construccion", detail: "La base documental esta comenzando.", className: "border-amber-200 bg-amber-50 text-amber-700" };
  if (coverage < 85) return { label: "Parcialmente respaldado", detail: "Existe respaldo relevante pendiente.", className: "border-sky-200 bg-sky-50 text-sky-700" };
  return { label: "Bien respaldado", detail: "La cobertura documental requerida es alta.", className: "border-emerald-200 bg-emerald-50 text-emerald-700" };
}

export default EvidenceHero;
