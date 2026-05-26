import { useEffect } from "react";
import { Loader2, X } from "lucide-react";

import { CHILE_REGION_NAMES, getComunasByRegion } from "../utils/chileRegions";

function ConstructoraForm({
  error,
  fieldErrors = {},
  form,
  loading = false,
  onClose,
  onSubmit,
  onUpdateForm,
  onClearError,
}) {
  useEffect(() => {
    onClearError?.();
  }, []);

  const comunas = getComunasByRegion(form.region);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
      <form
        onSubmit={onSubmit}
        className="my-6 max-h-[calc(100vh-3rem)] w-full max-w-3xl overflow-y-auto rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Nueva constructora</h2>
            <p className="text-sm text-slate-400">
              Los campos de region y comuna son listas desplegables dependientes.
            </p>
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
          <FormField
            error={fieldErrors.rut}
            label="RUT"
            name="rut"
            onChange={onUpdateForm}
            value={form.rut}
            className="sm:col-span-2"
            required
          />

          <FormField
            error={fieldErrors.nombre}
            label="Nombre"
            name="nombre"
            onChange={onUpdateForm}
            value={form.nombre}
            className="sm:col-span-2"
            required
          />

          <label className="space-y-2 text-sm">
            <span className="text-slate-300">Region</span>
            <select
              name="region"
              value={form.region}
              onChange={onUpdateForm}
              className={inputClass(fieldErrors.region)}
            >
              <option value="">Selecciona una region</option>
              {CHILE_REGION_NAMES.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
            <ErrorText error={fieldErrors.region} />
          </label>

          <label className="space-y-2 text-sm">
            <span className="text-slate-300">Comuna</span>
            <select
              name="comuna"
              value={form.comuna}
              onChange={onUpdateForm}
              disabled={!form.region}
              className={`${inputClass(fieldErrors.comuna)} disabled:cursor-not-allowed disabled:opacity-60`}
            >
              <option value="">Selecciona una comuna</option>
              {comunas.map((comuna) => (
                <option key={comuna} value={comuna}>
                  {comuna}
                </option>
              ))}
            </select>
            <ErrorText error={fieldErrors.comuna} />
          </label>

          <FormField
            error={fieldErrors.rubro}
            label="Rubro"
            name="rubro"
            onChange={onUpdateForm}
            value={form.rubro}
            className="sm:col-span-2"
            required
          />

          <FormField
            error={fieldErrors.direccion}
            label="Direccion"
            name="direccion"
            onChange={onUpdateForm}
            value={form.direccion}
            className="sm:col-span-2"
          />

          <FormField
            error={fieldErrors.email}
            label="Email"
            name="email"
            onChange={onUpdateForm}
            type="email"
            value={form.email}
            required
          />

          <FormField
            error={fieldErrors.telefono}
            label="Telefono"
            name="telefono"
            onChange={onUpdateForm}
            value={form.telefono}
          />

          <label className="space-y-2 text-sm sm:col-span-2">
            <span className="text-slate-300">Observaciones</span>
            <textarea
              name="observaciones"
              value={form.observaciones}
              onChange={onUpdateForm}
              rows={3}
              className={inputClass(fieldErrors.observaciones)}
            />
            <ErrorText error={fieldErrors.observaciones} />
          </label>
        </div>

        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : null}
          Guardar constructora
        </button>
      </form>
    </div>
  );
}

function FormField({
  className = "",
  error,
  label,
  name,
  onChange,
  required = false,
  type = "text",
  value,
}) {
  return (
    <label className={`space-y-2 text-sm ${className}`}>
      <span className="text-slate-300">{label}</span>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        className={inputClass(error)}
      />
      <ErrorText error={error} />
    </label>
  );
}

function ErrorText({ error }) {
  if (!error) {
    return null;
  }

  return (
    <span className="block text-xs text-red-300">
      {Array.isArray(error) ? error[0] : error}
    </span>
  );
}

function inputClass(error) {
  const errorClass = error
    ? "border-red-400/70 bg-red-400/5 focus:border-red-300"
    : "border-slate-700 bg-slate-950 focus:border-emerald-400/60";

  return `w-full rounded-2xl border px-4 py-3 text-slate-100 outline-none transition ${errorClass}`;
}

export default ConstructoraForm;
