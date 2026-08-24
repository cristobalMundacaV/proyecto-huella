import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Pencil, Plus, Trash2, UsersRound } from "lucide-react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { usePermissions } from "@/features/auth/hooks/usePermissions";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { createOrganizacionUsuario, deleteOrganizacionUsuario, getOrganizacionObras, getOrganizacionUsuarios, updateOrganizacionUsuario } from "@/shared/services/api";
import { Alert, Button, EmptyState, ErrorState, Input, Modal, PageHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { isValidEmail, normalizeEmail } from "@/shared/utils/validators";

const ROLE_LABELS = { admin: "Administrador", responsable_ambiental: "Responsable ambiental", analista: "Analista ambiental", operador: "Operador", revisor_ambiental: "Revisor ambiental", lector: "Lector" };
const ROLE_DESCRIPTIONS = { admin: "Administra la configuración y estructura de la organización.", responsable_ambiental: "Gestiona y gobierna la operación ambiental.", analista: "Analiza, prepara y registra información ambiental.", operador: "Registra información operacional en las obras asignadas.", revisor_ambiental: "Revisa y valida información sin administrar la organización.", lector: "Acceso de consulta sin capacidad de modificación." };
const emptyForm = { email: "", first_name: "", last_name: "", rol: "analista", cargo: "", alcance: "organizacion", obra_ids: [], activo: true };

export default function UsuariosPage() {
  const { user } = useAuth();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const { can } = usePermissions();
  const canAdminister = !user?.is_demo && can("team.manage");
  const [state, setState] = useState({ scopeKey: "", status: "loading", rows: [], error: "" });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState("");
  const [works, setWorks] = useState([]);
  const [emailTouched, setEmailTouched] = useState(false);
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
      const [rows, workRows] = await Promise.all([getOrganizacionUsuarios(activeOrganizacionId), getOrganizacionObras(activeOrganizacionId)]);
      if (requestRef.current === requestId) setWorks(Array.isArray(workRows) ? workRows : workRows?.results || []);
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
    if (!editingMember && !isValidEmail(form.email)) { setEmailTouched(true); return; }
    const organizationId = activeOrganizacionId;
    setSaving(true);
    setMutationError("");
    try {
      if (editingMember) await updateOrganizacionUsuario(organizationId, editingMember.id, { rol: form.rol, cargo: form.cargo, alcance: form.alcance, obra_ids: form.obra_ids, activo: form.activo });
      else await createOrganizacionUsuario(organizationId, form);
      if (String(activeScopeRef.current) !== String(organizationId)) return;
      setDialogOpen(false);
      setForm(emptyForm);
      setEditingMember(null);
      await load();
    } catch (error) {
      setMutationError(error.response?.data?.error || error.response?.data?.detail || "No se pudo agregar el usuario.");
    } finally {
      setSaving(false);
    }
  }

  function openCreate() { setMutationError(""); setEditingMember(null); setEmailTouched(false); setForm(emptyForm); setDialogOpen(true); }
  function openEdit(member) { setMutationError(""); setEditingMember(member); setForm({ ...emptyForm, rol: member.rol, cargo: member.cargo || "", alcance: member.alcance || "organizacion", obra_ids: member.obra_ids || [], activo: member.activo }); setDialogOpen(true); }
  async function removeMember(member) {
    if (!window.confirm(`¿Eliminar el acceso de ${member.nombre || member.username}?`)) return;
    try { await deleteOrganizacionUsuario(activeOrganizacionId, member.id); await load(); }
    catch (error) { setMutationError(error.response?.data?.detail || "No se pudo eliminar el acceso."); }
  }

  const scopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (!activeOrganizacionId) return <EmptyState title="Sin organización activa" description="Selecciona una organización antes de administrar accesos." />;
  if (state.scopeKey !== scopeKey || state.status === "loading") return <PlatformLoader title="Cargando usuarios" description="Estamos reuniendo accesos y roles de la organización activa." />;

  return (
    <main className="space-y-6">
      <PageHeader
        eyebrow="Configuración · Equipo y acceso"
        title="Usuarios y roles"
        description="Revisa quién tiene acceso y qué rol tiene en la organización."
        metadata={activeOrganizacion?.nombre || undefined}
        actions={canAdminister ? <Button onClick={openCreate}><Plus size={16} aria-hidden="true" />Agregar usuario</Button> : undefined}
      />

      {user?.is_demo && <Alert title="Solo lectura en modo demo">Puedes revisar los accesos, pero no agregar usuarios.</Alert>}
      {mutationError && <Alert tone="danger">{mutationError}</Alert>}

      {state.status === "error" ? (
        <ErrorState description={state.error} onRetry={load} />
      ) : !state.rows.length ? (
        <EmptyState title="Sin usuarios registrados" description="Los accesos de esta organización aparecerán aquí." action={canAdminister ? <Button onClick={openCreate}>Agregar usuario</Button> : undefined} />
      ) : (
        <TableShell>
          <TableHead><tr><TableCell as="th">Usuario</TableCell><TableCell as="th">Rol</TableCell><TableCell as="th">Alcance</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Organización</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead>
          <TableBody columns={6}>{state.rows.map((member) => {
            const isCurrent = String(member.id) === String(user?.id) || (member.username && member.username === user?.username);
            return <tr key={`${member.organizacion_id}-${member.id}`}>
              <TableCell><b>{member.nombre || member.username || member.email || "Usuario"}{isCurrent ? " · Tú" : ""}</b><span className="block text-xs text-[var(--text-muted)]">{member.email || member.username || "Sin correo informado"}{member.cargo ? ` · ${member.cargo}` : ""}</span></TableCell>
              <TableCell>{ROLE_LABELS[member.rol] || member.rol || "Sin rol"}</TableCell>
              <TableCell>{member.alcance_label || (member.alcance === "obras" ? "Obras específicas" : "Toda la organización")}</TableCell>
              <TableCell><StatusBadge tone={member.activo ? "success" : "neutral"}>{member.activo ? "Activo" : "Inactivo"}</StatusBadge></TableCell>
              <TableCell>{member.organizacion_nombre || activeOrganizacion?.nombre || "Sin datos"}</TableCell>
              <TableCell>{canAdminister ? <div className="flex gap-2"><Button variant="secondary" onClick={() => openEdit(member)}><Pencil size={15} aria-hidden="true" />Editar</Button><Button variant="secondary" onClick={() => removeMember(member)}><Trash2 size={15} aria-hidden="true" />Eliminar</Button></div> : <span className="text-xs text-[var(--text-muted)]">Solo lectura</span>}</TableCell>
            </tr>;
          })}</TableBody>
        </TableShell>
      )}

      <Modal
        open={dialogOpen}
        title={editingMember ? "Editar acceso" : "Agregar usuario"}
        description={editingMember ? "Actualiza rol, alcance y estado de la membresía tenant." : "Este flujo crea el usuario y su acceso a la organización inmediatamente."}
        onClose={() => !saving && setDialogOpen(false)}
        footer={<div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={() => setDialogOpen(false)}>Cancelar</Button><Button loading={saving} disabled={(!editingMember && !form.email.trim()) || (form.alcance === "obras" && !form.obra_ids.length)} onClick={submit}>{editingMember ? "Guardar cambios" : "Agregar usuario"}</Button></div>}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {!editingMember && <Input label="Correo electrónico" required type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} onBlur={() => { setEmailTouched(true); setForm((current) => ({ ...current, email: normalizeEmail(current.email) })); }} error={emailTouched && !isValidEmail(form.email) ? "El formato del correo electrónico no es válido." : undefined} />}
          <Input label="Nombre" value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} />
          <Input label="Apellido" value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} />
          <Input label="Cargo" value={form.cargo} onChange={(event) => setForm((current) => ({ ...current, cargo: event.target.value }))} />
          <Select label="Rol" value={form.rol} onChange={(event) => setForm((current) => ({ ...current, rol: event.target.value }))}>
            {Object.entries(ROLE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
          <Select label="Alcance" value={form.alcance} onChange={(event) => setForm((current) => ({ ...current, alcance: event.target.value, obra_ids: [] }))}>
            <option value="organizacion">Toda la organización</option><option value="obras">Obras específicas</option>
          </Select>
          <p className="sm:col-span-2 text-sm text-[var(--text-muted)]">{ROLE_DESCRIPTIONS[form.rol]}</p>
          {form.alcance === "obras" && <label className="sm:col-span-2 text-sm font-bold">Obras autorizadas<select multiple className="mt-2 min-h-32 w-full rounded-[var(--radius-lg)] border border-[var(--border-default)] p-3" value={form.obra_ids.map(String)} onChange={(event) => setForm((current) => ({ ...current, obra_ids: Array.from(event.target.selectedOptions, (option) => Number(option.value)) }))}>{works.map((work) => <option key={work.id} value={work.id}>{work.nombre}</option>)}</select></label>}
          <label className="flex items-center gap-3 self-end rounded-[var(--radius-lg)] border border-[var(--border-default)] p-3 text-sm font-bold"><input type="checkbox" checked={form.activo} onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))} />Acceso activo</label>
        </div>
        {mutationError && <div className="mt-4"><Alert tone="danger">{mutationError}</Alert></div>}
      </Modal>
    </main>
  );
}
