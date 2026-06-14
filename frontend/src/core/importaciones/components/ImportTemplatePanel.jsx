import { Download } from "lucide-react";
import { downloadCsvTemplate } from "@/presets/shared/importConfig";

function ImportTemplatePanel({ modules = [] }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">Plantillas disponibles</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((module) => (
          <article key={module.key} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="font-black text-[var(--text-main)]">{module.label}</p>
            <p className="mt-1 line-clamp-2 text-xs font-semibold text-[var(--text-muted)]">{module.columns.join(", ")}</p>
            <button
              type="button"
              onClick={() => downloadCsvTemplate(module.columns, `plantilla-${module.key}.csv`)}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-black text-emerald-700"
            >
              <Download size={14} />
              Descargar CSV
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

export default ImportTemplatePanel;
