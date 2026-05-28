import { useEffect, useMemo, useState } from "react";
import { Plus, ShieldCheck, UserRound, UsersRound, X } from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import {
  createConstructoraUsuario,
  getConstructoraUsuarios,
} from "@/shared/services/api";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";

const emptyForm = {
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  password: "",
  rol: "analista",
  cargo: "",
  activo: true,
};

const roleLabels = {
  admin: "Administrador",
  analista: "Analista",
  operador: "Operador",
  lector: "Lector",
};

function UsuariosPage() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const activeUsers = useMemo(
    () => usuarios.filter((usuario) => usuario.activo).length,
    [usuarios]
  );

  useEffect(() => {
    if (!activeConstructoraId) {
      setUsuarios([]);
      setLoading(false);
      return;
    }

    let isCancelled = false;
    setLoading(true);
    setError("");

    getConstructoraUsuarios(activeConstructoraId)
      .then((data) => {
        if (!isCancelled) {
          setUsuarios(Array.isArray(data) ? data : []);
        }
      })
      .catch((requestError) => {
        if (!isCancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar los usuarios."
          );
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [activeConstructoraId]);

  if (!activeConstructora) {
    return (
      <EmptyState
        title="Selecciona una constructora"
        description="Los usuarios se crean dentro de la constructora activa."
      />
    );
  }

  const updateForm = (event) => {
    const { name, type, checked, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
    setError("");
  };

  const closeForm = () => {
    setFormOpen(false);
    setForm(emptyForm);
    setError("");
  };

  const handleCreateUser = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");

    try {
      const created = await createConstructoraUsuario(activeConstructoraId, form);
      setUsuarios((current) => [created, ...current]);
      setForm(emptyForm);
      setFormOpen(false);
    } catch (requestError) {
      const responseData = requestError.response?.data;
      const firstError =
        responseData && typeof responseData === "object"
          ? Object.values(responseData).flat().join(" ")
          : "";
      setError(firstError || "No se pudo crear el usuario.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-emerald-200/80 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(209,250,229,0.9))] p-3 text-[#0F766E] shadow-[0_14px_30px_rgba(14,124,102,0.14)] ring-1 ring-white/70">
            <UsersRound size={30} strokeWidth={2.1} />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight text-[#0F172A] sm:text-4xl">
              Usuarios
            </h1>
            <p className="max-w-3xl text-[#475569]">
              Administra accesos, roles y permisos operativos para {activeConstructora.nombre}.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setFormOpen(true)}
          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#99F6E4] bg-[#F0FDFA] px-5 py-3 text-sm font-bold text-[#0F766E] shadow-[0_12px_24px_rgba(14,124,102,0.12)] transition hover:border-[#5EEAD4] hover:bg-[#CCFBF1] sm:w-fit"
        >
          <Plus size={18} />
          Nuevo usuario
        </button>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <UserKpi
          icon={UsersRound}
          label="Usuarios registrados"
          value={usuarios.length}
          description="Accesos vinculados"
          tone="teal"
        />
        <UserKpi
          icon={ShieldCheck}
          label="Usuarios activos"
          value={activeUsers}
          description="Cuentas habilitadas"
          tone="green"
        />
        <UserKpi
          icon={UserRound}
          label="Constructora"
          value={activeConstructora.nombre}
          description="Empresa seleccionada"
          tone="blue"
        />
      </section>

      {formOpen && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
          <form
            onSubmit={handleCreateUser}
            className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[28px] border border-[#CBD5E1] bg-white p-4 shadow-[0_24px_70px_rgba(15,23,42,0.24)] sm:p-6"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl border border-[#99F6E4] bg-[#F0FDFA] p-3 text-[#0F766E]">
                  <UserRound size={22} strokeWidth={2.1} />
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">
                    Nuevo acceso
                  </p>
                  <h2 className="mt-1 text-2xl font-black tracking-tight text-[#0F172A]">
                    Crear usuario
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-[#64748B]">
                    El usuario quedará vinculado a {activeConstructora.nombre} con el rol seleccionado.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeForm}
                className="rounded-2xl border border-[#E2E8F0] bg-white p-3 text-[#64748B] shadow-[0_8px_20px_rgba(15,23,42,0.08)] transition hover:border-[#CBD5E1] hover:text-[#0F172A]"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <Field label="Usuario" name="username" onChange={updateForm} required value={form.username} />
              <Field label="Email" name="email" onChange={updateForm} type="email" value={form.email} />
              <Field label="Clave" name="password" onChange={updateForm} required type="password" value={form.password} />
              <Field label="Nombre" name="first_name" onChange={updateForm} value={form.first_name} />
              <Field label="Apellido" name="last_name" onChange={updateForm} value={form.last_name} />
              <Field label="Cargo" name="cargo" onChange={updateForm} value={form.cargo} />
              <label className="block">
                <span className="text-xs font-black uppercase tracking-[0.18em] text-[#64748B]">Rol</span>
                <select
                  name="rol"
                  onChange={updateForm}
                  value={form.rol}
                  className="mt-2 h-12 w-full rounded-2xl border border-[#CBD5E1] bg-white px-4 text-sm font-semibold text-[#0F172A] outline-none transition focus:border-[#14B8A6] focus:ring-4 focus:ring-[#99F6E4]/40"
                >
                  <option value="admin">Administrador</option>
                  <option value="analista">Analista</option>
                  <option value="operador">Operador</option>
                  <option value="lector">Lector</option>
                </select>
              </label>
              <label className="flex h-12 items-center gap-3 self-end rounded-2xl border border-[#CBD5E1] bg-[#F8FAFC] px-4 text-sm font-bold text-[#334155]">
                <input
                  checked={form.activo}
                  name="activo"
                  onChange={updateForm}
                  type="checkbox"
                  className="h-4 w-4 accent-[#0F766E]"
                />
                Usuario activo
              </label>
            </div>

            {error && (
              <p className="mt-4 rounded-2xl border border-[#FDA29B] bg-[#FEF3F2] p-3 text-sm font-semibold text-[#B42318]">
                {error}
              </p>
            )}

            <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={closeForm}
                className="rounded-2xl border border-[#CBD5E1] bg-white px-5 py-3 text-sm font-bold text-[#334155] shadow-[0_8px_20px_rgba(15,23,42,0.06)] transition hover:border-[#94A3B8]"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-2xl border border-[#0F766E] bg-[#0F766E] px-5 py-3 text-sm font-bold text-white shadow-[0_14px_28px_rgba(14,124,102,0.22)] transition hover:bg-[#115E59] disabled:opacity-60"
              >
                {saving ? "Creando..." : "Crear usuario"}
              </button>
            </div>
          </form>
        </div>
      )}

      <section className="rounded-[28px] border border-[#CBD5E1] bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.08)] sm:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">
              Gestión de accesos
            </p>
            <h2 className="mt-1 text-2xl font-black tracking-tight text-[#0F172A]">
              Usuarios de la constructora
            </h2>
            <p className="mt-1 text-sm text-[#64748B]">
              {loading ? "Cargando usuarios..." : `${usuarios.length} usuarios encontrados.`}
            </p>
          </div>
          <span className="w-fit rounded-full border border-[#BFDBFE] bg-[#EFF6FF] px-4 py-2 text-sm font-black text-[#1D4ED8]">
            {activeUsers} activos
          </span>
        </div>

        <div className="overflow-hidden rounded-[22px] border border-[#E2E8F0]">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC] text-center text-xs font-black uppercase tracking-[0.08em] text-[#64748B]">
                  <th className="px-4 py-4">Nombre</th>
                  <th className="px-4 py-4">Usuario</th>
                  <th className="px-4 py-4">Email</th>
                  <th className="px-4 py-4">Rol</th>
                  <th className="px-4 py-4">Cargo</th>
                  <th className="px-4 py-4">Estado</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((usuario) => (
                  <tr key={usuario.id} className="border-b border-[#E2E8F0] text-center last:border-b-0 even:bg-[#F8FAFC]/70">
                    <td className="px-4 py-4 font-black text-[#0F172A]">{usuario.nombre}</td>
                    <td className="px-4 py-4 font-semibold text-[#334155]">{usuario.username}</td>
                    <td className="px-4 py-4 text-[#475569]">{usuario.email || "-"}</td>
                    <td className="px-4 py-4">
                      <span className="inline-flex rounded-full border border-[#99F6E4] bg-[#F0FDFA] px-3 py-1 text-xs font-black text-[#0F766E]">
                        {roleLabels[usuario.rol] || usuario.rol}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-[#475569]">{usuario.cargo || "-"}</td>
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex rounded-full border px-3 py-1 text-xs font-black ${
                          usuario.activo
                            ? "border-[#A7F3D0] bg-[#ECFDF3] text-[#047857]"
                            : "border-[#E2E8F0] bg-[#F8FAFC] text-[#64748B]"
                        }`}
                      >
                        {usuario.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                  </tr>
                ))}
                {!loading && usuarios.length === 0 && (
                  <tr>
                    <td className="px-4 py-12" colSpan={6}>
                      <div className="mx-auto flex max-w-xl flex-col items-center rounded-[24px] border border-dashed border-[#CBD5E1] bg-[#F8FAFC] px-6 py-8 text-center">
                        <div className="mb-3 rounded-full border border-[#99F6E4] bg-[#F0FDFA] p-4 text-[#0F766E]">
                          <UsersRound size={28} strokeWidth={2.1} />
                        </div>
                        <p className="text-lg font-black text-[#0F172A]">
                          Aún no hay usuarios registrados
                        </p>
                        <p className="mt-2 text-sm leading-6 text-[#64748B]">
                          Crea accesos para analistas, operadores o lectores de la constructora seleccionada.
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

function Field({ label, name, onChange, required = false, type = "text", value }) {
  return (
    <label className="block">
      <span className="text-xs font-black uppercase tracking-[0.18em] text-[#64748B]">
        {label}
      </span>
      <input
        name={name}
        onChange={onChange}
        required={required}
        type={type}
        value={value}
        className="mt-2 h-12 w-full rounded-2xl border border-[#CBD5E1] bg-white px-4 text-sm font-semibold text-[#0F172A] outline-none transition placeholder:text-[#94A3B8] focus:border-[#14B8A6] focus:ring-4 focus:ring-[#99F6E4]/40"
      />
    </label>
  );
}

function UserKpi({ icon: Icon, label, value, description, tone = "teal" }) {
  const tones = {
    teal: {
      card: "border-[#99F6E4] bg-[#F0FDFA]",
      icon: "border-[#99F6E4] bg-white text-[#0F766E]",
      value: "text-[#0F766E]",
    },
    green: {
      card: "border-[#A7F3D0] bg-[#ECFDF3]",
      icon: "border-[#A7F3D0] bg-white text-[#047857]",
      value: "text-[#047857]",
    },
    blue: {
      card: "border-[#BFDBFE] bg-[#EFF6FF]",
      icon: "border-[#BFDBFE] bg-white text-[#1D4ED8]",
      value: "text-[#1D4ED8]",
    },
  };
  const selectedTone = tones[tone] || tones.teal;

  return (
    <div className={`flex min-h-[8.5rem] flex-col rounded-[24px] border p-5 text-center shadow-[0_18px_45px_rgba(15,23,42,0.08)] ${selectedTone.card}`}>
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border bg-white shadow-[0_8px_20px_rgba(15,23,42,0.06)] ${selectedTone.icon}">
        <Icon size={24} strokeWidth={2.1} />
      </div>
      <p className="mt-3 text-[11px] font-black uppercase tracking-[0.2em] text-[#64748B]">
        {label}
      </p>
      <p className={`mt-2 line-clamp-2 text-2xl font-black leading-tight tracking-tight ${selectedTone.value}`}>
        {value}
      </p>
      {description ? <p className="mt-1 text-sm font-semibold text-[#64748B]">{description}</p> : null}
    </div>
  );
}

export default UsuariosPage;
