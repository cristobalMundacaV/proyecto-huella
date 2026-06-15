import { Upload } from "lucide-react";

function ImportUploadPanel({ disabled, module, onFile }) {
  return (
    <section className="rounded-3xl border border-emerald-200/70 bg-[linear-gradient(135deg,rgba(240,253,250,0.98),rgba(255,255,255,0.98))] p-5 shadow-[var(--shadow-card)]">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
        Carga guiada
      </p>
      <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">
        Cargar archivo
      </h2>
      <p className="mt-1 text-sm font-semibold leading-6 text-[var(--text-muted)]">
        {module?.supported
          ? "Carga una planilla XLSX, XLS o CSV para previsualizar, corregir y confirmar antes de guardar."
          : "Módulo preparado. Próxima conexión backend para importación masiva."}
      </p>

      <label
        className={`mt-4 inline-flex items-center gap-2 rounded-2xl px-5 py-3 text-sm font-black transition ${disabled
            ? "cursor-not-allowed bg-slate-100 text-slate-400"
            : "cursor-pointer bg-[var(--primary)] text-white shadow-[0_16px_32px_rgba(14,124,102,0.22)] hover:-translate-y-px"
          }`}
      >
        <Upload size={18} />
        Seleccionar XLSX / CSV
        <input
          type="file"
          accept=".xlsx,.xls,.csv"
          disabled={disabled}
          onChange={onFile}
          className="hidden"
        />
      </label>
    </section>
  );
}

export default ImportUploadPanel;