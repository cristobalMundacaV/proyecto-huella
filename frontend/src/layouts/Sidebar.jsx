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
  Settings,
  UsersRound,
} from "lucide-react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getActivePreset, getPresetLabel } from "@/presets/registry";

const navigationIconMap = {
  dashboard: LayoutDashboard,
  emisiones: Flame,
  factores: Database,
  constructoras: Building2,
  obras: Boxes,
  etapas: Factory,
  evidencias: FileCheck2,
  importaciones: DatabaseZap,
  reportes: BarChart3,
  usuarios: UsersRound,
  configuracion: Settings,
  recepcion_trozas: Database,
  produccion: Factory,
  secado: Flame,
  energia: DatabaseZap,
  transporte_forestal: Factory,
  residuos_subproductos: Boxes,
  flota: Factory,
  viajes: BarChart3,
  combustible: Flame,
  rutas: Database,
  mantenciones: Settings,
};

function Sidebar({ activeView, onSetActiveView, systemStatus }) {
  const {
    activeConstructora,
    activeConstructoraId,
    clearActiveConstructora,
    constructoras,
    loadingConstructoras,
    setActiveConstructora,
  } = useConstructoraActiva();

  const activePresetKey = activeConstructora?.preset || "construccion";
  const activePreset = getActivePreset(activePresetKey);

  const navigationItems = (activePreset.navigation || []).map((item) => ({
    ...item,
    icon: navigationIconMap[item.view] || LayoutDashboard,
  }));

  const statusItems = [
    [activePreset.processPluralLabel, systemStatus?.etapas ?? 0],
    [activePreset.unitPluralLabel, systemStatus?.obras ?? 0],
    ["Registros", systemStatus?.registros_emision ?? 0],
    ["Evidencias", systemStatus?.evidencias ?? 0],
    ["Fichas", systemStatus?.fichas_ambientales ?? 0],
  ];

  return (
    <aside className="w-full shrink-0 border-b border-white/10 bg-[var(--sidebar)] p-4 text-slate-100 shadow-[24px_0_80px_rgba(2,6,23,0.22)] sm:p-6 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-72 lg:flex-col lg:border-b-0 lg:border-r lg:overflow-y-auto">
      <nav className="space-y-3">
        <p className="px-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Navegación principal
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
              className={`sidebar-nav-item flex w-full items-center gap-3 rounded-2xl border px-4 py-3 transition ${isActive
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

      <section className="group mt-8 rounded-2xl border border-white/10 bg-white/5 p-4 shadow-[0_12px_28px_rgba(15,23,42,0.16)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/20 hover:bg-white/7 hover:shadow-[0_18px_36px_rgba(15,23,42,0.22)]">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 transition group-hover:text-emerald-200">
          Estado de la empresa
        </p>

        <div className="mt-3 space-y-2">
          {statusItems.map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-4 rounded-xl px-2 py-1 text-sm transition group-hover:bg-white/5"
            >
              <span className="text-slate-400">{label}</span>
              <span className="font-black text-emerald-100">{value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="group mt-6 rounded-2xl border border-emerald-300/15 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))] p-4 shadow-[0_12px_28px_rgba(0,0,0,0.14)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/40 hover:shadow-[0_18px_36px_rgba(0,0,0,0.2)] lg:mt-auto">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 transition group-hover:text-emerald-200">
          Empresa activa
        </p>

        <div className="mt-3 space-y-3">
          <select
            value={activeConstructoraId}
            onChange={(event) => {
              const selected = constructoras.find(
                (constructora) =>
                  String(constructora.constructora_id) === String(event.target.value)
              );

              if (selected) {
                setActiveConstructora(selected);
              } else {
                clearActiveConstructora();
              }
            }}
            className="w-full rounded-xl border border-emerald-300/18 bg-[var(--sidebar-active)] px-4 py-3 text-sm text-slate-50 shadow-[0_10px_18px_rgba(0,0,0,0.18)] outline-none transition focus:border-emerald-300/60 focus:ring-4 focus:ring-emerald-400/10"
          >
            <option value="">Selecciona una empresa</option>
            {constructoras.map((constructora) => (
              <option key={constructora.constructora_id} value={constructora.constructora_id}>
                {constructora.nombre}
              </option>
            ))}
          </select>

          {loadingConstructoras && (
            <p className="text-xs text-slate-500">Cargando empresas...</p>
          )}

          <div className="rounded-xl border border-emerald-300/15 bg-white/5 px-3 py-2 text-center text-[11px] font-black uppercase tracking-wide text-emerald-100">
            Preset: {getPresetLabel(activePresetKey)}
          </div>

          <button
            type="button"
            onClick={() => onSetActiveView?.("constructoras")}
            className="w-full rounded-xl border border-emerald-300/15 bg-white/5 px-3 py-2 text-xs font-bold text-emerald-100 transition hover:border-emerald-200/40 hover:bg-white/10"
          >
            Gestionar empresas
          </button>
        </div>
      </section>
    </aside>
  );
}

export default Sidebar;