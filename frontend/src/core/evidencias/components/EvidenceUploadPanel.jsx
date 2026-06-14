import { useMemo, useState } from "react";
import { UploadCloud } from "lucide-react";

function buildInitialMetadata(fields) {
  return Object.fromEntries(fields.map((field) => [field.key, ""]));
}

function EvidenceUploadPanel({ config, onSubmit, records = [], saving }) {
  const evidenceTypes = [...config.requiredEvidenceTypes, ...config.optionalEvidenceTypes];
  const metadataFields = config.getUploadMetadataFields();
  const initialMetadata = useMemo(() => buildInitialMetadata(metadataFields), [metadataFields]);
  const [form, setForm] = useState({
    nombre: "",
    evidenceType: evidenceTypes[0]?.key || "otro",
    fecha_documento: "",
    archivo: null,
    registro_emision: "",
    estado_documental: "pendiente",
    observaciones: "",
    metadata: initialMetadata,
  });

  const selectedType = evidenceTypes.find((item) => item.key === form.evidenceType) || evidenceTypes[0];

  function updateMetadata(key, value) {
    setForm((current) => ({ ...current, metadata: { ...current.metadata, [key]: value } }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    await onSubmit({ ...form, selectedType });
    setForm({
      nombre: "",
      evidenceType: evidenceTypes[0]?.key || "otro",
      fecha_documento: "",
      archivo: null,
      registro_emision: "",
      estado_documental: "pendiente",
      observaciones: "",
      metadata: initialMetadata,
    });
    event.currentTarget.reset();
  }

  const inputClass = "w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]";

  return (
    <form onSubmit={handleSubmit} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
      <div className="mb-5">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--primary-dark)]">Nuevo respaldo</p>
        <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">Subir evidencia</h2>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <input className={inputClass} placeholder="Nombre de la evidencia" value={form.nombre} onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))} required />
        <select className={inputClass} value={form.evidenceType} onChange={(event) => setForm((current) => ({ ...current, evidenceType: event.target.value }))}>
          {evidenceTypes.map((type) => <option key={type.key} value={type.key}>{type.label}</option>)}
        </select>
        <input type="date" className={inputClass} value={form.fecha_documento} onChange={(event) => setForm((current) => ({ ...current, fecha_documento: event.target.value }))} />
        <select className={inputClass} value={form.estado_documental} onChange={(event) => setForm((current) => ({ ...current, estado_documental: event.target.value }))}>
          <option value="pendiente">Pendiente revision</option>
          <option value="vinculada">Completa</option>
          <option value="observada">Incompleta</option>
          <option value="rechazada">Critica</option>
          <option value="sin_vinculo">Sin vincular</option>
        </select>
        <select className={`${inputClass} md:col-span-2`} value={form.registro_emision} onChange={(event) => setForm((current) => ({ ...current, registro_emision: event.target.value }))}>
          <option value="">Registro ambiental vinculado</option>
          {records.slice(0, 100).map((record) => (
            <option key={record.id} value={record.id}>
              #{record.id} - {record.fuente_emision || "Sin fuente"} ({record.fecha || "Sin fecha"})
            </option>
          ))}
        </select>
        {metadataFields.map((field) => (
          field.type === "select" ? (
            <select key={field.key} className={inputClass} value={form.metadata[field.key] || ""} onChange={(event) => updateMetadata(field.key, event.target.value)}>
              <option value="">{field.label}</option>
              {(field.options || []).map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          ) : (
            <input key={field.key} type={field.type || "text"} className={inputClass} placeholder={field.label} value={form.metadata[field.key] || ""} onChange={(event) => updateMetadata(field.key, event.target.value)} />
          )
        ))}
        <input type="file" className={`${inputClass} md:col-span-2 file:mr-4 file:rounded-xl file:border-0 file:bg-[var(--success-bg)] file:px-3 file:py-2 file:font-bold file:text-[var(--primary-dark)]`} onChange={(event) => setForm((current) => ({ ...current, archivo: event.target.files?.[0] || null }))} required />
        <textarea className={`${inputClass} min-h-24 md:col-span-2`} placeholder="Observaciones" value={form.observaciones} onChange={(event) => setForm((current) => ({ ...current, observaciones: event.target.value }))} />
      </div>

      <button type="submit" disabled={saving} className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-[var(--primary-dark)] px-5 py-3 text-sm font-black text-white disabled:opacity-60">
        <UploadCloud size={18} />
        {saving ? "Guardando..." : "Subir evidencia"}
      </button>
    </form>
  );
}

export default EvidenceUploadPanel;
