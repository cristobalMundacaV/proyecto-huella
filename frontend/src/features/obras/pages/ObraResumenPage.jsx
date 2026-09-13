import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, CalendarDays, Cloud, FileCheck2, Layers3, Leaf, MapPin, ShieldCheck, Zap } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import ChartCard from "@/shared/charts/ChartCard";
import CoverageProgressChart from "@/shared/charts/CoverageProgressChart";
import EnvironmentalDonutChart, { DonutLegend } from "@/shared/charts/EnvironmentalDonutChart";
import { ErrorState, LoadingState } from "@/shared/ui";
import { formatDate, formatNumber } from "@/shared/utils/formatters";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { environmentalProfileLabel, statusLabel } from "@/features/obras/components/WorkStatus";
import { getObraDashboard } from "@/features/obras/services/obraDashboardApi";
import { AiRecommendationsPanel, FlowStatusGrid } from "@/features/obras/components/ObraDashboardPanels";
import { buildExecutiveReading, buildFlowImpactDonutData, buildFlowPhysicalCards, buildReadinessRings, buildRecommendations, buildScopeDonutData, describeEmissionState } from "@/features/obras/utils/obraDashboardSelectors";

export default function ObraResumenPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const { obra } = useOutletContext();
  const [state, setState] = useState({ status: "loading", dashboard: null });
  useEffect(() => {
    if (!activeOrganizacionId || !obra?.id) return undefined;
    let active = true;
    getObraDashboard(activeOrganizacionId, obra.id, { relative_months: 3 })
      .then((dashboard) => active && setState({ status: "ready", dashboard }))
      .catch(() => active && setState({ status: "error", dashboard: null }));
    return () => { active = false; };
  }, [activeOrganizacionId, obra?.id]);
  if (state.status === "loading") return <LoadingState label="Calculando la cabina ambiental de la obra" />;
  if (state.status === "error") return <ErrorState title="No pudimos preparar el resumen ambiental" description="No se muestran valores estimados. Intenta nuevamente cuando el servicio esté disponible." />;
  return <WorkExecutiveDashboard dashboard={state.dashboard} obra={obra} />;
}

export function WorkExecutiveDashboard({ dashboard, obra }) {
  const kpis = dashboard.kpis || {};
  const scopeData = buildScopeDonutData(kpis);
  const flowData = buildFlowImpactDonutData(kpis);
  const rings = buildReadinessRings(dashboard.readiness);
  const flows = buildFlowPhysicalCards(kpis, obra.id);
  const recommendations = buildRecommendations(dashboard);
  const reading = buildExecutiveReading(dashboard);
  const emissionState = describeEmissionState(dashboard);
  const location = obra.ubicacion || [obra.comuna, obra.region].filter(Boolean).join(", ");
  const profile = environmentalProfileLabel(obra.perfil_ambiental, obra.tipo_proyecto);
  const readiness = dashboard.readiness?.cobertura_registros_pct;
  const evidence = kpis.cobertura_evidencia_pct;
  const critical = dashboard.resumen_ejecutivo?.hallazgos_altos;
  const risk = dashboard.risk?.risk_score;
  return <div className="space-y-3 pb-4">
    <section className="relative overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[radial-gradient(circle_at_72%_25%,rgba(110,231,183,0.20),transparent_30%),linear-gradient(118deg,#064e3b_0%,#066657_54%,#0f766e_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.18)] lg:p-7">
      <div className="relative grid gap-6 xl:grid-cols-[minmax(0,1fr)_305px] xl:items-center"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-200">Obra · Gestión ambiental</p><h1 className="mt-2 text-3xl font-black leading-tight sm:text-4xl">{obra.nombre || "Obra"}</h1><div className="mt-4 flex flex-wrap gap-2"><HeroPill icon={ShieldCheck}>{statusLabel(obra.estado)}</HeroPill>{obra.fecha_inicio && <HeroPill icon={CalendarDays}>Inicio {formatDate(obra.fecha_inicio)}</HeroPill>}{location && <HeroPill icon={MapPin}>{location}</HeroPill>}{profile && <HeroPill icon={Layers3}>Perfil: {profile}</HeroPill>}</div><p className="mt-4 max-w-3xl text-sm leading-6 text-emerald-50/85">{dashboard.readiness?.listo_para_reporte ? "El período cuenta con las condiciones registradas para avanzar a reporte." : "El período actual todavía requiere antecedentes o validaciones antes del cierre."}</p></div>
        <div className="rounded-[22px] border border-white/20 bg-emerald-950/45 p-4 shadow-xl backdrop-blur-sm"><div className="grid grid-cols-[1fr_auto] items-center gap-3"><div><p className="text-[10px] font-black uppercase tracking-[0.16em] text-emerald-200">Estado ambiental</p><p className="mt-1 text-xl font-black">{dashboard.estado_ejecutivo?.label}</p><p className="mt-2 text-xs leading-5 text-emerald-50/75">{dashboard.readiness?.listo_para_reporte ? "Período listo para reportar." : "El período actual no está listo para cierre."}</p></div><CoverageProgressChart value={readiness} size={74} strokeWidth={9} /></div><a className="mt-3 inline-flex items-center gap-1 text-xs font-black text-emerald-100" href="#readiness">Ver detalle <ArrowRight size={13} /></a></div></div>
    </section>
    <section className="flex flex-col gap-4 rounded-[20px] border border-emerald-200 bg-[linear-gradient(100deg,rgba(236,253,245,.96),rgba(240,253,250,.75))] p-4 shadow-[0_8px_24px_rgba(6,78,59,.05)] md:flex-row md:items-center"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><Leaf size={24} /></span><div className="min-w-0 md:border-l md:border-emerald-200 md:pl-4"><h2 className="font-black text-slate-950">Lectura ejecutiva</h2><p className="mt-1 text-sm leading-6 text-slate-600">{reading}</p></div><a className="inline-flex shrink-0 items-center justify-center gap-1 rounded-xl border border-emerald-200 bg-white px-4 py-2 text-xs font-black text-emerald-800 shadow-sm md:ml-auto" href="#insights">Ver recomendaciones <ArrowRight size={13} /></a></section>
    <section className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" aria-label="Indicadores principales"><ExecutiveKpi icon={Leaf} label="Huella total" value={kpis.huella_total_tco2e} unit="tCO2e" tone="blue" /><ExecutiveKpi icon={Cloud} label="Estado de emisiones" value={emissionState.label} helper={emissionState.helper} tone={emissionState.tone} /><ExecutiveKpi icon={Leaf} label="Alcance 1" value={kpis.alcance_1_tco2e} unit="tCO2e" helper={share(kpis.alcance_1_tco2e, kpis.huella_total_tco2e)} tone="emerald" /><ExecutiveKpi icon={Zap} label="Alcance 2" value={kpis.alcance_2_tco2e} unit="tCO2e" helper={share(kpis.alcance_2_tco2e, kpis.huella_total_tco2e)} tone="amber" /><ExecutiveKpi icon={Layers3} label="Alcance 3" value={kpis.alcance_3_tco2e} unit="tCO2e" helper={share(kpis.alcance_3_tco2e, kpis.huella_total_tco2e)} tone="violet" /></section>
    <section className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4"><ExecutiveKpi icon={FileCheck2} label="Cobertura de evidencia" value={evidence} unit="%" helper={`${dashboard.resumen_ejecutivo?.evidencias_faltantes ?? 0} evidencias faltantes`} tone="rose" progress={evidence} /><ExecutiveKpi icon={AlertTriangle} label="Riesgo ambiental" value={risk} helper={dashboard.risk?.nivel ? `Nivel ${String(dashboard.risk.nivel).replaceAll("_", " ")}` : "Sin evaluación"} tone="orange" /><ExecutiveKpi icon={AlertTriangle} label="Hallazgos críticos" value={critical} helper={critical ? "Requieren atención" : "Sin hallazgos altos"} tone="rose" /><ExecutiveKpi icon={ShieldCheck} label="Readiness del período" value={readiness} unit="%" helper={dashboard.readiness?.listo_para_reporte ? "Listo para reporte" : "Período no listo para cierre"} tone="emerald" progress={readiness} /></section>
    <section className="grid gap-3 xl:grid-cols-[1fr_1fr_.9fr]" id="readiness"><ChartCard title="GEI por alcance" description="Distribución de la huella total entre Alcance 1, 2 y 3." empty={!scopeData.some((row) => Number(row.value) > 0)}><DonutPanel data={scopeData} total={kpis.huella_total_tco2e} /></ChartCard><ChartCard title="Distribución por flujo" description="Impacto (kgCO2e → tCO2e) por flujo ambiental." empty={!flowData.length}><DonutPanel data={flowData} total={kpis.huella_total_tco2e} /></ChartCard><ChartCard title="Readiness del período" description="Cobertura, evidencias, factores y validación profesional."><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">{rings.map((ring) => <div className="rounded-xl bg-slate-50 px-3 py-2" key={ring.key}><CoverageProgressChart label={ring.label} value={ring.value} size={54} strokeWidth={7} /></div>)}</div></ChartCard></section>
    <section className="rounded-[22px] border border-slate-200 bg-white/90 p-4 shadow-[0_10px_30px_rgba(15,23,42,.05)]"><div className="mb-3 flex flex-wrap items-baseline gap-2"><h2 className="text-lg font-black text-slate-950">Estado por flujo</h2><p className="text-xs text-slate-500">Consumo físico real registrado en el período, por flujo ambiental.</p></div><FlowStatusGrid flows={flows} /></section>
    <section id="insights"><AiRecommendationsPanel recommendations={recommendations} pendientes={[]} /></section>
  </div>;
}

function HeroPill({ icon: Icon, children }) { return <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold"><Icon size={14} />{children}</span>; }
function DonutPanel({ data, total }) { return <div className="grid gap-2 sm:grid-cols-[210px_1fr] sm:items-center"><EnvironmentalDonutChart data={data} height={205} innerRadius={68} outerRadius={96} centerLabel="Total" centerValue={formatNumber(total)} centerUnit="tCO2e" valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /><DonutLegend data={data} valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /></div>; }
function share(value, total) { return Number(total) > 0 && value != null ? `${Math.round((Number(value) / Number(total)) * 100)}% del total` : "Sin participación calculable"; }
function ExecutiveKpi({ icon: Icon, label, value, unit, helper, tone, progress }) { const tones = { blue: "border-blue-200 bg-blue-50/65 text-blue-700", rose: "border-rose-200 bg-rose-50/65 text-rose-700", emerald: "border-emerald-200 bg-emerald-50/65 text-emerald-700", amber: "border-amber-200 bg-amber-50/65 text-amber-700", violet: "border-violet-200 bg-violet-50/65 text-violet-700", orange: "border-orange-200 bg-orange-50/65 text-orange-700", neutral: "border-slate-200 bg-slate-50 text-slate-700" }; const missing = value === null || value === undefined || value === ""; return <article className={`rounded-[18px] border p-3.5 shadow-[0_7px_20px_rgba(15,23,42,.045)] ${tones[tone] || tones.neutral}`}><div className="flex items-start gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/80 shadow-sm"><Icon size={20} /></span><div className="min-w-0"><p className="text-xs font-black text-slate-600">{label}</p><p className="mt-1 text-[21px] font-black leading-tight text-slate-950">{missing ? "Sin datos" : typeof value === "number" ? formatNumber(value) : value}{!missing && unit && <span className="ml-1 text-xs font-bold text-slate-500">{unit}</span>}</p>{progress != null && <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-current" style={{ width: `${Math.min(100, Math.max(0, Number(progress)))}%` }} /></div>}<p className="mt-1.5 text-[11px] leading-4 text-slate-500">{helper || "Dato del período actual"}</p></div></div></article>; }
