import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  Plus,
  Search,
  ShieldAlert,
  Trash2,
  UserCog,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import PlatformLoader from "@/shared/components/PlatformLoader";
import Toast from "@/shared/components/Toast";
import {
  Button,
  ErrorState,
  Input,
  Modal,
  Select,
  StatusBadge,
} from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import {
  assignSaaSAdmin,
  deleteSaaSOrganization,
  getSaaSDashboard,
  provisionSaaSOrganization,
  runSaaSAction,
  updateSaaSOrganization,
} from "../services/saasApi";

const labels = {
  piloto: "Piloto",
  activo: "Activo",
  pago_pendiente: "Pago pendiente",
  suspendido: "Suspendido",
  cancelado: "Cancelado",
  sin_plan: "Sin plan",
  starter: "Starter",
  professional: "Professional",
  enterprise: "Enterprise",
};
const tones = {
  piloto: "info",
  activo: "success",
  pago_pendiente: "warning",
  suspendido: "danger",
  cancelado: "neutral",
  saludable: "success",
  observacion: "warning",
  riesgo: "danger",
  critico: "danger",
};
const initialCreate = {
  nombre: "",
  sector: "",
  plan: "starter",
  estado: "piloto",
  admin_nombre: "",
  admin_apellido: "",
  admin_email: "",
  admin_cargo: "",
};
const initialAdmin = { nombre: "", apellido: "", email: "", cargo: "" };
const capabilities = [
  "Gestión operacional",
  "Evidencias y trazabilidad",
  "Importaciones",
  "Indicadores ambientales",
  "Inteligencia ambiental",
  "Problemáticas y acciones",
  "Reportes profesionales",
  "Integraciones",
  "Sensores / IoT",
];
const planCapabilities = {
  sin_plan: 0,
  starter: 2,
  professional: 7,
  enterprise: 9,
};

export default function SaaSOrganizationsPage() {
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: "loading", rows: [] });
  const [selectedId, setSelectedId] = useState(params.get("seleccion") || "");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("todas");
  const [form, setForm] = useState(null);
  const [createForm, setCreateForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [createAttempted, setCreateAttempted] = useState(false);
  const [toast, setToast] = useState(null);
  const [adminForm, setAdminForm] = useState(initialAdmin);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const load = () => {
    setState((current) => ({ ...current, status: "loading" }));
    getSaaSDashboard()
      .then((data) => {
        setState({ status: "ready", rows: data.organizations });
        setSelectedId(
          (current) => current || data.organizations[0]?.organizacion_id || "",
        );
      })
      .catch(() => setState({ status: "error", rows: [] }));
  };
  useEffect(load, []);
  const filtered = useMemo(
    () =>
      state.rows.filter((row) => {
        const text =
          `${row.nombre} ${row.rut} ${row.preset} ${row.plan}`.toLowerCase();
        return (
          text.includes(query.toLowerCase()) &&
          (statusFilter === "todas" || row.estado === statusFilter)
        );
      }),
    [query, state.rows, statusFilter],
  );
  const selected =
    state.rows.find((row) => row.organizacion_id === selectedId) || filtered[0];
  useEffect(() => {
    if (selected)
      setForm({
        plan: selected.plan,
        estado: selected.estado,
        disponibilidad: selected.disponibilidad,
        preset: selected.preset,
        fin_piloto: selected.fin_piloto || "",
        proximo_vencimiento: selected.proximo_vencimiento || "",
        responsable_comercial: selected.responsable_comercial || "",
      });
  }, [selected]);
  if (state.status === "loading" && !state.rows.length)
    return <PlatformLoader title="Cargando organizaciones SaaS" />;
  if (state.status === "error")
    return (
      <ErrorState
        description="No fue posible cargar las organizaciones."
        onRetry={load}
      />
    );

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      await updateSaaSOrganization(selected.organizacion_id, form);
      load();
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "No fue posible guardar la configuración.",
      );
    } finally {
      setBusy(false);
    }
  };
  const action = async (name) => {
    setBusy(true);
    setError("");
    try {
      await runSaaSAction(selected.organizacion_id, name);
      load();
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "La transición no está disponible.",
      );
    } finally {
      setBusy(false);
    }
  };
  const create = async () => {
    setCreateAttempted(true);
    if (
      ![
        "nombre",
        "sector",
        "admin_nombre",
        "admin_apellido",
        "admin_email",
      ].every((field) => createForm?.[field]?.trim())
    ) {
      setToast({
        id: Date.now(),
        tone: "error",
        message: "Falta información necesaria",
        subtitle:
          "Completa la organización, el sector y los datos del administrador.",
      });
      return;
    }
    if (!isValidEmail(createForm.admin_email)) {
      setToast({ id: Date.now(), tone: "error", message: "Correo electrónico incorrecto", subtitle: "Ingresa un correo válido, por ejemplo nombre@empresa.cl." });
      return;
    }
    setBusy(true);
    setError("");
    setToast({
      id: Date.now(),
      loading: true,
      message: "Creando organización",
      subtitle: "Estamos guardando la información.",
    });
    try {
      const created = await provisionSaaSOrganization(createForm);
      setCreateForm(null);
      setCreateAttempted(false);
      setSelectedId(created.organizacion_id);
      setToast({ id: Date.now(), tone: "success", message: "Organización creada", subtitle: created.mensaje_enviado === "invitation" ? "La persona ya tenía una cuenta. Le enviamos una invitación a esta organización." : "Enviamos el enlace de activación a su administrador." });
      load();
    } catch (requestError) {
      const emailDeliveryFailed =
        requestError.response?.data?.code === "email_delivery_failed";
      setToast({
        id: Date.now(),
        tone: "error",
        message: emailDeliveryFailed
          ? "No pudimos enviar la invitación"
          : "No pudimos crear la organización",
        subtitle: emailDeliveryFailed
          ? "La organización no fue creada. Revisa el correo del administrador e inténtalo nuevamente."
          : naturalCreateError(requestError),
      });
    } finally {
      setBusy(false);
    }
  };
  const actions = selected ? validActions(selected.estado) : [];
  const assignAdmin = async () => {
    if (!adminForm.email.trim()) {
      setToast({
        id: Date.now(),
        tone: "error",
        message: "Falta el correo del administrador",
        subtitle: "Ingresa un correo válido para crear o vincular la cuenta.",
      });
      return;
    }
    setBusy(true);
    try {
      const result = await assignSaaSAdmin(selected.organizacion_id, adminForm);
      setAdminForm(initialAdmin);
      setToast({
        id: Date.now(),
        message: "Administrador asignado",
        subtitle: result.detail,
      });
      load();
    } catch (requestError) {
      setToast({
        id: Date.now(),
        tone: "error",
        message: "No pudimos asignar el administrador",
        subtitle:
          requestError.response?.data?.email?.[0] ||
          requestError.response?.data?.detail ||
          "Revisa los datos e inténtalo nuevamente.",
      });
    } finally {
      setBusy(false);
    }
  };
  const removeTenant = async () => {
    setBusy(true);
    try {
      const result = await deleteSaaSOrganization(selected.organizacion_id);
      setConfirmDelete(false);
      setSelectedId("");
      setToast({
        id: Date.now(),
        message: "Organización eliminada",
        subtitle: result.detail,
      });
      load();
    } catch (requestError) {
      setConfirmDelete(false);
      setToast({
        id: Date.now(),
        tone: "error",
        message: "No se puede eliminar la organización",
        subtitle:
          requestError.response?.data?.detail ||
          "La organización contiene información que debe conservarse.",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-5 rounded-[28px] bg-gradient-to-r from-slate-900 to-emerald-900 p-7 text-white shadow-xl lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-300">
            Clientes SaaS
          </p>
          <h1 className="mt-2 text-3xl font-black">Organizaciones</h1>
          <p className="mt-2 text-sm text-slate-200">
            Gestiona clientes, planes, estados de acceso y configuración SaaS
            desde una sola vista.
          </p>
        </div>
        <Button leftIcon={Plus} onClick={() => setCreateForm(initialCreate)}>
          Nueva organización
        </Button>
      </section>
      <Toast
        message={toast?.message}
        subtitle={toast?.subtitle}
        tone={toast?.tone}
        loading={toast?.loading}
        toastKey={toast?.id}
        onClose={() => setToast(null)}
      />
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm font-bold text-rose-800">
          {error}
        </div>
      )}
      <section className="grid min-h-[680px] gap-5 xl:grid-cols-[360px_1fr]">
        <aside className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
          <Input
            label="Buscar organizaciones"
            leftIcon={Search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Nombre, RUT, preset o plan"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              "todas",
              "activo",
              "piloto",
              "pago_pendiente",
              "suspendido",
              "cancelado",
            ].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatusFilter(value)}
                className={`rounded-full px-3 py-2 text-xs font-bold ${statusFilter === value ? "bg-emerald-800 text-white" : "bg-slate-100 text-slate-600"}`}
              >
                {value === "todas" ? "Todas" : labels[value]}
              </button>
            ))}
          </div>
          <div className="mt-4 space-y-2">
            {filtered.map((row) => (
              <button
                key={row.organizacion_id}
                type="button"
                onClick={() => setSelectedId(row.organizacion_id)}
                className={`w-full rounded-2xl border p-4 text-left transition ${selected?.organizacion_id === row.organizacion_id ? "border-emerald-400 bg-emerald-50" : "border-slate-200 hover:border-emerald-200"}`}
              >
                <div className="flex items-start gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 font-black text-white">
                    {initials(row.nombre)}
                  </span>
                  <div className="min-w-0">
                    <b className="block truncate">{row.nombre}</b>
                    <p className="mt-1 text-xs capitalize text-slate-500">
                      {row.preset} · {labels[row.plan]}
                    </p>
                    <div className="mt-2">
                      <StatusBadge tone={tones[row.estado]}>
                        {labels[row.estado]}
                      </StatusBadge>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </aside>
        {selected && form && (
          <article className="space-y-5 rounded-[24px] border border-slate-200 bg-white p-6 shadow-sm">
            <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex gap-4">
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-emerald-900 text-xl font-black text-white">
                  {initials(selected.nombre)}
                </span>
                <div>
                  <h2 className="text-2xl font-black">{selected.nombre}</h2>
                  <p className="mt-1 text-sm capitalize text-slate-500">
                    Gestión ambiental de {selected.preset} ·{" "}
                    {selected.uso.obras} obras activas
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <StatusBadge tone={tones[selected.estado]}>
                      {labels[selected.estado]}
                    </StatusBadge>
                    <StatusBadge
                      tone={
                        selected.disponibilidad === "operativo"
                          ? "success"
                          : "danger"
                      }
                    >
                      {selected.disponibilidad === "operativo"
                        ? "Acceso operativo"
                        : "Acceso bloqueado"}
                    </StatusBadge>
                    <StatusBadge tone={tones[selected.salud.key]}>
                      {selected.salud.label}
                    </StatusBadge>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {actions.map((row) => (
                  <Button
                    key={row.action}
                    variant={row.danger ? "danger" : "secondary"}
                    disabled={busy}
                    onClick={() => action(row.action)}
                  >
                    {row.label}
                  </Button>
                ))}
                {selected.eliminacion?.permitida && (
                  <Button variant="danger" leftIcon={Trash2} disabled={busy} onClick={() => setConfirmDelete(true)}>
                    Eliminar tenant
                  </Button>
                )}
              </div>
            </header>
            <section>
              <h3 className="font-black">Resumen operativo</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ["Usuarios activos", selected.uso.usuarios],
                  ["Obras activas", selected.uso.obras],
                  ["Documentos", selected.uso.documentos],
                  [
                    "Problemáticas abiertas",
                    selected.uso.problematicas_abiertas,
                  ],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-2xl font-black">
                      {formatNumber(value, 0)}
                    </p>
                    <p className="text-xs font-bold text-slate-500">{label}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Última actividad observable:{" "}
                {formatDateTime(selected.ultima_actividad)} ·{" "}
                {selected.salud.reason}
              </p>
            </section>
            <section className="rounded-2xl border border-slate-200 p-5">
              <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-800"><UserCog size={20} /></span><div><h3 className="font-black">Usuario administrador</h3><p className="text-xs text-slate-500">Consulta quién administra el tenant o vincula una cuenta nueva o existente.</p></div></div>
              <div className="mt-4 grid gap-3">{selected.administradores?.length ? selected.administradores.map((admin) => <div key={admin.membership_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-4"><div><b>{admin.nombre}</b><p className="text-sm text-slate-600">{admin.email} {admin.cargo ? `· ${admin.cargo}` : ""}</p></div><StatusBadge tone={admin.cuenta_activada && admin.activo ? "success" : "warning"}>{admin.cuenta_activada ? (admin.activo ? "Cuenta activa" : "Acceso desactivado") : "Activación pendiente"}</StatusBadge></div>) : <p className="rounded-xl bg-amber-50 p-4 text-sm font-bold text-amber-800">Este tenant no tiene un administrador asignado.</p>}</div>
              <div className="mt-5 grid gap-3 border-t border-slate-200 pt-5 sm:grid-cols-2 lg:grid-cols-4"><Input label="Nombre" value={adminForm.nombre} onChange={(event) => setAdminForm({ ...adminForm, nombre: event.target.value })} /><Input label="Apellido" value={adminForm.apellido} onChange={(event) => setAdminForm({ ...adminForm, apellido: event.target.value })} /><Input label="Correo electrónico" type="email" required value={adminForm.email} onChange={(event) => setAdminForm({ ...adminForm, email: event.target.value })} /><Input label="Cargo" value={adminForm.cargo} onChange={(event) => setAdminForm({ ...adminForm, cargo: event.target.value })} /></div>
              <div className="mt-4 flex justify-end"><Button leftIcon={UserCog} loading={busy} onClick={assignAdmin}>Crear o vincular administrador</Button></div>
            </section>
            {!selected.eliminacion?.permitida && <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">La eliminación está protegida porque este tenant ya contiene datos operacionales.</p>}
            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 p-5">
                <h3 className="font-black">Identidad empresarial</h3>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  {[
                    ["RUT", selected.rut],
                    ["Giro", selected.rubro],
                    ["Email", selected.email],
                    ["Teléfono", selected.telefono],
                    ["Región", selected.region],
                    ["Comuna", selected.comuna],
                    ["Dirección", selected.direccion],
                    ["Contacto", selected.contacto],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-xs text-slate-500">{label}</dt>
                      <dd className="font-bold">{value || "Sin informar"}</dd>
                    </div>
                  ))}
                </dl>
              </div>
              <div className="rounded-2xl border border-slate-200 p-5">
                <h3 className="font-black">Plan y acceso</h3>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <Select
                    label="Plan comercial"
                    value={form.plan}
                    onChange={(event) =>
                      setForm({ ...form, plan: event.target.value })
                    }
                  >
                    <option value="sin_plan">Sin plan</option>
                    <option value="starter">Starter</option>
                    <option value="professional">Professional</option>
                    <option value="enterprise">Enterprise</option>
                  </Select>
                  <Select
                    label="Preset ambiental"
                    value={form.preset}
                    onChange={(event) =>
                      setForm({ ...form, preset: event.target.value })
                    }
                  >
                    <option value="construccion">Construcción</option>
                    <option value="transporte">Transporte</option>
                    <option value="industrial">Industrial</option>
                    <option value="forestal">Forestal</option>
                    <option value="aserradero">Aserradero</option>
                  </Select>
                  <Input
                    type="date"
                    label="Fin de piloto"
                    value={form.fin_piloto}
                    onChange={(event) =>
                      setForm({ ...form, fin_piloto: event.target.value })
                    }
                  />
                  <Input
                    type="date"
                    label="Próximo vencimiento"
                    value={form.proximo_vencimiento}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        proximo_vencimiento: event.target.value,
                      })
                    }
                  />
                  <Input
                    className="sm:col-span-2"
                    label="Responsable comercial"
                    value={form.responsable_comercial}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        responsable_comercial: event.target.value,
                      })
                    }
                  />
                </div>
                <div className="mt-4 flex justify-end">
                  <Button loading={busy} onClick={save}>
                    Guardar configuración
                  </Button>
                </div>
                <p className="mt-3 flex gap-2 text-xs text-amber-700">
                  <ShieldAlert size={15} />
                  Cambiar el preset queda auditado y no modifica datos
                  históricos existentes.
                </p>
              </div>
            </section>
            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 p-5">
                <h3 className="font-black">Capacidades comerciales</h3>
                <p className="mt-1 text-xs text-slate-500">
                  El plan define disponibilidad comercial; RBAC continúa
                  controlando las acciones de cada usuario.
                </p>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {capabilities.map((label, index) => (
                    <div
                      key={label}
                      className={`rounded-xl px-3 py-2 text-sm font-bold ${index < planCapabilities[selected.plan] ? "bg-emerald-50 text-emerald-800" : "bg-slate-50 text-slate-400"}`}
                    >
                      {index < planCapabilities[selected.plan] ? "✓" : "—"}{" "}
                      {label}
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 p-5">
                <h3 className="font-black">Uso del plan</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Consumo observable. No se aplican bloqueos automáticos por
                  límites.
                </p>
                <div className="mt-4 space-y-3">
                  {[
                    [
                      "Usuarios",
                      selected.uso.usuarios,
                      selected.limites?.usuarios,
                    ],
                    ["Obras", selected.uso.obras, selected.limites?.obras],
                    [
                      "Documentos procesados",
                      selected.uso.documentos,
                      selected.limites?.documentos,
                    ],
                  ].map(([label, value, limit]) => (
                    <div key={label}>
                      <div className="flex justify-between text-sm">
                        <b>{label}</b>
                        <span>
                          {value}
                          {limit ? ` / ${limit}` : " · sin límite configurado"}
                        </span>
                      </div>
                      {limit && (
                        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-emerald-500"
                            style={{
                              width: `${Math.min(100, (value / limit) * 100)}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </article>
        )}
      </section>
      {confirmDelete && selected && (
        <Modal open title="Eliminar organización" description="Esta acción elimina definitivamente la identidad del tenant y su configuración inicial." onClose={() => setConfirmDelete(false)} footer={<div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setConfirmDelete(false)}>Conservar organización</Button><Button variant="danger" leftIcon={Trash2} loading={busy} onClick={removeTenant}>Eliminar definitivamente</Button></div>}>
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-900"><b>Vas a eliminar {selected.nombre}.</b><p className="mt-1">El sistema verificó que no tiene obras, registros, documentos, evidencias, importaciones ni otros datos operacionales.</p></div>
        </Modal>
      )}
      {createForm && (
        <Modal
          open
          size="lg"
          title="Nueva organización"
          description="Crea el espacio inicial del cliente y define quién administrará Carbono Zero dentro de la organización."
          onClose={() => {
            setCreateForm(null);
            setCreateAttempted(false);
          }}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setCreateForm(null)}>
                Cancelar
              </Button>
              <Button loading={busy} onClick={create}>
                Crear organización
              </Button>
            </div>
          }
        >
          <div className="space-y-6">
            <fieldset className="grid gap-4 sm:grid-cols-2">
              <legend className="mb-3 font-black">Organización</legend>
              <Input
                className="sm:col-span-2"
                label="Nombre"
                required
                value={createForm.nombre}
                onChange={(event) =>
                  setCreateForm({ ...createForm, nombre: event.target.value })
                }
              />
              <Select
                label="Sector principal"
                required
                value={createForm.sector}
                onChange={(event) =>
                  setCreateForm({ ...createForm, sector: event.target.value })
                }
              >
                <option value="">Selecciona un sector</option>
                <option value="construccion">Construcción</option>
                <option value="forestal">Forestal</option>
                <option value="aserradero">Aserradero</option>
                <option value="transporte">Transporte</option>
                <option value="industrial">Industrial</option>
              </Select>
            </fieldset>
            <fieldset className="grid gap-4 sm:grid-cols-2">
              <legend className="mb-3 font-black">Servicio</legend>
              <Select
                label="Plan"
                value={createForm.plan}
                onChange={(event) =>
                  setCreateForm({ ...createForm, plan: event.target.value })
                }
              >
                <option value="starter">Starter</option>
                <option value="professional">Professional</option>
                <option value="enterprise">Enterprise</option>
              </Select>
              <Select
                label="Estado inicial"
                value={createForm.estado}
                onChange={(event) =>
                  setCreateForm({ ...createForm, estado: event.target.value })
                }
              >
                <option value="piloto">Piloto</option>
                <option value="activo">Activo</option>
              </Select>
            </fieldset>
            <fieldset className="grid gap-4 sm:grid-cols-2">
              <legend className="mb-3 font-black">Administrador inicial</legend>
              <Input
                label="Nombre"
                required
                value={createForm.admin_nombre}
                onChange={(event) =>
                  setCreateForm({
                    ...createForm,
                    admin_nombre: event.target.value,
                  })
                }
              />
              <Input
                label="Apellido"
                required
                value={createForm.admin_apellido}
                onChange={(event) =>
                  setCreateForm({
                    ...createForm,
                    admin_apellido: event.target.value,
                  })
                }
              />
              <Input
                label="Email"
                required
                type="email"
                error={createAttempted && !isValidEmail(createForm.admin_email) ? "Ingresa un correo válido, por ejemplo nombre@empresa.cl." : undefined}
                value={createForm.admin_email}
                onChange={(event) =>
                  setCreateForm({
                    ...createForm,
                    admin_email: event.target.value,
                  })
                }
              />
              <Input
                label="Cargo"
                value={createForm.admin_cargo}
                onChange={(event) =>
                  setCreateForm({
                    ...createForm,
                    admin_cargo: event.target.value,
                  })
                }
              />
            </fieldset>
          </div>
        </Modal>
      )}
    </div>
  );
}

function initials(name) {
  return String(name || "CZ")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}
function isValidEmail(value) { return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(value || "").trim()); }
function naturalCreateError(requestError) {
  const data = requestError?.response?.data;
  const raw = data?.admin_email?.[0] || data?.rut?.[0] || data?.nombre?.[0] || data?.detail;
  if (/correo|email/i.test(String(raw || ""))) return "Ingresa un correo válido, por ejemplo nombre@empresa.cl.";
  if (/rut|d[ií]gito|verificador/i.test(String(raw || "")))
    return "El RUT ya está registrado o su dígito verificador no corresponde.";
  if (/nombre|required|blank/i.test(String(raw || "")))
    return "Revisa el nombre de la organización e inténtalo nuevamente.";
  return "Revisa los datos ingresados e inténtalo nuevamente.";
}
function validActions(state) {
  if (state === "cancelado")
    return [{ action: "reactivar", label: "Reabrir y reactivar" }];
  if (state === "suspendido")
    return [
      { action: "reactivar", label: "Reactivar" },
      { action: "cancelar", label: "Cancelar", danger: true },
    ];
  if (state === "pago_pendiente")
    return [
      { action: "reactivar", label: "Regularizar y reactivar" },
      { action: "suspender", label: "Suspender", danger: true },
      { action: "cancelar", label: "Cancelar", danger: true },
    ];
  if (state === "piloto")
    return [
      { action: "activar", label: "Convertir a plan" },
      { action: "suspender", label: "Suspender", danger: true },
      { action: "cancelar", label: "Cancelar", danger: true },
    ];
  return [
    { action: "pago_pendiente", label: "Marcar pago pendiente" },
    { action: "suspender", label: "Suspender", danger: true },
    { action: "cancelar", label: "Cancelar", danger: true },
  ];
}
