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
<aside className="w-full shrink-0 border-b border-white/10 bg-[var(--sidebar)] p-4 text-slate-100 sm:p-6 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-72 lg:flex-col lg:border-b-0 lg:border-r lg:overflow-y-auto">
      <div className="mb-10 flex items-center gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/10 p-3">
          <Database className="text-[var(--primary)]" />
        </div>
        <div>
          <h2 className="text-xl font-bold">Carbono Zero</h2>
          <p className="text-xs text-slate-400">Carbon Intelligence</p>
        </div>
      </div>

      <section className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-4">
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
            className="w-full rounded-xl border border-white/10 bg-[var(--sidebar-active)] px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-[var(--primary)]"
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
            className="w-full rounded-xl border border-[var(--primary)]/30 bg-[var(--primary)] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[var(--primary-dark)]"
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
              className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 transition ${
                isActive
                  ? "border-[var(--primary)]/30 bg-[var(--sidebar-active)] text-white"
                  : item.disabled
                    ? "cursor-not-allowed border-white/10 bg-white/5 text-slate-500"
                    : "border-transparent bg-transparent text-slate-300 hover:border-white/10 hover:bg-white/10"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-10 rounded-2xl border border-white/10 bg-white/5 p-4">
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

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-xs text-slate-500">Sesion activa</p>
        <p className="mt-2 text-sm font-semibold text-slate-100">
          {user?.nombre || user?.username || "Usuario"}
        </p>
        <button
          type="button"
          onClick={logout}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-red-300/30 hover:bg-red-500/10 hover:text-red-100"
        >
          <LogOut size={16} />
          Cerrar sesion
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
