import { useState } from "react";
import { Building2, Pencil } from "lucide-react";
import { Alert, Button, EmptyState, ErrorState, Modal, PageHeader, StatusBadge } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useAuth } from "@/features/auth/context/AuthContext";
import { usePermissions } from "@/features/auth/hooks/usePermissions";
import { updateEmpresa } from "@/shared/services/api";
import { useOrganizacionActiva } from "../context/OrganizacionActivaContext";
import OrganizacionForm, { emptyOrganizationForm } from "../components/OrganizacionForm";

const PRESET_LABELS = { construccion: "Construcción", forestal: "Forestal", aserradero: "Aserradero", transporte: "Transporte", industrial: "Industrial" };

export default function OrganizacionesPage() {
  const { user } = useAuth();
  const { activeOrganizacion, loadingOrganizaciones, errorOrganizaciones, refreshOrganizaciones, setActiveOrganizacion } = useOrganizacionActiva();
  const { can } = usePermissions();
  const canEdit = !user?.is_demo && can("organization.update");
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(emptyOrganizationForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const openEdit = () => { setForm({ ...emptyOrganizationForm, ...activeOrganizacion }); setError(""); setEditing(true); };
  async function save() {
    if (!canEdit || !activeOrganizacion) return;
    setSaving(true); setError("");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([key]) => key !== "id" && key !== "organizacion_id" && !key.endsWith("_count") && !["created_at", "updated_at", "activa"].includes(key)));
      const saved = await updateEmpresa(activeOrganizacion.organizacion_id, payload);
      setActiveOrganizacion(saved); await refreshOrganizaciones(saved.organizacion_id); setEditing(false);
    } catch (requestError) { setError(requestError.response?.data?.detail || requestError.response?.data?.error || "No se pudo guardar la organización."); }
    finally { setSaving(false); }
  }

  if (loadingOrganizaciones && !activeOrganizacion) return <PlatformLoader title="Cargando organización" description="Estamos preparando la configuración del tenant activo." />;
  if (errorOrganizaciones) return <ErrorState description={errorOrganizaciones} onRetry={() => refreshOrganizaciones()} />;
  if (!activeOrganizacion) return <EmptyState icon={Building2} title="Sin organización asignada" description="Tu usuario no tiene una organización activa disponible. Solicita acceso al administrador de plataforma." />;

  return <main className="space-y-6">
    <PageHeader eyebrow="Configuración · General" title="Organización" description="Administra exclusivamente la identidad y el perfil operacional de la organización activa." metadata={activeOrganizacion.nombre} actions={canEdit ? <Button onClick={openEdit}><Pencil aria-hidden="true" size={16} />Editar información</Button> : undefined} />
    {!canEdit && <Alert title="Acceso de solo lectura">Solo un administrador de esta organización puede modificar sus datos.</Alert>}
    {error && <Alert tone="danger">{error}</Alert>}
    <section className="overflow-hidden rounded-[22px] border border-[var(--border-default)] bg-white">
      <div className="flex items-start gap-4 border-b border-[var(--border-default)] p-5"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700"><Building2 aria-hidden="true" size={21} /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-xl font-black">{activeOrganizacion.nombre}</h2><StatusBadge tone={activeOrganizacion.activa === false ? "neutral" : "success"}>{activeOrganizacion.activa === false ? "Inactiva" : "Activa"}</StatusBadge></div><p className="mt-1 text-sm text-[var(--text-muted)]">{activeOrganizacion.rut || "RUT no informado"} · {activeOrganizacion.rubro || PRESET_LABELS[activeOrganizacion.preset] || "Sector no informado"}</p></div></div>
      <dl className="grid gap-5 p-5 text-sm sm:grid-cols-2 lg:grid-cols-3"><Item label="Perfil operacional" value={PRESET_LABELS[activeOrganizacion.preset] || activeOrganizacion.preset} /><Item label="Ubicación" value={[activeOrganizacion.comuna, activeOrganizacion.region].filter(Boolean).join(", ")} /><Item label="Dirección" value={activeOrganizacion.direccion} /><Item label="Contacto" value={activeOrganizacion.contacto} /><Item label="Correo" value={activeOrganizacion.email} /><Item label="Teléfono" value={activeOrganizacion.telefono} /></dl>
    </section>
    <Modal open={editing} title="Editar organización" description="Los cambios afectan únicamente al tenant activo." onClose={() => !saving && setEditing(false)}>{editing && <OrganizacionForm mode="edit" initialPreset={activeOrganizacion.preset || ""} value={form} onChange={setForm} onSubmit={save} onCancel={() => setEditing(false)} saving={saving} error={error} />}</Modal>
  </main>;
}

function Item({ label, value }) { return <div><dt className="text-[var(--text-muted)]">{label}</dt><dd className="mt-1 font-bold">{value || "Sin datos"}</dd></div>; }
