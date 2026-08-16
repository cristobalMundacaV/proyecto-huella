import { Alert, Button, Input, Select, Textarea } from "@/shared/ui";

const PRESETS = [
  ["construccion", "Construcción"],
  ["forestal", "Forestal"],
  ["aserradero", "Aserradero"],
  ["transporte", "Transporte"],
  ["industrial", "Industrial"],
];

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
  const set = (field) => (event) => onChange({ ...value, [field]: event.target.type === "checkbox" ? event.target.checked : event.target.value });

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
          <Input label="RUT" value={value.rut} onChange={set("rut")} />
          <Input label="Rubro o sector" value={value.rubro} onChange={set("rubro")} />
          <Input label="Región" value={value.region} onChange={set("region")} />
          <Input label="Comuna" value={value.comuna} onChange={set("comuna")} />
          <Input label="Dirección" value={value.direccion} onChange={set("direccion")} />
          <Input label="Contacto" value={value.contacto} onChange={set("contacto")} />
          <Input label="Correo" type="email" value={value.email} onChange={set("email")} />
          <Input label="Teléfono" value={value.telefono} onChange={set("telefono")} />
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
        <Button type="submit" loading={saving} disabled={!value.nombre.trim()}>{editing ? "Guardar cambios" : "Crear organización"}</Button>
      </div>
    </form>
  );
}
