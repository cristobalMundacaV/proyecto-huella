import { AlertTriangle, ArrowRight, CalendarDays, Cloud, FileCheck2, Layers3, Leaf, MapPin, ShieldCheck, Zap } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import ChartCard from "@/shared/charts/ChartCard";
import CoverageProgressChart from "@/shared/charts/CoverageProgressChart";
import EnvironmentalDonutChart, { DonutLegend } from "@/shared/charts/EnvironmentalDonutChart";
import { CZMetricCard, CZPageHero, ErrorState } from "@/shared/ui";
import { formatDate, formatNumber } from "@/shared/utils/formatters";
import { environmentalProfileLabel, statusLabel } from "@/features/obras/components/WorkStatus";
import { AiRecommendationsPanel, FlowStatusGrid } from "@/features/obras/components/ObraDashboardPanels";
import { buildExecutiveReading, buildFlowImpactDonutData, buildFlowPhysicalCards, buildReadinessRings, buildRecommendations, buildScopeDonutData, describeEmissionState } from "@/features/obras/utils/obraDashboardSelectors";

// `dashboard`/`dashboardError` are fetched by `ObraWorkspaceLayout` IN
// PARALLEL with the obra workspace itself (not sequentially here) — this
// page never fetches on its own, so there is exactly one loading state for
// the whole obra summary, not two stacked ones.
export default function ObraResumenPage() {
  const { obra, dashboard, dashboardError } = useOutletContext();
  if (dashboardError || !dashboard) return <ErrorState title="No pudimos preparar el resumen ambiental" description="No se muestran valores estimados. Intenta nuevamente cuando el servicio esté disponible." />;
  return <WorkExecutiveDashboard dashboard={dashboard} obra={obra} />;
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
    <CZPageHero>
      <div className="relative grid gap-6 xl:grid-cols-[minmax(0,1fr)_305px] xl:items-center"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-200">Obra · Gestión ambiental</p><h1 className="mt-2 text-3xl font-black leading-tight sm:text-4xl">{obra.nombre || "Obra"}</h1><div className="mt-4 flex flex-wrap gap-2"><HeroPill icon={ShieldCheck}>{statusLabel(obra.estado)}</HeroPill>{obra.fecha_inicio && <HeroPill icon={CalendarDays}>Inicio {formatDate(obra.fecha_inicio)}</HeroPill>}{location && <HeroPill icon={MapPin}>{location}</HeroPill>}{profile && <HeroPill icon={Layers3}>Perfil: {profile}</HeroPill>}</div><p className="mt-4 max-w-3xl text-sm leading-6 text-emerald-50/85">{dashboard.readiness?.listo_para_reporte ? "El período cuenta con las condiciones registradas para avanzar a reporte." : "El período actual todavía requiere antecedentes o validaciones antes del cierre."}</p></div>
        <div className="rounded-[22px] border border-white/20 bg-emerald-950/45 p-4 shadow-xl backdrop-blur-sm"><div className="grid grid-cols-[1fr_auto] items-center gap-3"><div><p className="text-[10px] font-black uppercase tracking-[0.16em] text-emerald-200">Estado ambiental</p><p className="mt-1 text-xl font-black">{dashboard.estado_ejecutivo?.label}</p><p className="mt-2 text-xs leading-5 text-emerald-50/75">{dashboard.readiness?.listo_para_reporte ? "Período listo para reportar." : "El período actual no está listo para cierre."}</p></div><CoverageProgressChart value={readiness} size={74} strokeWidth={9} valueClassName="text-lg text-white" /></div><div className="mt-3 flex justify-end"><a className="inline-flex items-center gap-1 text-xs font-black text-emerald-100" href="#readiness">Ver detalle <ArrowRight size={13} /></a></div></div></div>
    </CZPageHero>
    <section className="flex flex-col gap-4 rounded-[20px] border border-emerald-200 bg-[linear-gradient(100deg,rgba(236,253,245,.96),rgba(240,253,250,.75))] p-4 shadow-[0_8px_24px_rgba(6,78,59,.05)] md:flex-row md:items-center"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><Leaf size={24} /></span><div className="min-w-0 md:border-l md:border-emerald-200 md:pl-4"><h2 className="font-black text-slate-950">Lectura ejecutiva</h2><p className="mt-1 text-sm leading-6 text-slate-600">{reading}</p></div><a className="inline-flex shrink-0 items-center justify-center gap-1 rounded-xl border border-emerald-200 bg-white px-4 py-2 text-xs font-black text-emerald-800 shadow-sm md:ml-auto" href="#insights">Ver recomendaciones <ArrowRight size={13} /></a></section>
    <section className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" aria-label="Indicadores principales"><CZMetricCard icon={Leaf} label="Huella total" value={kpis.huella_total_tco2e} unit="tCO2e" tone="blue" /><CZMetricCard icon={Cloud} label="Estado de emisiones" value={emissionState.label} supportingText={emissionState.helper} tone={emissionState.tone} /><CZMetricCard icon={Leaf} label="Alcance 1" value={kpis.alcance_1_tco2e} unit="tCO2e" supportingText={share(kpis.alcance_1_tco2e, kpis.huella_total_tco2e)} tone="emerald" /><CZMetricCard icon={Zap} label="Alcance 2" value={kpis.alcance_2_tco2e} unit="tCO2e" supportingText={share(kpis.alcance_2_tco2e, kpis.huella_total_tco2e)} tone="amber" /><CZMetricCard icon={Layers3} label="Alcance 3" value={kpis.alcance_3_tco2e} unit="tCO2e" supportingText={share(kpis.alcance_3_tco2e, kpis.huella_total_tco2e)} tone="violet" /></section>
    <section className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4"><CZMetricCard icon={FileCheck2} label="Cobertura de evidencia" value={evidence} unit="%" supportingText={`${dashboard.resumen_ejecutivo?.evidencias_faltantes ?? 0} evidencias faltantes`} tone="rose" progress={evidence} /><CZMetricCard icon={AlertTriangle} label="Riesgo ambiental" value={risk} supportingText={dashboard.risk?.nivel ? `Nivel ${String(dashboard.risk.nivel).replaceAll("_", " ")}` : "Sin evaluación"} tone="orange" /><CZMetricCard icon={AlertTriangle} label="Hallazgos críticos" value={critical} supportingText={critical ? "Requieren atención" : "Sin hallazgos altos"} tone="rose" /><CZMetricCard icon={ShieldCheck} label="Readiness del período" value={readiness} unit="%" supportingText={dashboard.readiness?.listo_para_reporte ? "Listo para reporte" : "Período no listo para cierre"} tone="emerald" progress={readiness} /></section>
    <section className="grid gap-3 xl:grid-cols-[1fr_1fr_.9fr]" id="readiness"><ChartCard title="GEI por alcance" description="Distribución de la huella total entre Alcance 1, 2 y 3." empty={!scopeData.some((row) => Number(row.value) > 0)}><DonutPanel data={scopeData} total={kpis.huella_total_tco2e} /></ChartCard><ChartCard title="Distribución por flujo" description="Impacto (kgCO2e → tCO2e) por flujo ambiental." empty={!flowData.length}><DonutPanel data={flowData} total={kpis.huella_total_tco2e} /></ChartCard><ChartCard title="Readiness del período" description="Cobertura, evidencias, factores y validación profesional."><div className="grid min-h-[300px] content-center gap-2 sm:grid-cols-2 xl:grid-cols-1">{rings.map((ring) => <div className="rounded-xl bg-slate-50 px-3 py-2" key={ring.key}><CoverageProgressChart label={ring.label} value={ring.value} size={54} strokeWidth={7} valueClassName="text-sm text-[var(--text-primary)]" /></div>)}</div></ChartCard></section>
    <section className="rounded-[22px] border border-slate-200 bg-white/90 p-4 shadow-[0_10px_30px_rgba(15,23,42,.05)]"><div className="mb-4"><h2 className="text-xl font-bold text-slate-950">Estado por flujo</h2><p className="mt-1 text-sm font-normal text-slate-500">Consumo físico real registrado en el período, por flujo ambiental.</p></div><FlowStatusGrid flows={flows} /></section>
    <section id="insights"><AiRecommendationsPanel recommendations={recommendations} pendientes={[]} /></section>
  </div>;
}

function HeroPill({ icon: Icon, children }) { return <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold"><Icon size={14} />{children}</span>; }
function DonutPanel({ data, total }) { return <div className="grid min-h-[300px] content-center gap-2 sm:grid-cols-[210px_1fr] sm:items-center"><EnvironmentalDonutChart data={data} height={205} innerRadius={68} outerRadius={96} centerLabel="Total" centerValue={formatNumber(total)} centerUnit="tCO2e" valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /><DonutLegend data={data} valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /></div>; }
function share(value, total) { return Number(total) > 0 && value != null ? `${Math.round((Number(value) / Number(total)) * 100)}% del total` : "Sin participación calculable"; }
