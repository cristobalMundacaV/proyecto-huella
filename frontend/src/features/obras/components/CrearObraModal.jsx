import { Loader2, Plus, X } from "lucide-react";

import { Field } from "./common";

function CrearObraModal({
  activeOrganizacion = null,
  organizaciones = [],
  materialesConstruccion,
  fieldErrors,
  form,
  onClose,
  onSubmit,
  onUpdateForm,
  saving,
  etapasOperativas = [],
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
      <form
        onSubmit={onSubmit}
        className="my-8 w-full max-w-4xl rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-300">
              <Plus size={18} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Nueva obra</h2>
              <p className="text-sm text-slate-400">
                Registra la base de trazabilidad ambiental de la obra.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:bg-slate-800"
            aria-label="Cerrar modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Código de obra" error={fieldErrors.codigo_obra?.[0]}>
            <input
              name="codigo_obra"
              value={form.codigo_obra}
              onChange={onUpdateForm}
              required
              placeholder="OBRA-LOS-ROBLES-001"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          {activeOrganizacion ? (
            <Field label="organizacion activa">
              <div className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100">
                <p className="font-semibold">{activeOrganizacion.nombre}</p>
                <p className="text-xs text-slate-400">{activeOrganizacion.organizacion_id}</p>
              </div>
            </Field>
          ) : (
            <Field
              label="organizacion / proveedor principal"
              error={fieldErrors.organizacion_nombre?.[0] || fieldErrors.organizacion?.[0]}
            >
              <input
                name="organizacion_nombre"
                value={form.organizacion_nombre}
                onChange={onUpdateForm}
                required
                placeholder="organizacion Andina SpA"
                className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
              />
            </Field>
          )}

          <Field
            label="Etapa / frente principal"
            error={fieldErrors.etapa_id?.[0] || fieldErrors.etapa?.[0]}
          >
            <select
              name="etapa_id"
              value={form.etapa_id}
              onChange={onUpdateForm}
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            >
              <option value="">Sin etapa específica</option>
              {etapasOperativas.map((unidad) => (
                <option key={unidad.etapa_id} value={unidad.etapa_id}>
                  {unidad.nombre} - {unidad.tipo}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Fecha de inicio" error={fieldErrors.fecha?.[0]}>
            <input
              type="date"
              name="fecha"
              value={form.fecha}
              onChange={onUpdateForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          <Field label="Tipo de obra / material principal" error={fieldErrors.tipo_proyecto?.[0]}>
            <input
              name="tipo_proyecto"
              value={form.tipo_proyecto}
              onChange={onUpdateForm}
              required
              list="obra-materiales-sugeridos"
              placeholder="Edificio habitacional / Hormigón armado"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
            <datalist id="obra-materiales-sugeridos">
              {materialesConstruccion.map((tipo_proyecto) => (
                <option key={tipo_proyecto.id} value={tipo_proyecto.nombre} />
              ))}
            </datalist>
          </Field>

          <Field label="Superficie o cantidad base" error={fieldErrors.superficie_m2?.[0]}>
            <input
              type="number"
              min="0"
              step="0.001"
              name="superficie_m2"
              value={form.superficie_m2}
              onChange={onUpdateForm}
              required
              placeholder="4800"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          <Field label="Ubicación de obra" error={fieldErrors.origen?.[0]}>
            <input
              name="origen"
              value={form.origen}
              onChange={onUpdateForm}
              required
              placeholder="Concepción, Biobío"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? <Loader2 className="animate-spin" size={18} /> : <Plus size={18} />}
          Guardar obra
        </button>
      </form>
    </div>
  );
}

export default CrearObraModal;
