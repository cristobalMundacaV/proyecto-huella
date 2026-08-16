import { useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { createEtapaObra, getOrganizacionEtapas } from "@/shared/services/api";
import { Alert, Button, EmptyState, ErrorState, Input, LoadingState, Modal, PageHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell, Textarea } from "@/shared/ui";

const TYPES = ["Excavacion", "Fundaciones", "Obra gruesa", "Estructura", "Instalaciones", "Terminaciones", "Urbanizacion", "Retiro de residuos", "Logistica", "Administracion de obra", "Otro"];
const STATES = { activa: "Activa", inactiva: "Inactiva", suspendida: "Suspendida", finalizada: "Finalizada" };
const emptyForm = { nombre: "", tipo: "Otro", region: "", comuna: "", direccion: "", descripcion: "", estado: "activa", activa: true };
const profileName = (preset) => ({ construccion: "Construcción", forestal: "Forestal", aserradero: "Aserradero", transporte: "Transporte", industrial: "Industrial" }[preset] || "Operación");

export default function EtapasPage() {
  const { user } = useAuth();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", status: "loading", rows: [], error: "" });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState("");
  const requestRef = useRef(0);
  const activeScopeRef = useRef(activeOrganizacionId);
  activeScopeRef.current = activeOrganizacionId;

  async function load() {
    if (!activeOrganizacionId) return;
    const scopeKey = String(activeOrganizacionId);
    const requestId = ++requestRef.current;
    setState({ scopeKey, status: "loading", rows: [], error: "" });
    try {
      const rows = await getOrganizacionEtapas(activeOrganizacionId);
      if (requestRef.current === requestId) setState({ scopeKey, status: "ready", rows: Array.isArray(rows) ? rows : [], error: "" });
    } catch (error) {
      if (requestRef.current === requestId) setState({ scopeKey, status: "error", rows: [], error: error.response?.data?.error || "No se pudo cargar la estructura." });
    }
  }

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrganizacionId]);

  async function create() {
    const organizationId = activeOrganizacionId;
    setSaving(true); setMutationError("");
    try {
      await createEtapaObra(organizationId, form);
      if (String(activeScopeRef.current) !== String(organizationId)) return;
      setDialogOpen(false); setForm(emptyForm); await load();
    } catch (error) {
      setMutationError(error.response?.data?.error || error.response?.data?.detail || "No se pudo crear la etapa.");
    } finally { setSaving(false); }
  }

  const scopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (!activeOrganizacionId) return <EmptyState title="Sin organización activa" description="Selecciona una organización para revisar su estructura." />;
  if (state.scopeKey !== scopeKey || state.status === "loading") return <LoadingState label="Cargando estructura" />;

  const construction = activeOrganizacion?.preset === "construccion";
  const unitLabel = construction ? "Etapa" : "Elemento de estructura";
  const pluralLabel = construction ? "Etapas" : "Estructura registrada";

  return (
    <main className="space-y-6">
      <PageHeader
        eyebrow="Administración · Estructura"
        title="Estructura"
        description="Revisa cómo está organizada la operación de esta organización."
        metadata={`${profileName(activeOrganizacion?.preset)} · ${activeOrganizacion?.nombre || "Organización"}`}
        actions={construction && !user?.is_demo ? <Button onClick={() => { setForm(emptyForm); setMutationError(""); setDialogOpen(true); }}><Plus size={16} aria-hidden="true" />Nueva etapa</Button> : undefined}
      />

      {user?.is_demo && <Alert title="Solo lectura en modo demo">La estructura puede revisarse, pero no modificarse.</Alert>}
      {!construction && <Alert title="Estructura según el perfil activo">Esta vista conserva la estructura registrada. No ofrece creación de etapas de obra para un perfil que no es Construcción.</Alert>}
      {mutationError && <Alert tone="danger">{mutationError}</Alert>}

      {state.status === "error" ? <ErrorState description={state.error} onRetry={load} /> : !state.rows.length ? (
        <EmptyState
          title={construction ? "Sin etapas registradas" : "Sin estructura registrada"}
          description={construction ? "Las etapas ayudan a ordenar la operación de las obras. Créala sólo cuando aporte contexto real." : "No se fuerza una estructura de construcción para este perfil de operación."}
          action={construction && !user?.is_demo ? <Button onClick={() => setDialogOpen(true)}>Crear etapa</Button> : undefined}
        />
      ) : (
        <section className="space-y-3">
          <div><h2 className="text-lg font-black">{pluralLabel}</h2><p className="text-sm text-[var(--text-muted)]">{state.rows.length} {state.rows.length === 1 ? unitLabel.toLowerCase() : pluralLabel.toLowerCase()}.</p></div>
          <TableShell>
            <TableHead><tr><TableCell as="th">Nombre</TableCell><TableCell as="th">Tipo</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Ubicación</TableCell><TableCell as="th">Registros vinculados</TableCell></tr></TableHead>
            <TableBody columns={5}>{state.rows.map((item) => <tr key={item.id}>
              <TableCell><b>{item.nombre || "Sin nombre"}</b>{item.descripcion && <span className="block text-xs text-[var(--text-muted)]">{item.descripcion}</span>}</TableCell>
              <TableCell>{item.tipo || "Sin datos"}</TableCell>
              <TableCell><StatusBadge tone={item.estado === "activa" && item.activa !== false ? "success" : "neutral"}>{STATES[item.estado] || (item.activa === false ? "Inactiva" : item.estado || "Sin datos")}</StatusBadge></TableCell>
              <TableCell>{[item.comuna, item.region].filter(Boolean).join(", ") || "Sin datos"}</TableCell>
              <TableCell>{item.registros_count ?? 0}</TableCell>
            </tr>)}</TableBody>
          </TableShell>
        </section>
      )}

      <Modal
        open={dialogOpen}
        title="Crear etapa"
        description="Registra sólo la información necesaria para ubicar esta etapa dentro de la operación."
        onClose={() => !saving && setDialogOpen(false)}
        footer={<div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={() => setDialogOpen(false)}>Cancelar</Button><Button loading={saving} disabled={!form.nombre.trim()} onClick={create}>Crear etapa</Button></div>}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Nombre" required value={form.nombre} onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))} />
          <Select label="Tipo" value={form.tipo} onChange={(event) => setForm((current) => ({ ...current, tipo: event.target.value }))}>{TYPES.map((value) => <option key={value} value={value}>{value}</option>)}</Select>
          <Input label="Región" value={form.region} onChange={(event) => setForm((current) => ({ ...current, region: event.target.value }))} />
          <Input label="Comuna" value={form.comuna} onChange={(event) => setForm((current) => ({ ...current, comuna: event.target.value }))} />
          <Input label="Dirección" value={form.direccion} onChange={(event) => setForm((current) => ({ ...current, direccion: event.target.value }))} />
          <Select label="Estado" value={form.estado} onChange={(event) => setForm((current) => ({ ...current, estado: event.target.value, activa: event.target.value === "activa" }))}>{Object.entries(STATES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
        </div>
        <div className="mt-4"><Textarea label="Descripción" rows={3} value={form.descripcion} onChange={(event) => setForm((current) => ({ ...current, descripcion: event.target.value }))} /></div>
        {mutationError && <Alert tone="danger">{mutationError}</Alert>}
      </Modal>
    </main>
  );
}
