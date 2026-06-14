import { useMemo, useState } from "react";
import { Save } from "lucide-react";

function getToday() {
  return new Date().toISOString().slice(0, 10);
}

function createInitialForm(config) {
  return {
    fecha: getToday(),
    cantidad: "",
    unidad: config.defaultUnit || "",
    factor_emision: config.defaultFactor ?? 0,
    proveedor: "",
    observaciones: "",
    metadata: Object.fromEntries((config.metadataFields || []).map((field) => [field.key, ""])),
  };
}

function AserraderoQuickForm({ config, disabled, onSubmit, saving }) {
  const initialForm = useMemo(() => createInitialForm(config), [config]);
  const [form, setForm] = useState(initialForm);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateMetadata = (field, value) => {
    setForm((current) => ({
      ...current,
      metadata: {
        ...current.metadata,
        [field]: value,
      },
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit(form);
    setForm(createInitialForm(config));
  };

  const inputClass =
    "w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] px-3 py-2.5 text-sm font-semibold text-[var(--text-main)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/15";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-premium)] sm:p-6"
    >
      <div className="flex flex-col gap-2 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
            Registro rapido
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Nueva operacion</h2>
        </div>
        <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">
          Factor 0 permitido para trazabilidad operativa
        </span>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Fecha">
          <input
            type="date"
            value={form.fecha}
            onChange={(event) => updateField("fecha", event.target.value)}
            className={inputClass}
            required
          />
        </Field>
        <Field label="Cantidad">
          <input
            type="number"
            step="any"
            min="0"
            value={form.cantidad}
            onChange={(event) => updateField("cantidad", event.target.value)}
            className={inputClass}
            required
          />
        </Field>
        <Field label="Unidad">
          <input
            value={form.unidad}
            onChange={(event) => updateField("unidad", event.target.value)}
            className={inputClass}
            required
          />
        </Field>
        <Field label="Factor de emision">
          <input
            type="number"
            step="any"
            min="0"
            value={form.factor_emision}
            onChange={(event) => updateField("factor_emision", event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Proveedor / origen">
          <input
            value={form.proveedor}
            onChange={(event) => updateField("proveedor", event.target.value)}
            className={inputClass}
            placeholder="Proveedor, predio u origen"
          />
        </Field>

        {(config.metadataFields || []).map((field) => (
          <Field key={field.key} label={field.label}>
            <input
              type={field.type || "text"}
              step={field.type === "number" ? "any" : undefined}
              value={form.metadata[field.key] ?? ""}
              onChange={(event) => updateMetadata(field.key, event.target.value)}
              className={inputClass}
            />
          </Field>
        ))}
      </div>

      <Field label="Observaciones" className="mt-4">
        <textarea
          value={form.observaciones}
          onChange={(event) => updateField("observaciones", event.target.value)}
          className={`${inputClass} min-h-24 resize-y`}
          placeholder="Detalle operativo, desviaciones o respaldo pendiente"
        />
      </Field>

      <div className="mt-5 flex justify-end">
        <button
          type="submit"
          disabled={disabled || saving}
          className="inline-flex items-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_12px_24px_rgba(14,124,102,0.18)] transition hover:bg-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Save size={18} />
          {saving ? "Registrando..." : "Registrar operacion"}
        </button>
      </div>
    </form>
  );
}

function Field({ children, className = "", label }) {
  return (
    <label className={`block text-sm font-bold text-[var(--text-main)] ${className}`}>
      <span className="mb-1.5 block text-xs font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}

export default AserraderoQuickForm;
