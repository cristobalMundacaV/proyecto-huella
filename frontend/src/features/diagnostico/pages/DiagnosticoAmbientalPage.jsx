import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { Alert, Button, Card, CardContent, EmptyState, ErrorState, Input, PageHeader, Select, StatusBadge, Textarea } from "@/shared/ui";
import CapacidadesAmbientales from "../components/CapacidadesAmbientales";
import { saveDiagnostico } from "../api/diagnosticoApi";
import { useDiagnostico } from "../hooks/useDiagnostico";

const STATES = [
  ["pendiente", "Pendiente"],
  ["en_progreso", "En progreso"],
  ["completado", "Completado"],
  ["requiere_actualizacion", "Requiere actualización"],
];
const GROUPS = [
  ["proceso", "Procesos identificados"],
  ["informacion_disponible", "Información disponible"],
  ["informacion_faltante", "Información pendiente"],
  ["fuente", "Fuentes conocidas"],
  ["brecha", "Brechas de contexto"],
];
const emptyForm = { estado: "pendiente", objetivo_principal: "", descripcion_contexto: "", observaciones: "" };
const keyFor = (item) => item.id ? `id-${item.id}` : item.localId;
const statusTone = (value) => value === "completado" ? "success" : value === "requiere_actualizacion" || value === "pendiente" ? "warning" : "info";
const PROFILE_LABELS = { construccion: "Construcción", forestal: "Forestal", aserradero: "Aserradero", transporte: "Transporte", industrial: "Industrial" };

export default function DiagnosticoAmbientalPage() {
  const { user } = useAuth();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const state = useDiagnostico(activeOrganizacionId);
  const [form, setForm] = useState(emptyForm);
  const [elementos, setElementos] = useState([]);
  const [dirtyItems, setDirtyItems] = useState(() => new Set());
  const [deletedIds, setDeletedIds] = useState([]);
  const [formDirty, setFormDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState("");
  const [success, setSuccess] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const activeScopeRef = useRef(activeOrganizacionId);

  useLayoutEffect(() => {
    activeScopeRef.current = activeOrganizacionId;
    setShowCreateForm(false);
  }, [activeOrganizacionId]);

  useEffect(() => {
    if (state.diagnostico.status !== "ready") return;
    const diagnostic = state.diagnostico.data;
    setForm(diagnostic ? {
      estado: diagnostic.estado,
      objetivo_principal: diagnostic.objetivo_principal || "",
      descripcion_contexto: diagnostic.descripcion_contexto || "",
      observaciones: diagnostic.observaciones || "",
    } : emptyForm);
    setElementos(diagnostic?.elementos || []);
    setDirtyItems(new Set());
    setDeletedIds([]);
    setFormDirty(false);
  }, [state.diagnostico.data, state.diagnostico.status]);

  const setField = (field, value) => { setForm((current) => ({ ...current, [field]: value })); setFormDirty(true); setSuccess(""); };
  function addElement(tipo) { const localId = `new-${Date.now()}-${Math.random()}`; setElementos((items) => [...items, { localId, tipo, nombre: "", descripcion: "" }]); setDirtyItems((current) => new Set(current).add(localId)); }
  function updateElement(item, field, value) { const key = keyFor(item); setElementos((items) => items.map((current) => keyFor(current) === key ? { ...current, [field]: value } : current)); setDirtyItems((current) => new Set(current).add(key)); setSuccess(""); }
  function removeElement(item) { setElementos((items) => items.filter((current) => keyFor(current) !== keyFor(item))); if (item.id) setDeletedIds((ids) => [...ids, item.id]); setSuccess(""); }

  async function save() {
    const organizationId = activeOrganizacionId;
    setSaving(true); setMutationError(""); setSuccess("");
    try {
      const changed = elementos.filter((item) => dirtyItems.has(keyFor(item))).map(({ id, tipo, nombre, descripcion }) => ({ ...(id ? { id } : {}), tipo, nombre, descripcion }));
      const payload = { ...form, elementos: [...changed, ...deletedIds.map((id) => ({ id, eliminar: true }))] };
      await saveDiagnostico(organizationId, payload, Boolean(state.diagnostico.data));
      if (String(activeScopeRef.current) !== String(organizationId)) return;
      await state.reload();
      setSuccess("Contexto guardado.");
    } catch (error) {
      setMutationError(error.response?.data?.error || error.response?.data?.detail || "No se pudo guardar el diagnóstico.");
    } finally { setSaving(false); }
  }

  const scopeKey = activeOrganizacionId ? `${activeOrganizacionId}:organizacion` : "";
  if (!activeOrganizacionId) return <EmptyState title="Sin organización activa" description="Selecciona una organización para revisar su contexto." />;
  if (state.scopeKey !== scopeKey || state.diagnostico.status === "loading") return <PlatformLoader title="Cargando diagnóstico" description="Estamos preparando el contexto ambiental de la organización." />;

  const diagnostic = state.diagnostico.data;
  const canSave = !user?.is_demo && (formDirty || dirtyItems.size > 0 || deletedIds.length > 0);

  if (state.diagnostico.status === "error") return <main className="space-y-6"><PageHeader eyebrow="Administración · Diagnóstico" title="Diagnóstico de contexto" description="Define el contexto organizacional que determina qué información ambiental aplica." metadata={activeOrganizacion?.nombre || undefined} /><ErrorState description={state.diagnostico.error} onRetry={state.reload} /></main>;

  if (!diagnostic && !showCreateForm) return <main className="space-y-6"><PageHeader eyebrow="Administración · Diagnóstico" title="Diagnóstico de contexto" description="Define el contexto organizacional que determina qué información ambiental aplica." metadata={activeOrganizacion?.nombre || undefined} /><EmptyState title="Diagnóstico aún no configurado" description="Inicia el contexto ambiental de esta organización para definir procesos, fuentes, brechas y aplicabilidad." primaryAction={!user?.is_demo ? <Button onClick={() => setShowCreateForm(true)}>Iniciar diagnóstico</Button> : undefined} /></main>;

  return (
    <main className="space-y-7">
      <PageHeader
        eyebrow="Administración · Diagnóstico"
        title="Diagnóstico de contexto"
        description="Define el contexto organizacional que ayuda a determinar qué aplica y qué información falta."
        metadata={activeOrganizacion?.nombre || undefined}
        status={diagnostic ? <StatusBadge tone={statusTone(diagnostic.estado)}>{STATES.find(([value]) => value === diagnostic.estado)?.[1] || diagnostic.estado}</StatusBadge> : undefined}
      />

      {user?.is_demo && <Alert title="Solo lectura en modo demo">Puedes revisar el contexto, pero no modificarlo.</Alert>}
      {mutationError && <Alert tone="danger">{mutationError}</Alert>}
      {success && <Alert tone="success">{success}</Alert>}

      <section className="grid gap-3 md:grid-cols-3">
        <Info label="Sector" value={activeOrganizacion?.rubro || "Sin datos"} />
        <Info label="Perfil de operación" value={PROFILE_LABELS[activeOrganizacion?.preset] || activeOrganizacion?.preset || "Sin datos"} />
        <Info label="Siguiente paso" value={state.preparacion.status === "ready" ? state.preparacion.data?.siguiente_paso || "Sin datos" : state.preparacion.status === "error" ? "No disponible" : "Cargando…"} />
      </section>

      <section className="space-y-4">
          <div><h2 className="text-lg font-black">Contexto organizacional</h2><p className="text-sm text-[var(--text-muted)]">Estas respuestas describen el contexto actual; pueden actualizarse cuando cambie la operación.</p></div>
          <Card><CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <Select label="Estado" value={form.estado} disabled={user?.is_demo} onChange={(event) => setField("estado", event.target.value)}>{STATES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
              <Input label="Objetivo o necesidad principal" value={form.objetivo_principal} disabled={user?.is_demo} onChange={(event) => setField("objetivo_principal", event.target.value)} />
              <Textarea label="Contexto" rows={4} value={form.descripcion_contexto} disabled={user?.is_demo} onChange={(event) => setField("descripcion_contexto", event.target.value)} />
              <Textarea label="Observaciones" rows={4} value={form.observaciones} disabled={user?.is_demo} onChange={(event) => setField("observaciones", event.target.value)} />
            </div>
          </CardContent></Card>
      </section>

      {state.diagnostico.status === "ready" && (
        <section className="space-y-4">
          <h2 className="text-lg font-black">Información disponible y pendiente</h2>
          <div className="grid gap-4 lg:grid-cols-2">{GROUPS.map(([type, title]) => <ElementGroup key={type} type={type} title={title} items={elementos.filter((item) => item.tipo === type)} readOnly={user?.is_demo} onAdd={addElement} onUpdate={updateElement} onRemove={removeElement} />)}</div>
        </section>
      )}

      <section className="space-y-4">
        <div><h2 className="text-lg font-black">Aplicabilidad</h2><p className="text-sm text-[var(--text-muted)]">Indica qué capacidades aplican al contexto de esta organización. Un estado pendiente no se completa con supuestos.</p></div>
        {state.capacidades.status === "loading" ? <PlatformLoader compact title="Cargando aplicabilidad" description="Estamos revisando las capacidades disponibles." /> : state.capacidades.status === "error" ? <ErrorState description={state.capacidades.error} onRetry={state.reload} /> : !state.capacidades.data.length ? <EmptyState title="Sin capacidades registradas" description="No hay aplicabilidad disponible para mostrar." /> : <CapacidadesAmbientales organizacionId={activeOrganizacionId} capacidades={state.capacidades.data} onChange={state.reload} readOnly={user?.is_demo} />}
      </section>

      {!user?.is_demo && state.diagnostico.status === "ready" && <div className="flex justify-end"><Button loading={saving} disabled={!canSave} onClick={save}>{diagnostic ? "Guardar cambios" : "Guardar contexto"}</Button></div>}
    </main>
  );
}

function Info({ label, value }) { return <Card><CardContent><p className="text-xs font-bold uppercase text-[var(--text-muted)]">{label}</p><p className="mt-1 font-semibold">{value ?? "Sin datos"}</p></CardContent></Card>; }
function ElementGroup({ type, title, items, readOnly, onAdd, onUpdate, onRemove }) {
  return <Card><CardContent><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-black">{title}</h3>{!readOnly && <Button size="sm" variant="secondary" onClick={() => onAdd(type)}><Plus size={15} aria-hidden="true" />Agregar</Button>}</div><div className="mt-4 space-y-3">{!items.length && <p className="text-sm text-[var(--text-muted)]">Sin información registrada.</p>}{items.map((item) => <div key={keyFor(item)} className="rounded-[var(--radius-md)] border border-[var(--border-default)] p-3"><div className="flex gap-2"><input aria-label={`Nombre en ${title}`} value={item.nombre || ""} disabled={readOnly} onChange={(event) => onUpdate(item, "nombre", event.target.value)} className="min-w-0 flex-1 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-sm focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-50" />{!readOnly && <Button variant="danger" size="sm" aria-label={`Eliminar ${item.nombre || title}`} onClick={() => onRemove(item)}><Trash2 size={16} aria-hidden="true" /></Button>}</div><textarea aria-label={`Descripción en ${title}`} rows={2} value={item.descripcion || ""} disabled={readOnly} onChange={(event) => onUpdate(item, "descripcion", event.target.value)} className="mt-2 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-sm focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-50" /></div>)}</div></CardContent></Card>;
}
