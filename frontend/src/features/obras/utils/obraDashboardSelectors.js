import { getEnvironmentalDomain, getFlowChartColor } from "../../../shared/config/environmentalDomains.js";

const SCOPE_LABELS = {
  1: "Alcance 1 · Combustión directa",
  2: "Alcance 2 · Energía comprada",
  3: "Alcance 3 · Otras fuentes",
};

const SCOPE_COLORS = { 1: "#059669", 2: "#f59e0b", 3: "#1976d2" };

const FLOW_ROUTE = {
  energia: "energia",
  combustible: "combustibles",
  agua: "agua",
  residuos: "residuos",
  materiales: "materiales",
};

/** Pure display transform: never computes a number, only shapes already
 * backend-computed `kpis.alcance_*_tco2e` for the donut chart. */
export function buildScopeDonutData(kpis) {
  if (!kpis) return [];
  return [1, 2, 3]
    .map((scope) => ({
      name: SCOPE_LABELS[scope],
      value: kpis[`alcance_${scope}_tco2e`],
      color: SCOPE_COLORS[scope],
    }))
    .filter((row) => row.value !== null && row.value !== undefined);
}

/** Pure display transform of `kpis.impacto_por_flujo_tco2e` (already
 * computed backend-side from the same ledger as the scope split). */
export function buildFlowImpactDonutData(kpis) {
  const impact = kpis?.impacto_por_flujo_tco2e || {};
  return Object.entries(impact)
    .filter(([, value]) => value !== null && value !== undefined && Number(value) > 0)
    .map(([categoria, value]) => {
      const domain = getEnvironmentalDomain(categoria);
      return {
        name: domain?.label || categoria,
        value,
        color: getFlowChartColor(categoria),
      };
    });
}

const READINESS_RINGS = [
  { key: "cobertura_registros_pct", label: "Cobertura de registros" },
  { key: "evidencia_pct", label: "Evidencia documental" },
  { key: "factores_pct", label: "Factores asignados" },
  { key: "validacion_profesional_pct", label: "Validación profesional" },
];

export function buildReadinessRings(readiness) {
  if (!readiness) return [];
  return READINESS_RINGS.map((ring) => ({ ...ring, value: readiness[ring.key] }));
}

/** Physical (non-monetary, non-CO2e) per-flow values, one row per flow the
 * backend already aggregated in `kpis[<flujo>]` — first unit key only, since
 * `operational_aggregate` returns one dominant unit per flow when the data
 * is consistent. Never invents a coverage/evidence figure per flow: that
 * granularity is not computed backend-side yet, so it is deliberately left
 * out rather than fabricated (see product report "pendientes"). */
export function buildFlowPhysicalCards(kpis, obraId) {
  if (!kpis) return [];
  return ["energia", "agua", "combustible", "residuos", "materiales"]
    .map((flujo) => {
      const domain = getEnvironmentalDomain(flujo);
      const byUnit = kpis[flujo] || {};
      const [unit, agg] = Object.entries(byUnit)[0] || [];
      const route = FLOW_ROUTE[flujo];
      return {
        key: flujo,
        label: domain?.label || flujo,
        icon: domain?.icon,
        text: domain?.text,
        softBg: domain?.softBg,
        border: domain?.border,
        value: agg?.total ?? null,
        unit,
        href: route ? `/obras/${obraId}/operacion/${route}` : `/obras/${obraId}/operacion`,
      };
    });
}

const SEVERITY_TONE = { critical: "danger", high: "danger", medium: "warning", low: "info", info: "info" };
const SEVERITY_LABEL = { critical: "Crítica", high: "Alta", medium: "Media", low: "Baja", info: "Informativa" };

const METRIC_ROUTE = {
  energia: "energia", combustible: "combustibles", agua: "agua",
  residuos: "residuos", materiales: "materiales", ruido: "ruido",
};

/** Pure display transform of `dashboard.top_findings` (already-serialized
 * `DiagnosticFinding` dicts from AI-INTELLIGENCE-03) into recommendation
 * cards. Adds no new claim: title/description/reason/recommendations all
 * come verbatim from the backend finding. */
export function buildRecommendations(dashboard) {
  const findings = Array.isArray(dashboard?.top_findings) ? dashboard.top_findings : [];
  const obraId = dashboard?.obra_id;
  return findings.slice(0, 3).map((finding) => ({
    key: `${finding.code}-${finding.entity_id ?? "obra"}-${finding.metric ?? ""}`,
    tone: SEVERITY_TONE[finding.severity] || "neutral",
    priorityLabel: SEVERITY_LABEL[finding.severity] || finding.severity,
    title: finding.title,
    description: String(finding.description || "").replace(/\s*\([^)]*\)(?=\.)/, ""),
    reason: finding.reason,
    recommendations: Array.isArray(finding.recommendations) ? finding.recommendations : [],
    comparison: buildFindingComparison(finding),
    href: METRIC_ROUTE[finding.metric] ? `/obras/${obraId}/operacion/${METRIC_ROUTE[finding.metric]}` : `/obras/${obraId}/problemas`,
  }));
}

function buildFindingComparison(finding) {
  const evidence = finding?.evidence || {};
  if (!["CONSUMPTION_INCREASE", "CONSUMPTION_DECREASE"].includes(finding?.code)) return null;
  if (evidence.previous_value === null || evidence.previous_value === undefined || evidence.current_value === null || evidence.current_value === undefined) return null;
  return { before: evidence.previous_value, after: evidence.current_value, unit: evidence.unit || "" };
}

export function describeEmissionState(dashboard) {
  const code = dashboard?.estado_ejecutivo?.codigo;
  const level = dashboard?.risk?.nivel;
  if (code === "critica" || level === "critico") return { label: "Emisiones críticas", helper: "Prioridad ambiental inmediata", tone: "rose" };
  if (code === "atencion" || level === "alto") return { label: "Emisiones altas", helper: "Requieren atención y seguimiento", tone: "rose" };
  if (level === "medio") return { label: "Emisiones en atención", helper: "Seguimiento recomendado", tone: "amber" };
  if (code === "estable" || code === "lista_para_reporte") return { label: "Emisiones estables", helper: "Sin señal crítica en el período", tone: "emerald" };
  return { label: "Estado en evaluación", helper: "Período todavía incompleto", tone: "neutral" };
}

export function buildExecutiveReading(dashboard) {
  const kpis = dashboard?.kpis || {};
  const total = Number(kpis.huella_total_tco2e || 0);
  const flows = buildFlowImpactDonutData(kpis).toSorted((a, b) => Number(b.value) - Number(a.value));
  const scopes = buildScopeDonutData(kpis).toSorted((a, b) => Number(b.value) - Number(a.value));
  const dominantFlow = flows[0];
  const dominantScope = scopes[0];
  const flowShare = total > 0 && dominantFlow ? Math.round((Number(dominantFlow.value) / total) * 100) : null;
  const scopeShare = total > 0 && dominantScope ? Math.round((Number(dominantScope.value) / total) * 100) : null;
  const evidence = kpis.cobertura_evidencia_pct;
  const findings = dashboard?.resumen_ejecutivo?.hallazgos_altos ?? 0;
  const parts = [];
  if (total > 0) parts.push(`La huella alcanza ${total.toLocaleString("es-CL")} tCO2e${dominantFlow ? ` y se concentra en ${dominantFlow.name}${flowShare !== null ? ` (${flowShare}%)` : ""}` : ""}${dominantScope ? ` y ${dominantScope.name.split(" · ")[0]}${scopeShare !== null ? ` (${scopeShare}%)` : ""}` : ""}.`);
  else parts.push("La huella del período no registra emisiones calculadas con la información disponible.");
  parts.push(evidence === null || evidence === undefined ? "La cobertura de evidencia aún no está disponible." : `La cobertura de evidencia es ${evidence}%${Number(evidence) < 80 ? ", por debajo del nivel esperado para el cierre" : ""}.`);
  parts.push(dashboard?.readiness?.listo_para_reporte ? "El período está listo para reporte." : "El período aún no está listo para cierre.");
  parts.push(findings ? `Se identifican ${findings} hallazgo${findings === 1 ? "" : "s"} de alta severidad que requieren atención.` : "No se identifican hallazgos de alta severidad en el período.");
  return parts.join(" ");
}
