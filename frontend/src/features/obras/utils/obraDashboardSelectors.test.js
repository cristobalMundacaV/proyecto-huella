import assert from "node:assert/strict";
import test from "node:test";

import {
  buildFlowImpactDonutData,
  buildFlowPhysicalCards,
  buildReadinessRings,
  buildScopeDonutData,
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
