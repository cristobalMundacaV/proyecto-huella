import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Building2, CheckCircle2, Pencil, Plus, Trash2 } from "lucide-react";

import ConfirmationModal from "@/shared/components/ConfirmationModal";
import { Alert, Button, Card, CardContent, EmptyState, ErrorState, Modal, PageHeader, StatusBadge } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useAuth } from "@/features/auth/context/AuthContext";
import { createEmpresa, deleteEmpresa, updateEmpresa } from "@/shared/services/api";
import { useOrganizacionActiva } from "../context/OrganizacionActivaContext";
import OrganizacionForm, { emptyOrganizationForm } from "../components/OrganizacionForm";

const PRESET_LABELS = { construccion: "Construcción", forestal: "Forestal", aserradero: "Aserradero", transporte: "Transporte", industrial: "Industrial" };

export default function OrganizacionesPage({ initialOpenCreate = false }) {
  const { user } = useAuth();
  const {
    activeOrganizacion,
    activeOrganizacionId,
    clearActiveOrganizacion,
    organizaciones,
    loadingOrganizaciones,
    errorOrganizaciones,
    refreshOrganizaciones,
    setActiveOrganizacion,
  } = useOrganizacionActiva();
  const [dialog, setDialog] = useState(null);
  const [form, setForm] = useState(emptyOrganizationForm);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState("");
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const requestRef = useRef(0);
  const activeOrgRef = useRef(activeOrganizacionId);

  useLayoutEffect(() => {
    activeOrgRef.current = activeOrganizacionId;
  }, [activeOrganizacionId]);

  useEffect(() => {
    if (initialOpenCreate && user?.is_demo === false && !activeOrganizacion && !loadingOrganizaciones) {
      setDialog((current) => current || { mode: "create" });
    }
  }, [activeOrganizacion, initialOpenCreate, loadingOrganizaciones, user?.is_demo]);

  useEffect(() => {
    if (user?.is_demo) setDialog(null);
  }, [user?.is_demo]);

  function openCreate() {
    setForm(emptyOrganizationForm);
    setMutationError("");
    setDialog({ mode: "create" });
  }

  function openEdit(item) {
    setForm({ ...emptyOrganizationForm, ...item });
    setMutationError("");
    setDialog({ mode: "edit", item });
  }

  async function submit() {
    if (user?.is_demo) {
      setMutationError("El modo demo es de solo lectura.");
      return;
    }

    setSaving(true);
    setMutationError("");
    const requestId = ++requestRef.current;
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([key]) => key !== "id" && key !== "organizacion_id" && !key.endsWith("_count") && !["created_at", "updated_at"].includes(key)));

      payload.nombre = String(payload.nombre || "").trim();
      payload.email = String(payload.email || "").trim();
      payload.contacto = String(payload.contacto || "").trim();

      const phoneDigits = String(payload.telefono || "").replace(/\D/g, "");
      const localPhoneDigits = phoneDigits.startsWith("56")
        ? phoneDigits.slice(2)
        : phoneDigits;

      payload.telefono = localPhoneDigits
        ? `+56${localPhoneDigits}`
        : "";

      if (
        payload.telefono &&
        (
          payload.telefono.trim().length !== 12 ||
          !/^\+56\d{9}$/.test(payload.telefono.trim())
        )
      ) {
        setMutationError("El telefono debe contener 9 digitos ademas de +56.");
        setSaving(false);
        return;
      }
      const saved = dialog.mode === "edit" ? await updateEmpresa(dialog.item.organizacion_id, payload) : await createEmpresa(payload);
      if (requestRef.current !== requestId) return;
      const currentActiveId = activeOrgRef.current;
      const editedActive = dialog.mode === "edit" && String(dialog.item.organizacion_id) === String(currentActiveId);
      if (dialog.mode === "create" || editedActive) setActiveOrganizacion(saved);
      setDialog(null);
      try {
        await refreshOrganizaciones(dialog.mode === "create" ? saved.organizacion_id : currentActiveId);
      } catch {
        setMutationError("La organización se guardó, pero no se pudo actualizar la lista.");
      }
    } catch (error) {
      if (requestRef.current === requestId) setMutationError(error.response?.data?.error || error.response?.data?.detail || "No se pudo guardar la organización.");
    } finally {
      if (requestRef.current === requestId) setSaving(false);
    }
  }

  async function confirmDelete() {
    const item = deleteCandidate;
    if (!item) return;
    setSaving(true);
    setMutationError("");
    try {
      await deleteEmpresa(item.organizacion_id);
      const remaining = organizaciones.filter((organization) => organization.organizacion_id !== item.organizacion_id);
      const currentActiveId = activeOrgRef.current;
      const deletingActive = String(item.organizacion_id) === String(currentActiveId);
      const currentActive = organizaciones.find((organization) => String(organization.organizacion_id) === String(currentActiveId)) || activeOrganizacion;
      const nextOrganization = deletingActive ? remaining[0] || null : currentActive;
      if (deletingActive) {
        if (nextOrganization) setActiveOrganizacion(nextOrganization);
        else clearActiveOrganizacion();
      }
      setDeleteCandidate(null);
      try {
        await refreshOrganizaciones(nextOrganization?.organizacion_id || "");
      } catch {
        setMutationError("La organización fue eliminada, pero no se pudo actualizar la lista.");
      }
    } catch (error) {
      setMutationError(error.response?.data?.error || "No se pudo eliminar la organización.");
      setDeleteCandidate(null);
    } finally {
      setSaving(false);
    }
  }

  if (loadingOrganizaciones && !organizaciones.length) return <PlatformLoader title="Cargando organizaciones" description="Estamos reuniendo los espacios disponibles para tu usuario." />;

  return (
    <main className="space-y-7">
      <PageHeader
        eyebrow="Administración · Organización"
        title="Organización"
        description="Revisa qué organización estás administrando y gestiona su identidad."
        actions={!user?.is_demo ? <Button onClick={openCreate}><Plus size={16} aria-hidden="true" />Nueva organización</Button> : undefined}
      />

      {user?.is_demo && <Alert title="Solo lectura en modo demo">Puedes seleccionar una organización para recorrer la experiencia, pero no crear, editar ni eliminar organizaciones.</Alert>}
      {errorOrganizaciones && <ErrorState description={errorOrganizaciones} onRetry={() => refreshOrganizaciones()} />}
      {mutationError && <Alert tone="danger">{mutationError}</Alert>}

      {activeOrganizacion ? (
        <section className="space-y-3">
          <h2 className="text-lg font-black">Organización activa</h2>
          <Card>
            <CardContent>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2"><Building2 size={20} className="text-[var(--brand-primary)]" aria-hidden="true" /><h3 className="text-xl font-black">{activeOrganizacion.nombre}</h3><StatusBadge tone={activeOrganizacion.activa === false ? "neutral" : "success"}>{activeOrganizacion.activa === false ? "Inactiva" : "Activa"}</StatusBadge></div>
                  <p className="mt-2 text-sm text-[var(--text-muted)]">{activeOrganizacion.rut || "Identificación no informada"} · {activeOrganizacion.rubro || PRESET_LABELS[activeOrganizacion.preset] || "Sector no informado"}</p>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">Perfil de operación: <b>{PRESET_LABELS[activeOrganizacion.preset] || activeOrganizacion.preset || "Sin datos"}</b>{activeOrganizacion.email ? ` · ${activeOrganizacion.email}` : ""}</p>
                </div>
                {!user?.is_demo && <Button variant="secondary" onClick={() => openEdit(activeOrganizacion)}><Pencil size={16} aria-hidden="true" />Editar</Button>}
              </div>
            </CardContent>
          </Card>
        </section>
      ) : (
        <EmptyState title="Sin organización activa" description="Crea una organización para comenzar a configurar la experiencia." action={!user?.is_demo ? <Button onClick={openCreate}>Crear organización</Button> : undefined} />
      )}

      {organizaciones.length > 0 && (
        <section className="space-y-3">
          <div><h2 className="text-lg font-black">Organizaciones disponibles</h2><p className="text-sm text-[var(--text-muted)]">Seleccionar una organización cambia el contexto de trabajo; editarla modifica sus datos.</p></div>
          <div className="grid gap-3 md:grid-cols-2">
            {organizaciones.map((item) => {
              const selected = String(item.organizacion_id) === String(activeOrganizacionId);
              return <Card key={item.organizacion_id}><CardContent>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><h3 className="font-black">{item.nombre}</h3><p className="mt-1 text-sm text-[var(--text-muted)]">{PRESET_LABELS[item.preset] || item.preset || "Perfil no informado"}{item.rubro ? ` · ${item.rubro}` : ""}</p>{selected && <p className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-[var(--brand-primary)]"><CheckCircle2 size={14} aria-hidden="true" />En uso</p>}</div>
                  <StatusBadge tone={item.activa === false ? "neutral" : "success"}>{item.activa === false ? "Inactiva" : "Activa"}</StatusBadge>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {!selected && <Button size="sm" onClick={() => setActiveOrganizacion(item)}>Usar esta organización</Button>}
                  {!user?.is_demo && <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>}
                  {!user?.is_demo && <Button size="sm" variant="danger" onClick={() => setDeleteCandidate(item)}><Trash2 size={15} aria-hidden="true" />Eliminar</Button>}
                </div>
              </CardContent></Card>;
            })}
          </div>
        </section>
      )}

      <Modal
        open={Boolean(dialog)}
        title={dialog?.mode === "edit" ? "Editar organización" : "Crear organización"}
        description={dialog?.mode === "edit" ? "Actualiza la identidad y el perfil de operación de esta organización." : "Empieza con la identidad mínima y agrega datos de contacto sólo si los necesitas."}
        onClose={() => !saving && setDialog(null)}
      >
        {dialog && <OrganizacionForm mode={dialog.mode} initialPreset={dialog.item?.preset || ""} value={form} onChange={setForm} onSubmit={submit} onCancel={() => setDialog(null)} saving={saving} error={mutationError} />}
      </Modal>

      {deleteCandidate && <ConfirmationModal
        title={`Eliminar ${deleteCandidate.nombre}`}
        description="Esta acción elimina la organización y sus obras, etapas, registros, evidencias y transportes asociados. No es una desactivación."
        confirmLabel="Eliminar organización"
        loading={saving}
        onCancel={() => setDeleteCandidate(null)}
        onConfirm={confirmDelete}
      />}
    </main>
  );
}
