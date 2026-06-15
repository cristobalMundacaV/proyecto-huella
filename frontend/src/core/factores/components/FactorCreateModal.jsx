import { useMemo, useState } from "react";

function buildInitialForm({ config, initialFactor, preset }) {
  if (initialFactor) {
    return {
      preset: initialFactor.preset || preset,
      module: initialFactor.module || "",
      categoria: initialFactor.categoria || config.categories[0] || "Otros",
      actividad: initialFactor.actividad || "",
      actividad_key: initialFactor.actividad_key || "",
      unidad: initialFactor.unidad || "",
      factor_emision: initialFactor.factor_emision ?? "",
      fuente: initialFactor.fuente || "Referencia interna - validar antes de uso oficial",
      anio: initialFactor.anio || new Date().getFullYear(),
      alcance: initialFactor.alcance || "Referencial",
      descripcion: initialFactor.descripcion || "",
      activo: initialFactor.activo !== false,
      metadata: {
        ...(initialFactor.metadata || {}),
        requires_validation: Boolean(initialFactor.metadata?.requires_validation),
      },
    };
  }

  return {
    preset,
    module: "",
    categoria: config.categories[0] || "Otros",
    actividad: "",
    actividad_key: "",
    unidad: "",
    factor_emision: "",
    fuente: "Referencia interna - validar antes de uso oficial",
    anio: new Date().getFullYear(),
    alcance: "Referencial",
    descripcion: "",
    activo: true,
    metadata: { requires_validation: true },
  };
}

function FactorCreateModal({
  config,
  initialFactor = null,
  mode = "create",
  onClose,
  onSubmit,
  preset,
}) {
  const initialForm = useMemo(
    () => buildInitialForm({ config, initialFactor, preset }),
    [config, initialFactor, preset]
  );
  const [form, setForm] = useState(initialForm);

  const inputClass =
    "rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-center text-sm text-[var(--text-main)] outline-none transition focus:border-emerald-300 focus:ring-4 focus:ring-emerald-100";

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateMetadata = (field, value) => {
    setForm((current) => ({
      ...current,
      metadata: {
        ...(current.metadata || {}),
        [field]: value,
      },
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit({
            ...form,
            factor_emision: String(form.factor_emision || "0"),
            anio: Number(form.anio || new Date().getFullYear()),
          });
        }}
        className="w-full max-w-3xl rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl"
      >
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
              Factor de emisión
            </p>
            <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">
              {mode === "edit" ? "Editar factor" : "Nuevo factor"}
            </h2>
            <p className="mt-2 max-w-2xl text-sm font-semibold text-[var(--text-muted)]">
              Mantén actualizado el catálogo ambiental usado para calcular huella y reportes.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <select
            className={inputClass}
            value={form.categoria}
            onChange={(event) => updateField("categoria", event.target.value)}
          >
            {config.categories.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>

          <select
            className={inputClass}
            value={form.module}
            onChange={(event) => updateField("module", event.target.value)}
          >
            <option value="">Módulo / uso general</option>
            {config.modules.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>

          <input
            className={inputClass}
            placeholder="Actividad"
            value={form.actividad}
            onChange={(event) => updateField("actividad", event.target.value)}
            required
          />

          <input
            className={inputClass}
            placeholder="Clave actividad opcional"
            value={form.actividad_key}
            onChange={(event) => updateField("actividad_key", event.target.value)}
          />

          <input
            className={inputClass}
            placeholder="Unidad"
            value={form.unidad}
            onChange={(event) => updateField("unidad", event.target.value)}
            required
          />

          <input
            className={inputClass}
            type="number"
            step="any"
            placeholder="Factor"
            value={form.factor_emision}
            onChange={(event) => updateField("factor_emision", event.target.value)}
            required
          />

          <input
            className={inputClass}
            type="number"
            placeholder="Año"
            value={form.anio}
            onChange={(event) => updateField("anio", event.target.value)}
            required
          />

          <select
            className={inputClass}
            value={form.alcance}
            onChange={(event) => updateField("alcance", event.target.value)}
          >
            <option value="Referencial">Referencial</option>
            <option value="Validado">Validado</option>
            <option value="Alcance 1">Alcance 1</option>
            <option value="Alcance 2">Alcance 2</option>
            <option value="Alcance 3">Alcance 3</option>
          </select>

          <input
            className={`${inputClass} md:col-span-2`}
            placeholder="Fuente"
            value={form.fuente}
            onChange={(event) => updateField("fuente", event.target.value)}
            required
          />

          <textarea
            className={`${inputClass} min-h-[110px] resize-y md:col-span-2`}
            placeholder="Descripción"
            value={form.descripcion}
            onChange={(event) => updateField("descripcion", event.target.value)}
          />

          <label className="flex items-center justify-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm font-bold text-[var(--text-main)]">
            <input
              type="checkbox"
              checked={form.activo}
              onChange={(event) => updateField("activo", event.target.checked)}
            />
            Factor activo
          </label>

          <label className="flex items-center justify-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm font-bold text-[var(--text-main)]">
            <input
              type="checkbox"
              checked={Boolean(form.metadata?.requires_validation)}
              onChange={(event) => updateMetadata("requires_validation", event.target.checked)}
            />
            Requiere validación
          </label>
        </div>

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-[var(--border)] px-4 py-3 font-bold text-[var(--text-main)]"
          >
            Cancelar
          </button>
          <button className="rounded-xl bg-[var(--primary)] px-4 py-3 font-black text-white">
            {mode === "edit" ? "Guardar cambios" : "Crear factor"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default FactorCreateModal;