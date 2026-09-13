import { getEnvironmentalDomain, getFlowChartColor } from "../../../shared/config/environmentalDomains.js";

const SCOPE_COLORS = { 1: "#c2410c", 2: "#a16207", 3: "#0369a1" };

/** Pure display transform of the organization dashboard payload (already
 * aggregated server-side by `build_organization_dashboard`) into the shape
 * the portfolio charts/KPIs need. Never sums or ranks anything itself. */
export function mapPortfolioDashboard(dashboard) {
  const empty = {
    total: null, scopes: [], flows: [], works: [], readinessByWork: [],
    evidence: null, readiness: null, readyPeriods: 0, highRisks: 0,
    hallazgosCriticos: 0, insights: [], topWorks: [],
  };
  if (!dashboard) return empty;

  const kpis = dashboard.kpis || {};
  const scopes = [1, 2, 3]
    .map((scope) => ({ name: `Alcance ${scope}`, value: kpis[`alcance_${scope}_tco2e`], color: SCOPE_COLORS[scope] }))
    .filter((row) => row.value !== null && row.value !== undefined && Number(row.value) > 0);

  const flows = Object.entries(kpis.impacto_por_flujo_tco2e || {})
    .filter(([, value]) => value !== null && value !== undefined && Number(value) > 0)
    .map(([categoria, value]) => ({ name: getEnvironmentalDomain(categoria)?.label || categoria, value, color: getFlowChartColor(categoria) }));

  const works = (dashboard.emisiones_por_obra || []).map((row) => ({ name: row.obra_nombre, value: row.huella_total_tco2e }));
  const readinessByWork = (dashboard.readiness_por_obra || []).map((row) => ({ name: row.obra_nombre, value: row.cobertura_registros_pct }));
  const readyPeriods = (dashboard.readiness_por_obra || []).filter((row) => row.listo_para_reporte).length;
  const highRisks = (dashboard.riesgo_por_obra || []).filter((row) => ["alto", "critico"].includes(row.nivel)).length;

  return {
    total: kpis.huella_total_tco2e ?? null,
    scopes, flows, works, readinessByWork,
    evidence: kpis.cobertura_evidencia_promedio_pct ?? null,
    readiness: kpis.readiness_promedio_pct ?? null,
    readyPeriods, highRisks,
    hallazgosCriticos: kpis.hallazgos_criticos || 0,
    insights: Array.isArray(dashboard.prioridades) ? dashboard.prioridades.slice(0, 3) : [],
    topWorks: Array.isArray(dashboard.top_obras_prioritarias) ? dashboard.top_obras_prioritarias : [],
  };
}
