import { ArrowLeft, BarChart3, Building2, ClipboardList, CreditCard, Gauge, HeartPulse, Layers3, Settings2, UsersRound } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const links = [
  ["/saas", "Panel SaaS", Gauge, true], ["/saas/organizaciones", "Organizaciones", Building2],
  ["/saas/organizaciones?vista=planes", "Planes", Layers3], ["/saas/organizaciones?vista=suscripciones", "Suscripciones", UsersRound],
  ["/saas?vista=uso", "Uso", BarChart3], ["/saas?vista=salud", "Salud de clientes", HeartPulse],
  [null, "Facturación", CreditCard], ["/saas/auditoria", "Auditoría SaaS", ClipboardList], [null, "Configuración SaaS", Settings2],
];

export default function SaaSLayout() {
  const { user } = useAuth();
  const { activeOrganizacion } = useOrganizacionActiva();
  return <main className="min-h-screen bg-slate-100 text-slate-950"><div className="grid min-h-screen lg:grid-cols-[260px_1fr]"><aside className="border-r border-emerald-950/15 bg-emerald-950 px-4 py-6 text-white"><div className="px-3"><p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-300">SaaS Carbono Zero</p><h1 className="mt-2 text-xl font-black">Administración global</h1><p className="mt-2 text-xs leading-5 text-emerald-100/70">Plano exclusivo de Mundaca’s Solutions.</p></div><nav className="mt-8 space-y-1">{links.map(([to, label, Icon, end]) => to ? <NavLink key={label} to={to} end={end} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-bold transition ${isActive ? "bg-white text-emerald-950" : "text-emerald-50/80 hover:bg-white/10 hover:text-white"}`}><Icon aria-hidden="true" size={18} />{label}</NavLink> : <div key={label} className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-bold text-emerald-100/35" title="Preparado para una integración futura"><Icon aria-hidden="true" size={18} />{label}</div>)}</nav><div className="mt-8 border-t border-white/10 px-3 pt-5 text-xs text-emerald-100/60"><b className="block text-white">{user?.nombre}</b>Superadministrador de plataforma</div></aside><div className="min-w-0"><header className="sticky top-0 z-30 flex min-h-[72px] items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-5 shadow-sm backdrop-blur sm:px-8"><Link to="/saas" className="flex min-w-0 items-center gap-3"><img src="/brand/carbono-zero-logo.png" alt="Carbono Zero" className="h-10 w-auto" /><span className="hidden border-l border-slate-200 pl-3 text-sm font-black text-slate-700 sm:block">Carbono Zero Global</span></Link><Link to="/seleccionar-organizacion?desde=saas" className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 text-sm font-black text-emerald-900 transition hover:border-emerald-400 hover:bg-emerald-100"><ArrowLeft size={17} /><span className="hidden sm:inline">Volver a empresas</span><span className="sm:hidden">Empresas</span>{activeOrganizacion && <span className="hidden max-w-48 truncate font-medium text-emerald-700 xl:inline">· {activeOrganizacion.nombre}</span>}</Link></header><section className="min-w-0 p-5 sm:p-8 lg:p-10"><Outlet /></section></div></div></main>;
}
