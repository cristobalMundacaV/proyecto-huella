import { NavLink } from "react-router-dom";
import { BarChart3, Building2, Database, Factory, FileOutput, History, Leaf, UsersRound } from "lucide-react";

export const settingsSections = [
  { to: "/administracion/organizacion", label: "General", icon: Building2 },
  { to: "/administracion/equipo", label: "Equipo y acceso", icon: UsersRound },
  { to: "/administracion/operacion", label: "Operación", icon: Factory },
  { to: "/administracion/ambiental", label: "Gestión ambiental", icon: Leaf },
  { to: "/administracion/calculo", label: "Cálculo e indicadores", icon: BarChart3 },
  { to: "/administracion/reportes", label: "Reportes", icon: FileOutput },
  { to: "/administracion/datos", label: "Datos", icon: Database },
  { to: "/administracion/auditoria", label: "Auditoría", icon: History },
];

export default function SettingsNav() {
  return <nav aria-label="Secciones de configuración" className="overflow-x-auto rounded-[20px] border border-[var(--border-default)] bg-white p-2 lg:sticky lg:top-24">
    <p className="hidden px-3 pb-2 pt-1 text-xs font-black uppercase tracking-[0.14em] text-emerald-700 lg:block">Configuración</p>
    <div className="flex min-w-max gap-1 lg:min-w-0 lg:flex-col">{settingsSections.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-bold transition ${isActive ? "bg-emerald-50 text-emerald-800" : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)]"}`}><Icon aria-hidden="true" size={17} />{label}</NavLink>)}</div>
  </nav>;
}
