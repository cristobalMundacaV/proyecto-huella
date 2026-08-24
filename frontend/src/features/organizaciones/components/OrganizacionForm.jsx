import { Alert, Button, Input, Select, Textarea } from "@/shared/ui";
import ChileLocationFields from "@/shared/components/ChileLocationFields";
import { formatChileanRut, isValidChileanRut, isValidEmail, isValidPhone } from "@/shared/utils/validators";

const PRESETS = [
  ["construccion", "Construcción"],
  ["forestal", "Forestal"],
  ["aserradero", "Aserradero"],
  ["transporte", "Transporte"],
  ["industrial", "Industrial"],
];

function phoneLocalDigits(value = "") {
  const digits = String(value).replace(/\D/g, "");

  return digits.startsWith("56") ? digits.slice(2) : digits;
}

function normalizePhoneLocal(value = "") {
  return phoneLocalDigits(value).slice(0, 9);
}

function toCanonicalPhone(value = "") {
  const local = normalizePhoneLocal(value);

  return local ? `+56${local}` : "";
}

export const emptyOrganizationForm = {
  nombre: "",
  rut: "",
  region: "",
  comuna: "",
  direccion: "",
  rubro: "",
  preset: "construccion",
  activa: true,
  email: "",
  telefono: "",
  contacto: "",
  observaciones: "",
};

export default function OrganizacionForm({ value, onChange, onSubmit, onCancel, saving = false, mode = "create", error = "", initialPreset = "" }) {
  const editing = mode === "edit";
  const set = (field) => (event) => {
    const rawValue = event.target.value;

    const nextValue =
      event.target.type === "checkbox"
        ? event.target.checked
        : field === "rut"
          ? formatChileanRut(rawValue)
          : field === "email"
            ? rawValue.replace(/\s/g, "")
            : field === "telefono"
              ? toCanonicalPhone(rawValue)
              : rawValue;

    onChange({ ...value, [field]: nextValue });
  };

  const rutInvalid = Boolean(value.rut) && !isValidChileanRut(value.rut);
  const emailInvalid = !isValidEmail(value.email);
  const phoneInvalid = !isValidPhone(value.telefono);
  const phoneLocalValue = normalizePhoneLocal(value.telefono);

  return (
    <form className="space-y-5" onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
      {error && <Alert tone="danger">{error}</Alert>}

      <fieldset className="space-y-4">
        <legend className="text-base font-black">Identidad</legend>
        <Input label="Nombre de la organización" required value={value.nombre} onChange={set("nombre")} />
        <Select label="Perfil de operación" value={value.preset} onChange={set("preset")}>
          {PRESETS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </Select>
        <p className="text-xs leading-5 text-[var(--text-muted)]">
          El perfil define vocabulario, navegación y composición de la experiencia. {editing ? "Cambiarlo reorganiza cómo se presenta la organización." : "Elige el que mejor representa la operación inicial."}
        </p>
        {editing && initialPreset && value.preset !== initialPreset && <Alert tone="warning" title="Cambio de perfil de operación">Este cambio modifica cómo se organiza y nombra la experiencia de la organización. Revisa que corresponda antes de guardar.</Alert>}
      </fieldset>

      <details className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-4" open={editing}>
        <summary className="cursor-pointer font-bold">Datos de identificación y contacto</summary>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <Input
              label="RUT"
              value={value.rut}
              onChange={set("rut")}
              inputMode="text"
              autoComplete="off"
              maxLength={12}
              aria-invalid={rutInvalid || undefined}
            />
            {rutInvalid && (
              <p className="mt-1 text-xs font-semibold text-[var(--status-danger)]">
                Revisa el RUT y su dígito verificador.
              </p>
            )}
          </div>
          <Input label="Rubro o sector" value={value.rubro} onChange={set("rubro")} />
          <ChileLocationFields region={value.region} comuna={value.comuna} onChange={(location) => onChange({ ...value, ...location })} />
          <Input label="Dirección" value={value.direccion} onChange={set("direccion")} />
          <Input label="Nombre contacto" value={value.contacto} onChange={set("contacto")} autoComplete="name" />
          <Input
            label="Correo"
            type="email"
            value={value.email}
            onChange={set("email")}
            autoComplete="email"
            error={emailInvalid ? "Ingresa un correo v\u00e1lido." : undefined}
          />
          <div>
            <label
              htmlFor="organization-phone"
              className="text-sm font-semibold text-[var(--text-secondary)]"
            >
              {"Tel\u00e9fono"}
            </label>

            <div
              className={`mt-1 flex overflow-hidden rounded-[var(--radius-md)] border bg-[var(--bg-elevated)] transition ${
                phoneInvalid
                  ? "border-[var(--status-danger)]"
                  : "border-[var(--border-default)] focus-within:border-[var(--brand-primary)] focus-within:shadow-[var(--focus-ring)]"
              }`}
            >
              <span
                className="flex shrink-0 items-center border-r border-[var(--border-default)] bg-[var(--bg-surface-subtle)] px-3 font-semibold text-[var(--text-secondary)]"
                aria-hidden="true"
              >
                +56
              </span>

              <input
                id="organization-phone"
                type="tel"
                inputMode="numeric"
                autoComplete="tel-national"
                aria-label={"N\u00famero de tel\u00e9fono"}
                aria-invalid={phoneInvalid || undefined}
                aria-describedby={
                  phoneInvalid ? "organization-phone-error" : undefined
                }
                maxLength={9}
                value={phoneLocalValue}
                onChange={set("telefono")}
                placeholder="966635509"
                className="min-w-0 flex-1 bg-transparent px-3 py-2.5 text-[var(--text-primary)] outline-none"
              />
            </div>

            {phoneInvalid && (
              <span
                id="organization-phone-error"
                role="alert"
                className="mt-1 block text-xs font-semibold text-[var(--status-danger)]"
              >
                {"Ingresa 9 d\u00edgitos. Se guardar\u00e1 con +56."}
              </span>
            )}
          </div>
        </div>
        <div className="mt-4"><Textarea label="Observaciones" rows={3} value={value.observaciones} onChange={set("observaciones")} /></div>
      </details>

      {editing && (
        <label className="flex items-start gap-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] p-4">
          <input className="mt-1" type="checkbox" checked={Boolean(value.activa)} onChange={set("activa")} />
          <span><b>Organización activa</b><span className="block text-xs text-[var(--text-muted)]">Una organización inactiva conserva sus datos, pero su estado queda registrado como inactivo.</span></span>
        </label>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button type="submit" loading={saving} disabled={!value.nombre.trim() || rutInvalid || emailInvalid || phoneInvalid}>{editing ? "Guardar cambios" : "Crear organización"}</Button>
      </div>
    </form>
  );
}
