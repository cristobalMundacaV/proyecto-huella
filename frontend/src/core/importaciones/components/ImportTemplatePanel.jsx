import { Download } from "lucide-react";

import { getPlantillaGenericaXlsxUrl } from "@/shared/services/api";

function ImportTemplatePanel({ modules = [] }) {
  return (
    <section className="rounded-3xl border border-emerald-200/70 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
            Plantillas inteligentes
          </p>
          <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">
            Descarga plantillas XLSX
          </h2>
          <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
            Usa Excel para completar datos. El sistema validará las filas antes de importar.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((module) => (
          <article
            key={module.key}
            className="rounded-2xl border border-emerald-200/70 bg-white/85 p-4 shadow-[0_12px_28px_rgba(15,118,110,0.08)] ring-1 ring-white/80"
          >
            <p className="font-black text-[var(--text-main)]">{module.label}</p>
            <p className="mt-1 line-clamp-2 text-xs font-semibold text-[var(--text-muted)]">
              {module.columns.join(", ")}
            </p>

            <a
              href={getPlantillaGenericaXlsxUrl(
                module.columns,
                `plantilla-${module.key}.xlsx`
              )}
              download={`plantilla-${module.key}.xlsx`}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-black text-emerald-700 transition hover:-translate-y-px hover:border-emerald-300 hover:bg-emerald-100"
            >
              <Download size={14} />
              Descargar XLSX
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

export default ImportTemplatePanel;