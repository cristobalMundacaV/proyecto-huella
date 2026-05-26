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
        description="Los usuarios se crean dentro de la Constructora activa."
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
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
            <UsersRound className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">Usuarios</h1>
            <p className="max-w-3xl text-slate-400">
              Administra accesos y roles para {activeConstructora.nombre}.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setFormOpen((current) => !current)}
          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20"
        >
          <Plus size={18} />
          Nuevo usuario
        </button>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <UserKpi icon={<UsersRound />} label="Usuarios registrados" value={usuarios.length} />
        <UserKpi icon={<ShieldCheck />} label="Usuarios activos" value={activeUsers} />
        <UserKpi icon={<UserRound />} label="Constructora" value={activeConstructora.nombre} />
      </section>

      {formOpen && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/75 px-4 py-6 backdrop-blur-sm">
          <form
            onSubmit={handleCreateUser}
            className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-3xl border border-slate-700 bg-slate-900 p-4 shadow-2xl sm:p-6"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-emerald-300">Nuevo acceso</p>
                <h2 className="mt-1 text-xl font-bold text-slate-100">
                  Crear usuario en {activeConstructora.nombre}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="rounded-2xl border border-slate-700 bg-slate-950 p-3 text-slate-300 transition hover:bg-slate-800 hover:text-white"
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
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Rol</span>
                <select
                  name="rol"
                  onChange={updateForm}
                  value={form.rol}
                  className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
                >
                  <option value="admin">Administrador</option>
                  <option value="analista">Analista</option>
                  <option value="operador">Operador</option>
                  <option value="lector">Lector</option>
                </select>
              </label>
              <label className="flex items-center gap-3 self-end rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                <input
                  checked={form.activo}
                  name="activo"
                  onChange={updateForm}
                  type="checkbox"
                />
                Usuario activo
              </label>
            </div>

            {error && (
              <p className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-100">
                {error}
              </p>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="rounded-2xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-200"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:opacity-60"
              >
                {saving ? "Creando..." : "Crear usuario"}
              </button>
            </div>
          </form>
        </div>
      )}

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5">
          <h2 className="text-xl font-bold text-slate-100">Usuarios de la constructora</h2>
          <p className="mt-1 text-sm text-slate-400">
            {loading ? "Cargando usuarios..." : `${usuarios.length} usuarios encontrados.`}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Usuario</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Rol</th>
                <th className="px-4 py-3">Cargo</th>
                <th className="px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => (
                <tr key={usuario.id} className="border-b border-slate-800/80">
                  <td className="px-4 py-4 font-semibold text-slate-100">{usuario.nombre}</td>
                  <td className="px-4 py-4 text-slate-300">{usuario.username}</td>
                  <td className="px-4 py-4 text-slate-300">{usuario.email || "-"}</td>
                  <td className="px-4 py-4">
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200">
                      {usuario.rol}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-slate-300">{usuario.cargo || "-"}</td>
                  <td className="px-4 py-4 font-semibold text-slate-200">
                    {usuario.activo ? "Activo" : "Inactivo"}
                  </td>
                </tr>
              ))}
              {!loading && usuarios.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-400" colSpan={6}>
                    No hay usuarios registrados para esta Constructora.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Field({ label, name, onChange, required = false, type = "text", value }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <input
        name={name}
        onChange={onChange}
        required={required}
        type={type}
        value={value}
        className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
      />
    </label>
  );
}

function UserKpi({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className="text-cyan-300">{icon}</div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </p>
      </div>
      <p className="line-clamp-2 text-2xl font-black text-slate-100">{value}</p>
    </div>
  );
}

export default UsuariosPage;
