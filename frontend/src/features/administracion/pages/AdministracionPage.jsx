import { ArrowRight, BarChart3, Building2, Database, Factory, FileOutput, GitBranch, History, Leaf, Settings2, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import SettingsNav from "../components/SettingsNav";
import { usePermissions } from "@/features/auth/hooks/usePermissions";

const baseRows = [
  { to: "/administracion/organizacion", icon: Building2, title: "General", description: "Identidad, contacto y perfil operacional de la organización activa." },
  { to: "/administracion/equipo", icon: UsersRound, title: "Equipo y acceso", description: "Usuarios, roles y estado de acceso dentro del tenant." },
  { to: "/administracion/operacion", icon: Factory, title: "Operación", description: "Obras, etapas, activos, sensores y estructura operacional." },
  { to: "/administracion/estructura-operacional", icon: GitBranch, title: "Áreas y flujos ambientales", description: "Edita las áreas activas y dónde se origina o administra cada flujo de información." },
  { to: "/administracion/ambiental", icon: Leaf, title: "Gestión ambiental", description: "Perfil ambiental y aplicabilidad de las capacidades por obra." },
  { to: "/administracion/calculo", icon: BarChart3, title: "Cálculo e indicadores", description: "Metodologías gobernadas, factores, indicadores y unidades de presentación." },
  { to: "/administracion/reportes", icon: FileOutput, title: "Reportes", description: "Preferencias reales de agrupación, periodo y presentación." },
  { to: "/administracion/datos", icon: Database, title: "Datos", description: "Preferencias de captura y acceso al Centro de Importaciones." },
  { to: "/administracion/auditoria", icon: History, title: "Auditoría", description: "Historial disponible de acciones y trazabilidad gobernada." },
];

const sectionPermission = { organizacion: "organization.view", equipo: "team.view", operacion: "works.view", "estructura-operacional": "settings.manage", ambiental: "environmental_profile.view", calculo: "indicators.view", reportes: "reports.view", datos: "operational_data.view", auditoria: "audit.view" };

export default function AdministracionPage() {
  const { activeOrganizacion } = useOrganizacionActiva();
  const { can } = usePermissions();
  const rows = baseRows.filter(({ to }) => can(sectionPermission[to.split("/").pop()]));
  return <main className="space-y-6">
    <header className="flex flex-wrap items-start gap-4 border-b border-[var(--border-default)] pb-5"><span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700"><Settings2 aria-hidden="true" size={23} /></span><div><p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">Configuración</p><h1 className="mt-1 text-3xl font-black">Configuración de la organización</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">Administra cómo opera, registra, calcula y presenta su gestión ambiental esta organización.</p><p className="mt-2 text-sm font-bold text-emerald-800">{activeOrganizacion?.nombre}</p></div></header>
    <div className="grid items-start gap-5 lg:grid-cols-[230px_minmax(0,1fr)]"><SettingsNav /><section className="overflow-hidden rounded-[22px] border border-[var(--border-default)] bg-white"><div className="border-b border-[var(--border-default)] p-5"><h2 className="text-xl font-black">Centro de configuración</h2><p className="mt-1 text-sm text-[var(--text-muted)]">Cada área administra únicamente recursos del tenant activo.</p></div><div className="divide-y divide-[var(--border-default)]">{rows.map(({ to, icon: Icon, title, description }) => <Link key={to} to={to} className="group flex items-center gap-4 p-4 transition hover:bg-emerald-50/40 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><Icon aria-hidden="true" size={19} /></span><span className="min-w-0 flex-1"><b className="block">{title}</b><span className="mt-0.5 block text-sm text-[var(--text-muted)]">{description}</span></span><ArrowRight aria-hidden="true" className="shrink-0 text-emerald-700 transition group-hover:translate-x-0.5" size={17} /></Link>)}</div></section></div>
  </main>;
}
