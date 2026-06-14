import { useEffect } from "react";
import { Building2, Loader2, Mail, MapPin, Phone, Save, X } from "lucide-react";

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
    <div className="premium-modal-overlay fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-6">
      <form
        onSubmit={onSubmit}
        className="premium-modal-shell my-4 max-h-[calc(100vh-2rem)] w-full max-w-4xl overflow-y-auto p-5 sm:my-6 sm:p-7"
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-3xl border border-[#A7F3D0] bg-[#ECFDF5] text-[#047857] shadow-[0_14px_30px_rgba(4,120,87,0.12)]">
              <Building2 size={26} />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.16em] text-[var(--primary-dark)]">
                Nueva empresa
              </p>
              <h2 className="mt-1 text-2xl font-black leading-tight text-[var(--text-main)]">
                Registrar empresa
              </h2>
              <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-[var(--text-muted)]">
                Completa los datos base para crear la empresa y dejarla disponible para obras, emisiones, evidencias e importaciones.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-white text-[var(--text-main)] shadow-[0_10px_24px_rgba(15,23,42,0.08)] transition hover:-translate-y-0.5 hover:border-[#A7F3D0] hover:bg-[#ECFDF5] hover:text-[#047857]"
            aria-label="Cerrar modal"
          >
            <X size={19} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            error={fieldErrors.rut}
            label="RUT"
            name="rut"
            onChange={onUpdateForm}
            placeholder="Ej: 76.123.456-7"
            value={form.rut}
            className="sm:col-span-2"
            required
          />

          <FormField
            error={fieldErrors.nombre}
            icon={<Building2 size={17} />}
            label="Nombre de la empresa"
            name="nombre"
            onChange={onUpdateForm}
            placeholder="Ej: Empresa Andina SpA"
            value={form.nombre}
            className="sm:col-span-2"
            required
          />

          <SelectField
            error={fieldErrors.region}
            label="Región"
            name="region"
            onChange={onUpdateForm}
            value={form.region}
            options={CHILE_REGION_NAMES}
            placeholder="Selecciona una región"
          />

          <SelectField
            disabled={!form.region}
            error={fieldErrors.comuna}
            label="Comuna"
            name="comuna"
            onChange={onUpdateForm}
            value={form.comuna}
            options={comunas}
            placeholder={form.region ? "Selecciona una comuna" : "Selecciona una región primero"}
          />

          <FormField
            error={fieldErrors.rubro}
            label="Rubro"
            name="rubro"
            onChange={onUpdateForm}
            placeholder="Ej: Construcción no forestal"
            value={form.rubro}
            className="sm:col-span-2"
            required
          />

          <FormField
            error={fieldErrors.direccion}
            icon={<MapPin size={17} />}
            label="Dirección"
            name="direccion"
            onChange={onUpdateForm}
            placeholder="Dirección comercial u oficina principal"
            value={form.direccion}
            className="sm:col-span-2"
          />

          <FormField
            error={fieldErrors.email}
            icon={<Mail size={17} />}
            label="Email"
            name="email"
            onChange={onUpdateForm}
            placeholder="contacto@constructora.cl"
            type="email"
            value={form.email}
            required
          />

          <FormField
            error={fieldErrors.telefono}
            icon={<Phone size={17} />}
            label="Teléfono"
            name="telefono"
            onChange={onUpdateForm}
            placeholder="+56 9 1234 5678"
            value={form.telefono}
          />

          <label className="space-y-2 text-sm sm:col-span-2">
            <span className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
              Observaciones
            </span>
            <textarea
              name="observaciones"
              value={form.observaciones}
              onChange={onUpdateForm}
              rows={4}
              placeholder="Notas internas, condiciones de operación o información relevante para la carga inicial."
              className={inputClass(fieldErrors.observaciones, "min-h-[110px] resize-y")}
            />
            <ErrorText error={fieldErrors.observaciones} />
          </label>
        </div>

        {error && (
          <p className="mt-5 rounded-2xl border border-[#FECACA] bg-[#FEF2F2] p-4 text-sm font-semibold text-[#B42318]">
            {error}
          </p>
        )}

        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl border border-[var(--border)] bg-white px-5 py-3 text-sm font-black text-[var(--text-muted)] shadow-[0_10px_24px_rgba(15,23,42,0.05)] hover:-translate-y-0.5 hover:text-[var(--text-main)]"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#0E7C66]/20 bg-[linear-gradient(180deg,#0E7C66,#095C4C)] px-6 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(14,124,102,0.22)] hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            Guardar empresa
          </button>
        </div>
      </form>
    </div>
  );
}

function FormField({
  className = "",
  error,
  icon,
  label,
  name,
  onChange,
  placeholder = "",
  required = false,
  type = "text",
  value,
}) {
  return (
    <label className={`space-y-2 text-sm ${className}`}>
      <span className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
        {label}
      </span>
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute left-4 top-1/2 flex -translate-y-1/2 text-[#047857]">
            {icon}
          </span>
        )}
        <input
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          className={inputClass(error, icon ? "pl-11" : "")}
        />
      </div>
      <ErrorText error={error} />
    </label>
  );
}

function SelectField({
  disabled = false,
  error,
  label,
  name,
  onChange,
  options = [],
  placeholder,
  value,
}) {
  return (
    <label className="space-y-2 text-sm">
      <span className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
        {label}
      </span>
      <select
        name={name}
        value={value}
        onChange={onChange}
        disabled={disabled}
        className={`${inputClass(error)} disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 disabled:opacity-80`}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <ErrorText error={error} />
    </label>
  );
}

function ErrorText({ error }) {
  if (!error) return null;

  return (
    <span className="block text-xs font-semibold text-[#B42318]">
      {Array.isArray(error) ? error[0] : error}
    </span>
  );
}

function inputClass(error, extraClass = "") {
  const errorClass = error
    ? "border-[#FCA5A5] bg-[#FEF2F2] focus:border-[#B42318]"
    : "border-[var(--border)] bg-white focus:border-[var(--primary)]";

  return `w-full rounded-2xl border px-4 py-3 text-[var(--text-main)] outline-none shadow-[0_1px_0_rgba(255,255,255,0.85)_inset] transition placeholder:text-slate-400 ${errorClass} ${extraClass}`;
}

export default ConstructoraForm;
