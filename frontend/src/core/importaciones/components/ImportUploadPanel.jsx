import { Upload } from "lucide-react";

function ImportUploadPanel({ disabled, module, onFile }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">Cargar archivo</h2>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        {module?.supported ? "Carga un CSV para previsualizar antes de confirmar." : "Modulo preparado. Proxima conexion backend para importacion masiva."}
      </p>
      <label className={`mt-4 inline-flex items-center gap-2 rounded-2xl px-5 py-3 text-sm font-black ${disabled ? "cursor-not-allowed bg-slate-100 text-slate-400" : "cursor-pointer bg-[var(--primary)] text-white"}`}>
        <Upload size={18} />
        Seleccionar CSV
        <input type="file" accept=".csv" disabled={disabled} onChange={onFile} className="hidden" />
      </label>
    </section>
  );
}

export default ImportUploadPanel;
