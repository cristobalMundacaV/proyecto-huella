import {
  BarChart3,
  Boxes,
  Building2,
  Database,
  DatabaseZap,
  Factory,
  FileCheck2,
  Flame,
  LayoutDashboard,
  LogOut,
  Settings,
  UsersRound,
} from "lucide-react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";

function Sidebar({ activeView, onSetActiveView, systemStatus }) {
  const { logout, user } = useAuth();
  const { activeEmpresaId, empresas, loadingEmpresas, setActiveEmpresa } =
    useEmpresaActiva();

  const navigationItems = [
    {
      icon: LayoutDashboard,
      label: "Panel principal",
      view: "dashboard",
    },
    {
      icon: Flame,
      label: "Emisiones",
      view: "emisiones",
    },
    {
      icon: Building2,
      label: "Empresas",
      view: "empresas",
    },
    {
      icon: Factory,
      label: "Unidades Operativas",
      view: "unidades",
    },
    {
      icon: Boxes,
      label: "Lotes",
      view: "lotes",
    },
    {
      icon: BarChart3,
      label: "Reportes",
      view: "reportes",
    },
    {
      icon: DatabaseZap,
      label: "Importación de datos",
      view: "importaciones",
    },
    {
      icon: FileCheck2,
      label: "Evidencias",
      view: "evidencias",
    },
    {
      icon: UsersRound,
      label: "Usuarios",
      view: "usuarios",
    },
    {
      icon: Settings,
      label: "Configuración",
      view: "configuracion",
    },
  ];
  const statusItems = [
    ["Unidades", systemStatus?.unidades ?? 0],
    ["Lotes", systemStatus?.lotes ?? 0],
    ["Actividades", systemStatus?.actividades ?? 0],
    ["Evidencias", systemStatus?.evidencias ?? 0],
    ["Pasaportes", systemStatus?.pasaportes ?? 0],
  ];

  return (
    <aside className="w-full shrink-0 border-b border-slate-800 bg-slate-900 p-4 sm:p-6 lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
      <div className="mb-10 flex items-center gap-3">
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
          <Database className="text-emerald-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold">Carbono Zero</h2>
          <p className="text-xs text-slate-400">Carbon Intelligence</p>
        </div>
      </div>

      <section className="mb-8 rounded-3xl border border-slate-800 bg-slate-950 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Empresa activa
        </p>
        <div className="mt-3 space-y-3">
          <select
            value={activeEmpresaId}
            onChange={(event) => {
              const selected = empresas.find(
                (empresa) => String(empresa.empresa_id) === String(event.target.value)
              );

              if (selected) {
                setActiveEmpresa(selected);
              }
            }}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
          >
            <option value="">Selecciona una empresa</option>
            {empresas.map((empresa) => (
              <option key={empresa.empresa_id} value={empresa.empresa_id}>
                {empresa.nombre}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => onSetActiveView("empresas", { openCreateEmpresa: true })}
            className="w-full rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-400/20"
          >
            Nueva empresa
          </button>

          {loadingEmpresas && (
            <p className="text-xs text-slate-500">Cargando empresas...</p>
          )}
        </div>
      </section>

      <nav className="space-y-3">
        <p className="px-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Navegacion principal
        </p>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.view;

          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onSetActiveView(item.view)}
              disabled={item.disabled}
              className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 transition ${
                isActive
                  ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                  : item.disabled
                    ? "cursor-not-allowed border-slate-800 bg-slate-900 text-slate-500"
                    : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <p className="text-xs text-slate-500">Estado de la empresa</p>
        <div className="mt-3 space-y-2">
          {statusItems.map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-4 text-sm"
            >
              <span className="text-slate-400">{label}:</span>
              <span className="font-semibold text-slate-100">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <p className="text-xs text-slate-500">Sesion activa</p>
        <p className="mt-2 text-sm font-semibold text-slate-100">
          {user?.nombre || user?.username || "Usuario"}
        </p>
        <button
          type="button"
          onClick={logout}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-rose-400/30 hover:bg-rose-400/10 hover:text-rose-100"
        >
          <LogOut size={16} />
          Cerrar sesion
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
