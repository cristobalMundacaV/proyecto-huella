import { Loader2, Plus, X } from "lucide-react";

import { Field } from "./common";

function CrearLoteModal({
  activeEmpresa = null,
  empresas = [],
  especiesMadera,
  fieldErrors,
  form,
  onClose,
  onSubmit,
  onUpdateForm,
  saving,
  unidadesOperativas = [],
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
              <h2 className="text-xl font-semibold">Nuevo lote</h2>
              <p className="text-sm text-slate-400">
                Registra la base de trazabilidad del Pasaporte Verde.
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
          <Field label="ID lote" error={fieldErrors.id_lote?.[0]}>
            <input
              name="id_lote"
              value={form.id_lote}
              onChange={onUpdateForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          {activeEmpresa ? (
            <Field label="Empresa activa">
              <div className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100">
                <p className="font-semibold">{activeEmpresa.nombre}</p>
                <p className="text-xs text-slate-400">{activeEmpresa.empresa_id}</p>
              </div>
            </Field>
          ) : (
            <Field
              label="Empresa"
              error={fieldErrors.empresa_aserradero?.[0] || fieldErrors.empresa?.[0]}
            >
              <input
                name="empresa_aserradero"
                value={form.empresa_aserradero}
                onChange={onUpdateForm}
                required
                className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
              />
            </Field>
          )}

          <Field
            label="Unidad operativa"
            error={fieldErrors.unidad_id?.[0] || fieldErrors.unidad_operativa?.[0]}
          >
            <select
              name="unidad_id"
              value={form.unidad_id}
              onChange={onUpdateForm}
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            >
              <option value="">Sin unidad especifica</option>
              {unidadesOperativas.map((unidad) => (
                <option key={unidad.unidad_id} value={unidad.unidad_id}>
                  {unidad.nombre} - {unidad.tipo}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Fecha" error={fieldErrors.fecha?.[0]}>
            <input
              type="date"
              name="fecha"
              value={form.fecha}
              onChange={onUpdateForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          <Field label="Especie" error={fieldErrors.especie?.[0]}>
            <select
              name="especie"
              value={form.especie}
              onChange={onUpdateForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            >
              {especiesMadera.map((especie) => (
                <option key={especie.id} value={especie.nombre}>
                  {especie.nombre}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Volumen m3" error={fieldErrors.volumen_m3?.[0]}>
            <input
              type="number"
              min="0"
              step="0.001"
              name="volumen_m3"
              value={form.volumen_m3}
              onChange={onUpdateForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          <Field label="Origen" error={fieldErrors.origen?.[0]}>
            <input
              name="origen"
              value={form.origen}
              onChange={onUpdateForm}
              required
              placeholder="Predio, planta o lugar de salida"
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
          Guardar lote
        </button>
      </form>
    </div>
  );
}

export default CrearLoteModal;
