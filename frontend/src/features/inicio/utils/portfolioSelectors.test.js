import assert from "node:assert/strict";
import test from "node:test";

import { mapPortfolioDashboard } from "./portfolioSelectors.js";

test("returns an empty, non-throwing shape when the portfolio dashboard is unavailable", () => {
  const mapped = mapPortfolioDashboard(null);
  assert.equal(mapped.total, null);
  assert.deepEqual(mapped.scopes, []);
  assert.deepEqual(mapped.works, []);
  assert.equal(mapped.readyPeriods, 0);
  assert.equal(mapped.highRisks, 0);
  assert.deepEqual(mapped.insights, []);
});

test("maps kpis, per-obra rows and never exceeds 3 insights even if the backend sent more", () => {
  const dashboard = {
    kpis: {
      huella_total_tco2e: 120.5, alcance_1_tco2e: 40, alcance_2_tco2e: 30, alcance_3_tco2e: 50.5,
      impacto_por_flujo_tco2e: { materiales: 80, agua: 10 },
      readiness_promedio_pct: 62.3, cobertura_evidencia_promedio_pct: 71.1, hallazgos_criticos: 4,
    },
    emisiones_por_obra: [{ obra_id: 1, obra_nombre: "Obra A", huella_total_tco2e: 120.5 }],
    readiness_por_obra: [
      { obra_id: 1, obra_nombre: "Obra A", listo_para_reporte: true, cobertura_registros_pct: 92 },
      { obra_id: 2, obra_nombre: "Obra B", listo_para_reporte: false, cobertura_registros_pct: 40 },
    ],
    riesgo_por_obra: [
      { obra_id: 1, obra_nombre: "Obra A", risk_score: 10, nivel: "bajo" },
      { obra_id: 2, obra_nombre: "Obra B", risk_score: 80, nivel: "critico" },
    ],
    top_obras_prioritarias: [{ obra_id: 2, obra_nombre: "Obra B" }],
    prioridades: [
      { code: "A", priority: "alta", title: "1" }, { code: "B", priority: "media", title: "2" },
      { code: "C", priority: "baja", title: "3" }, { code: "D", priority: "baja", title: "4" },
    ],
  };

  const mapped = mapPortfolioDashboard(dashboard);
  assert.equal(mapped.total, 120.5);
  assert.equal(mapped.scopes.length, 3);
  assert.equal(mapped.flows.length, 2);
  assert.equal(mapped.readyPeriods, 1);
  assert.equal(mapped.highRisks, 1);
  assert.equal(mapped.hallazgosCriticos, 4);
  assert.equal(mapped.insights.length, 3, "must truncate to at most 3 insights even if the backend ever sent more");
  assert.equal(mapped.topWorks.length, 1);
});

test("a scope with a zero value is dropped from the donut data, not shown as a fake zero slice", () => {
  const mapped = mapPortfolioDashboard({
    kpis: { alcance_1_tco2e: 0, alcance_2_tco2e: 12, alcance_3_tco2e: null, impacto_por_flujo_tco2e: {} },
    emisiones_por_obra: [], readiness_por_obra: [], riesgo_por_obra: [], top_obras_prioritarias: [], prioridades: [],
  });
  assert.deepEqual(mapped.scopes.map((row) => row.name), ["Alcance 2 · Energía adquirida"]);
});
