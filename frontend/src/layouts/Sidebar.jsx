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
      label: "Constructoras",
      view: "empresas",
    },
    {
      icon: Factory,
      label: "Etapas / frentes",
      view: "unidades",
    },
    {
      icon: Boxes,
      label: "Obras",
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
    ["Etapas / frentes", systemStatus?.unidades ?? 0],
    ["Obras", systemStatus?.lotes ?? 0],
    ["Registros", systemStatus?.actividades ?? 0],
    ["Evidencias", systemStatus?.evidencias ?? 0],
    ["Fichas", systemStatus?.pasaportes ?? 0],
  ];

  return (
    <aside className="w-full shrink-0 border-b border-white/10 bg-[var(--sidebar)] p-4 text-slate-100 shadow-[24px_0_80px_rgba(2,6,23,0.22)] sm:p-6 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-72 lg:flex-col lg:border-b-0 lg:border-r lg:overflow-y-auto">
      <div className="mb-10 flex items-center gap-3">
        <div className="rounded-2xl border border-emerald-300/20 bg-[linear-gradient(180deg,rgba(18,61,52,1),rgba(15,45,39,0.96))] p-3 shadow-[0_16px_30px_rgba(0,0,0,0.24)] ring-1 ring-emerald-200/10">
          <Database className="text-emerald-300" />
        </div>
        <div>
          <h2 className="text-xl font-black tracking-tight">Carbono Zero</h2>
          <p className="text-xs text-slate-400">Inteligencia ambiental para obras</p>
        </div>
      </div>

      <section className="group mb-8 rounded-2xl border border-emerald-300/15 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))] p-4 shadow-[0_12px_28px_rgba(0,0,0,0.14)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/40 hover:shadow-[0_18px_36px_rgba(0,0,0,0.2)]">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 transition group-hover:text-emerald-200">
          Constructora activa
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
            className="w-full rounded-xl border border-emerald-300/18 bg-[var(--sidebar-active)] px-4 py-3 text-sm text-slate-50 shadow-[0_10px_18px_rgba(0,0,0,0.18)] outline-none transition focus:border-emerald-300/60 focus:ring-4 focus:ring-emerald-400/10"
          >
            <option value="">Selecciona una constructora</option>
            {empresas.map((empresa) => (
              <option key={empresa.empresa_id} value={empresa.empresa_id}>
                {empresa.nombre}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => onSetActiveView("empresas", { openCreateEmpresa: true })}
            className="w-full rounded-2xl border border-[var(--primary)]/35 bg-[linear-gradient(180deg,var(--primary),var(--primary-dark))] px-3 py-2 text-xs font-bold text-white shadow-[0_14px_28px_rgba(14,124,102,0.28)] transition hover:-translate-y-px hover:shadow-[0_16px_32px_rgba(14,124,102,0.34)] active:scale-[0.98]"
          >
            Nueva constructora
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
              className={`sidebar-nav-item flex w-full items-center gap-3 rounded-2xl border px-4 py-3 transition ${
                isActive
                  ? "sidebar-nav-item--active border-[var(--primary)]/35 bg-[var(--sidebar-active)] text-white"
                  : item.disabled
                    ? "cursor-not-allowed border-white/10 bg-white/5 text-slate-500"
                    : "border-transparent bg-transparent text-slate-300 hover:-translate-x-0.5 hover:border-white/10 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="group mt-10 rounded-2xl border border-white/10 bg-white/5 p-4 shadow-[0_12px_28px_rgba(15,23,42,0.16)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/20 hover:bg-white/7 hover:shadow-[0_18px_36px_rgba(15,23,42,0.22)]">
        <p className="text-xs text-slate-500 transition group-hover:text-emerald-200">
          Estado de la empresa
        </p>
        <div className="mt-3 space-y-2">
          {statusItems.map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-4 rounded-xl px-2 py-1 text-sm transition group-hover:bg-white/5"
            >
              <span className="text-slate-400">{label}:</span>
              <span className="font-semibold text-slate-100">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="group mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 shadow-[0_12px_28px_rgba(15,23,42,0.16)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/20 hover:bg-white/7 hover:shadow-[0_18px_36px_rgba(15,23,42,0.22)]">
        <p className="text-xs text-slate-500 transition group-hover:text-emerald-200">Sesion activa</p>
        <p className="mt-2 text-sm font-semibold text-slate-100">
          {user?.nombre || user?.username || "Usuario"}
        </p>
        <button
          type="button"
          onClick={logout}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:-translate-y-px hover:border-red-300/30 hover:bg-red-500/10 hover:text-red-100 active:scale-[0.98]"
        >
          <LogOut size={16} />
          Cerrar sesion
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
