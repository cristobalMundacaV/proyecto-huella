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
  inteligencia: DatabaseZap,
  emisiones: Flame,
  operacion: Factory,
  administracion: Settings,
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
    <aside className="w-full shrink-0 border-b border-[var(--sidebar-border)] bg-[var(--sidebar)] p-4 text-[var(--text-main)] shadow-[18px_0_50px_rgba(19,34,56,0.06)] sm:p-6 lg:sticky lg:top-[72px] lg:flex lg:h-[calc(100vh-72px)] lg:w-72 lg:flex-col lg:border-b-0 lg:border-r lg:overflow-y-auto">
      <section className="group mb-9 mt-2 rounded-2xl border border-[var(--sidebar-border)] bg-white/64 p-4 shadow-[0_12px_28px_rgba(19,34,56,0.05)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-white/84 hover:shadow-[0_18px_36px_rgba(19,34,56,0.08)]">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] transition group-hover:text-[var(--primary-dark)]">
          Estado de la empresa
        </p>

        <div className="mt-3 space-y-2">
          {statusItems.map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-4 rounded-xl px-2 py-1 text-sm transition group-hover:bg-emerald-50/70"
            >
              <span className="text-slate-600">{label}</span>
              <span className="font-black text-[var(--primary-dark)]">{value}</span>
            </div>
          ))}
        </div>
      </section>

      <nav className="space-y-2">
        <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">
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
              className={`sidebar-nav-item flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-bold transition ${isActive
                  ? "sidebar-nav-item--active border-emerald-200 bg-[var(--sidebar-active)] text-[var(--primary-dark)] shadow-[0_12px_28px_rgba(15,124,109,0.12)]"
                  : item.disabled
                    ? "cursor-not-allowed border-transparent bg-white/30 text-slate-400"
                    : "border-transparent bg-transparent text-slate-600 hover:-translate-x-0.5 hover:border-[var(--border)] hover:bg-white/75 hover:text-[var(--primary-dark)]"
                }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-9 space-y-5 pb-6 lg:mt-auto">
        <div className="mx-auto h-px w-[82%] bg-gradient-to-r from-transparent via-[var(--sidebar-border)] to-transparent" />

        <section className="group rounded-2xl border border-[var(--sidebar-border)] bg-white/62 p-4 shadow-[0_12px_28px_rgba(19,34,56,0.05)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-white/85 hover:shadow-[0_18px_36px_rgba(19,34,56,0.08)]">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] transition group-hover:text-[var(--primary-dark)]">
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
              className="w-full rounded-xl border border-[var(--border)] bg-white px-4 py-3 text-sm font-bold text-[var(--text-main)] shadow-sm outline-none transition focus:border-emerald-300/60 focus:ring-4 focus:ring-emerald-400/10"
            >
              <option value="">Selecciona una empresa</option>
              {constructoras.map((constructora) => (
                <option key={constructora.constructora_id} value={constructora.constructora_id}>
                  {constructora.nombre}
                </option>
              ))}
            </select>

            {loadingConstructoras && (
              <p className="text-xs text-[var(--text-muted)]">Cargando empresas...</p>
            )}

            <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 px-3 py-2 text-center text-[11px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
              Preset: {getPresetLabel(activePresetKey)}
            </div>

            <button
              type="button"
              onClick={() => onSetActiveView?.("administracion")}
              className="w-full rounded-xl border border-[var(--border)] bg-white px-3 py-2 text-xs font-bold text-[var(--primary-dark)] shadow-sm transition hover:border-emerald-200 hover:bg-emerald-50"
            >
              Gestionar administración
            </button>
          </div>
        </section>
      </div>
    </aside>
  );
}

export default Sidebar;
