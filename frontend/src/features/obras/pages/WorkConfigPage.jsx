import { ArrowRight, Boxes, CheckCircle2, ClipboardList, Gauge, Settings2, SlidersHorizontal } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";

import { ButtonLink, CZMetricCard, CZSection, SectionHeader, StatusBadge } from "@/shared/ui";

const scopeStatus = (value) => value === "aplica";

export default function WorkConfigPage() {
  const { obraId } = useParams();
  const { obra, context } = useOutletContext();
  const diagnosis = context?.diagnostico_obra;
  const profileCompleted = diagnosis?.estado === "completado";
  const profileKnown = Boolean(diagnosis);
  const applicability = Array.isArray(diagnosis?.aplicabilidad) ? diagnosis.aplicabilidad : null;
  const activeScopes = applicability?.filter((item) => scopeStatus(item.estado_obra)).length;
  const unresolvedScopes = applicability?.filter((item) => ["pendiente", "no_determinado", "sin_datos"].includes(item.estado_obra)).length;
  const profilePath = `/obras/${obraId}/diagnostico`;
  const profileStatus = !profileKnown ? "Sin datos" : profileCompleted ? "Configurado" : "Pendiente";
  const scopeLabel = activeScopes == null ? "Sin datos" : `${activeScopes} activos`;
  const generalStatus = !profileKnown ? "Sin datos" : !profileCompleted ? "Configuración incompleta" : unresolvedScopes > 0 ? "Ámbitos por revisar" : "Perfil preparado";

  const steps = [
    { number: "01", title: "Perfil ambiental", description: "Define contexto, cobertura y aplicabilidad ambiental de esta obra.", path: profilePath, icon: Gauge, badge: profileStatus, badgeTone: profileCompleted ? "success" : "warning", color: profileCompleted ? "border-emerald-200 bg-emerald-50/60 text-emerald-700" : "border-amber-300 bg-amber-50/80 text-amber-800", action: profileCompleted ? "Ver perfil" : "Completar perfil" },
    { number: "02", title: "Ámbitos", description: "Selecciona las dimensiones ambientales aplicables a la operación.", path: "/administracion/ambiental", icon: Boxes, badge: scopeLabel, badgeTone: activeScopes == null ? "neutral" : unresolvedScopes > 0 ? "warning" : "info", color: "border-blue-200 bg-blue-50/60 text-blue-700", action: "Configurar ámbitos", note: "Vista organizacional; los activos corresponden a la aplicabilidad de esta obra." },
    { number: "03", title: "Factores y metodologías", description: "Revisa las referencias y metodologías utilizadas por el cálculo gobernado.", path: "/gobernanza/factores", icon: SlidersHorizontal, badge: "Revisión", badgeTone: "info", color: "border-violet-200 bg-violet-50/60 text-violet-700", action: "Revisar cálculo", note: "Sin estado de configuración por obra." },
    { number: "04", title: "Parámetros", description: "Administra preferencias de cálculo, importación y presentación.", path: "/administracion/calculo", icon: Settings2, badge: "Sin dato por obra", badgeTone: "neutral", color: "border-slate-200 bg-slate-50 text-slate-700", action: "Editar parámetros", note: "Vista organizacional." },
  ];

  return <main className="space-y-5 pb-8">
    <section className="rounded-[var(--radius-hero)] border border-emerald-800/20 bg-[linear-gradient(115deg,#064e3b,#087568)] px-5 py-5 text-white shadow-[var(--shadow-card-v1)] lg:px-7">
      <div className="grid items-center gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(250px,350px)]">
        <div><p className="text-[11px] font-black uppercase tracking-[0.16em] text-emerald-100">Configuración de obra</p><h1 className="mt-1 text-2xl font-black tracking-tight sm:text-[28px]">Configuración de {obra?.nombre || "esta obra"}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50">Define el perfil ambiental, los ámbitos aplicables y los criterios de cálculo que gobiernan esta obra.</p></div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-4"><div className="flex items-center justify-between gap-2"><p className="text-[11px] font-black uppercase tracking-wider text-emerald-100">Estado general</p><span className="rounded-full bg-white/15 px-2.5 py-1 text-xs font-bold">{generalStatus}</span></div><div className="mt-3 grid grid-cols-3 gap-2 border-t border-white/15 pt-3 text-center"><div><p className="text-sm font-black">{profileStatus}</p><p className="text-[11px] text-emerald-100">Perfil</p></div><div><p className="text-sm font-black">{activeScopes ?? "—"}</p><p className="text-[11px] text-emerald-100">Ámbitos activos</p></div><div><p className="text-sm font-black">—</p><p className="text-[11px] text-emerald-100">Factores y métodos</p></div></div><p className="mt-2 text-[10px] text-emerald-100/90">Factores, métodos y parámetros no informan estado por obra.</p></div>
      </div>
    </section>

    <section aria-label="Indicadores de configuración" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <div className="relative"><CZMetricCard icon={Gauge} label="Perfil ambiental" value={profileStatus} supportingText={profileCompleted ? "Contexto ambiental confirmado" : "Primer paso para preparar la obra"} tone={profileCompleted ? "success" : "warning"} className="h-full pb-10" /><Link to={profilePath} className="absolute bottom-3 right-4 inline-flex items-center gap-1 text-xs font-black text-emerald-800">{profileCompleted ? "Ver perfil" : "Completar perfil"} <ArrowRight aria-hidden="true" size={13} /></Link></div>
      <CZMetricCard icon={Boxes} label="Ámbitos activos" value={activeScopes} supportingText={activeScopes == null ? "Aplicabilidad no disponible" : `${unresolvedScopes} por determinar en esta obra`} tone={unresolvedScopes > 0 ? "warning" : "info"} />
      <CZMetricCard icon={SlidersHorizontal} label="Factores y metodologías" value={null} supportingText="Sin estado por obra; revisar cálculo gobernado" tone="info" />
      <CZMetricCard icon={Settings2} label="Parámetros" value={null} supportingText="Preferencias organizacionales; sin estado por obra" tone="neutral" />
    </section>

    <section><SectionHeader title="Ruta de configuración" description="Avanza desde el perfil de la obra hacia las superficies organizacionales de configuración." /><div className="mt-3 grid gap-3 sm:grid-cols-2">{steps.map((step) => <Link key={step.number} to={step.path} className={`group flex min-h-[164px] flex-col rounded-[var(--radius-card)] border p-4 shadow-[var(--shadow-card-v1)] transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)] ${step.color}`}><div className="flex items-start justify-between gap-2"><div className="flex items-center gap-2"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/85 shadow-sm"><step.icon aria-hidden="true" size={20} /></span><span className="text-xs font-black opacity-70">{step.number}</span></div><StatusBadge tone={step.badgeTone}>{step.badge}</StatusBadge></div><h3 className="mt-2 font-black text-slate-950">{step.title}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{step.description}</p>{step.note && <p className="mt-1 text-[11px] leading-4 text-slate-500">{step.note}</p>}<span className="mt-auto flex items-center justify-end gap-1 pt-3 text-xs font-black">{step.action} <ArrowRight aria-hidden="true" size={15} /></span></Link>)}</div></section>

    <CZSection className="!p-4 sm:!p-5"><div className="flex flex-wrap items-center gap-3"><span className={`flex h-10 w-10 items-center justify-center rounded-xl ${profileCompleted && unresolvedScopes === 0 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{profileCompleted && unresolvedScopes === 0 ? <CheckCircle2 aria-hidden="true" size={20} /> : <ClipboardList aria-hidden="true" size={20} />}</span><div className="min-w-0 flex-1"><h2 className="text-lg font-black text-slate-950">{profileCompleted && unresolvedScopes === 0 ? "Perfil y ámbitos preparados" : "Configuración incompleta"}</h2><p className="mt-0.5 text-sm text-slate-600">{profileCompleted && unresolvedScopes === 0 ? "El contexto y la aplicabilidad de la obra están definidos; el estado de parámetros y metodologías no está disponible por obra." : "Completa los elementos pendientes antes de considerar esta obra totalmente preparada."}</p></div>{!profileCompleted && <ButtonLink to={profilePath} size="sm">Completar perfil</ButtonLink>}</div><div className="mt-3 border-t border-slate-100 pt-3 text-sm text-slate-600">{!profileCompleted ? <p>Perfil ambiental pendiente.</p> : unresolvedScopes > 0 ? <p>{unresolvedScopes} ámbito(s) por determinar en la aplicabilidad de esta obra.</p> : <p>No existe detalle por obra para certificar factores, metodologías y parámetros organizacionales.</p>}</div></CZSection>
  </main>;
}
