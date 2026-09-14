import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExecutiveReading,
  buildFlowImpactDonutData,
  buildFlowPhysicalCards,
  buildReadinessRings,
  buildScopeDonutData,
  buildRecommendations,
} from "./obraDashboardSelectors.js";

test("dashboard chart selectors preserve backend values", () => {
  const kpis = {
    huella_total_tco2e: 6,
    alcance_1_tco2e: 1,
    alcance_2_tco2e: 2,
    alcance_3_tco2e: 3,
    impacto_por_flujo_tco2e: { energia: 2, agua: 0, residuos: 4 },
  };

  assert.deepEqual(buildScopeDonutData(kpis).map(({ value }) => value), [1, 2, 3]);
  assert.deepEqual(buildFlowImpactDonutData(kpis).map(({ value }) => value), [2, 4]);
});

test("executive dashboard limits insights to three and handles missing data", () => {
  const findings = Array.from({ length: 7 }, (_, index) => ({
    code: `F-${index}`, severity: "high", title: `Hallazgo ${index}`,
    description: "Detalle trazable", recommendations: [],
  }));
  const dashboard = {
    obra_id: 9,
    kpis: { huella_total_tco2e: 0, cobertura_evidencia_pct: null },
    readiness: { listo_para_reporte: false },
    resumen_ejecutivo: { hallazgos_altos: 0 },
    top_findings: findings,
  };
  assert.equal(buildRecommendations(dashboard).length, 3);
  assert.match(buildExecutiveReading(dashboard), /no registra emisiones calculadas/i);
  assert.match(buildExecutiveReading(dashboard), /aún no está disponible/i);
});

test("readiness and physical flows expose missing values without inventing data", () => {
  const rings = buildReadinessRings({
    cobertura_registros_pct: 80,
    evidencia_pct: 70,
    factores_pct: 60,
    validacion_profesional_pct: 50,
  });
  assert.deepEqual(rings.map(({ value }) => value), [80, 70, 60, 50]);

  const flows = buildFlowPhysicalCards({ energia: { kWh: { total: 25 } } }, 9);
  assert.equal(flows.find(({ key }) => key === "energia").value, 25);
  assert.equal(flows.find(({ key }) => key === "agua").value, null);
  assert.equal(flows.find(({ key }) => key === "energia").href, "/obras/9/operacion/energia");
});

test("consumption insights separate the human message from before and after values", () => {
  const [insight] = buildRecommendations({
    obra_id: 73,
    top_findings: [{
      code: "CONSUMPTION_INCREASE",
      severity: "critical",
      metric: "energia",
      title: "Aumento relevante de energía",
      description: "El consumo de energía aumentó 200.0% respecto del período anterior (3200.00 -> 9600.00 kWh).",
      evidence: { previous_value: 3200, current_value: 9600, unit: "kWh" },
      recommendations: ["Revisar el detalle operacional del período para confirmar la causa del aumento."],
    }],
  });
  assert.equal(insight.description, "El consumo de energía aumentó 200.0% respecto del período anterior.");
  assert.deepEqual(insight.comparison, { before: 3200, after: 9600, unit: "kWh" });
  assert.equal(insight.href, "/obras/73/operacion/energia");
});
