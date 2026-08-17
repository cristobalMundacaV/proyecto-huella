import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Plus, UsersRound } from "lucide-react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { createOrganizacionUsuario, getOrganizacionUsuarios } from "@/shared/services/api";
import { Alert, Button, EmptyState, ErrorState, Input, LoadingState, Modal, PageHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";

const ROLE_LABELS = { admin: "Administrador", analista: "Analista", operador: "Operador", lector: "Lector" };
const emptyForm = { username: "", email: "", first_name: "", last_name: "", password: "", rol: "analista", cargo: "", activo: true };

export default function UsuariosPage() {
  const { user } = useAuth();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", status: "loading", rows: [], error: "" });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState("");
  const requestRef = useRef(0);
  const activeScopeRef = useRef(activeOrganizacionId);

  useLayoutEffect(() => {
    activeScopeRef.current = activeOrganizacionId;
  }, [activeOrganizacionId]);

  async function load() {
    if (!activeOrganizacionId) return;
    const scopeKey = String(activeOrganizacionId);
    const requestId = ++requestRef.current;
    setState({ scopeKey, status: "loading", rows: [], error: "" });
    try {
      const rows = await getOrganizacionUsuarios(activeOrganizacionId);
      if (requestRef.current === requestId) setState({ scopeKey, status: "ready", rows: Array.isArray(rows) ? rows : [], error: "" });
    } catch (error) {
      if (requestRef.current === requestId) setState({ scopeKey, status: "error", rows: [], error: error.response?.data?.error || "No se pudieron cargar los usuarios." });
    }
  }

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrganizacionId]);

  async function submit() {
    const organizationId = activeOrganizacionId;
    setSaving(true);
    setMutationError("");
    try {
      await createOrganizacionUsuario(organizationId, form);
      if (String(activeScopeRef.current) !== String(organizationId)) return;
      setDialogOpen(false);
      setForm(emptyForm);
      await load();
    } catch (error) {
      setMutationError(error.response?.data?.error || error.response?.data?.detail || "No se pudo agregar el usuario.");
    } finally {
      setSaving(false);
    }
  }

  const scopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (!activeOrganizacionId) return <EmptyState title="Sin organización activa" description="Selecciona una organización antes de administrar accesos." />;
  if (state.scopeKey !== scopeKey || state.status === "loading") return <LoadingState label="Cargando usuarios" />;

  return (
    <main className="space-y-6">
      <PageHeader
        eyebrow="Administración · Usuarios"
        title="Usuarios y roles"
        description="Revisa quién tiene acceso y qué rol tiene en la organización."
        metadata={activeOrganizacion?.nombre || undefined}
        actions={!user?.is_demo ? <Button onClick={() => { setMutationError(""); setForm(emptyForm); setDialogOpen(true); }}><Plus size={16} aria-hidden="true" />Agregar usuario</Button> : undefined}
      />

      {user?.is_demo && <Alert title="Solo lectura en modo demo">Puedes revisar los accesos, pero no agregar usuarios.</Alert>}
      {mutationError && <Alert tone="danger">{mutationError}</Alert>}

      {state.status === "error" ? (
        <ErrorState description={state.error} onRetry={load} />
      ) : !state.rows.length ? (
        <EmptyState title="Sin usuarios registrados" description="Agrega un usuario cuando necesite acceso directo a esta organización." action={!user?.is_demo ? <Button onClick={() => setDialogOpen(true)}>Agregar usuario</Button> : undefined} />
      ) : (
        <TableShell>
          <TableHead><tr><TableCell as="th">Usuario</TableCell><TableCell as="th">Rol</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Organización</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead>
          <TableBody columns={5}>{state.rows.map((member) => {
            const isCurrent = String(member.id) === String(user?.id) || (member.username && member.username === user?.username);
            return <tr key={`${member.organizacion_id}-${member.id}`}>
              <TableCell><b>{member.nombre || member.username || member.email || "Usuario"}{isCurrent ? " · Tú" : ""}</b><span className="block text-xs text-[var(--text-muted)]">{member.email || member.username || "Sin correo informado"}{member.cargo ? ` · ${member.cargo}` : ""}</span></TableCell>
              <TableCell>{ROLE_LABELS[member.rol] || member.rol || "Sin rol"}</TableCell>
              <TableCell><StatusBadge tone={member.activo ? "success" : "neutral"}>{member.activo ? "Activo" : "Inactivo"}</StatusBadge></TableCell>
              <TableCell>{member.organizacion_nombre || activeOrganizacion?.nombre || "Sin datos"}</TableCell>
              <TableCell><span className="text-xs text-[var(--text-muted)]">Sin cambios disponibles</span></TableCell>
            </tr>;
          })}</TableBody>
        </TableShell>
      )}

      <Modal
        open={dialogOpen}
        title="Agregar usuario"
        description="Este flujo crea el usuario y su acceso a la organización inmediatamente."
        onClose={() => !saving && setDialogOpen(false)}
        footer={<div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={() => setDialogOpen(false)}>Cancelar</Button><Button loading={saving} disabled={!form.username.trim() || form.password.length < 8} onClick={submit}>Agregar usuario</Button></div>}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Usuario" required value={form.username} onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))} />
          <Input label="Correo" type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
          <Input label="Nombre" value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} />
          <Input label="Apellido" value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} />
          <Input label="Contraseña" type="password" required value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} />
          <Input label="Cargo" value={form.cargo} onChange={(event) => setForm((current) => ({ ...current, cargo: event.target.value }))} />
          <Select label="Rol" value={form.rol} onChange={(event) => setForm((current) => ({ ...current, rol: event.target.value }))}>
            {Object.entries(ROLE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
          <label className="flex items-center gap-3 self-end rounded-[var(--radius-lg)] border border-[var(--border-default)] p-3 text-sm font-bold"><input type="checkbox" checked={form.activo} onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))} />Acceso activo</label>
        </div>
        {mutationError && <div className="mt-4"><Alert tone="danger">{mutationError}</Alert></div>}
      </Modal>
    </main>
  );
}
