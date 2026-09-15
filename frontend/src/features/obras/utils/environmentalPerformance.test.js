import assert from "node:assert/strict";
import test from "node:test";

import {
  buildEnvironmentalBalance,
  buildFlowPerformance,
  buildGeiPerformance,
  buildMaterialsPerformance,
  buildMultiFlowNarrative,
  buildPhysicalFlowPerformances,
  buildTransportPerformance,
  pickRelevantFlows,
} from "./environmentalPerformance.js";

const record = (overrides) => ({
  flujo: "energia",
  periodo_inicio: "2026-08-01",
  periodo_fin: "2026-08-31",
  mediciones: [{ concepto: "consumo_energia", valor: 100, unidad: "kWh" }],
  ...overrides,
});

test("a flow with no records at all reports sin_datos, not zero", () => {
  const result = buildFlowPerformance([], "energia");
  assert.equal(result.state, "sin_datos");
  assert.equal(result.currentValue, null);
  assert.equal(result.hasComparison, false);
});

test("a flow with only one populated month has no comparison, but does have a current value", () => {
  const records = [record({ periodo_inicio: "2026-08-05" })];
  const result = buildFlowPerformance(records, "energia");
  assert.equal(result.state, "con_datos");
  assert.equal(result.currentValue, 100);
  assert.equal(result.hasComparison, false);
  assert.equal(result.variation, null);
});

test("a flow with two populated months computes a real variation", () => {
  const records = [
    record({ periodo_inicio: "2026-07-05", mediciones: [{ concepto: "consumo_energia", valor: 100, unidad: "kWh" }] }),
    record({ periodo_inicio: "2026-08-05", mediciones: [{ concepto: "consumo_energia", valor: 150, unidad: "kWh" }] }),
  ];
  const result = buildFlowPerformance(records, "energia");
  assert.equal(result.hasComparison, true);
  assert.equal(result.currentValue, 150);
  assert.equal(result.previousValue, 100);
  assert.equal(result.variation, 50);
});

test("never mixes incompatible units within one flow — only the dominant unit's months are compared", () => {
  const records = [
    record({ periodo_inicio: "2026-06-05", mediciones: [{ concepto: "consumo_energia", valor: 100, unidad: "kWh" }] }),
    record({ periodo_inicio: "2026-07-05", mediciones: [{ concepto: "consumo_energia", valor: 120, unidad: "kWh" }] }),
    // a single stray record in a different unit must never get summed into the kWh total
    record({ periodo_inicio: "2026-08-05", mediciones: [{ concepto: "consumo_energia", valor: 5, unidad: "MWh" }] }),
  ];
  const result = buildFlowPerformance(records, "energia");
  assert.equal(result.unit, "kWh");
  // the MWh-only month must not appear as "current" since it carries no kWh value
  assert.equal(result.currentValue, 120);
  assert.equal(result.currentLabel, "jul 26");
});

test("buildPhysicalFlowPerformances covers exactly the 7 RegistroFlujoAmbiental domains, never transporte/materiales", () => {
  const results = buildPhysicalFlowPerformances([]);
  const domains = results.map((row) => row.domain);
  assert.deepEqual(domains, ["energia", "agua", "combustibles", "residuos", "ruido", "emisiones-atmosfericas", "suelo"]);
  assert.ok(!domains.includes("transporte"));
  assert.ok(!domains.includes("materiales"));
});

test("buildTransportPerformance derives km/viajes per month from each trip's own date, not a pre-aggregated total", () => {
  const journeys = [
    { fecha_salida: "2026-07-10", metricas: { distancia_km: 40 } },
    { fecha_salida: "2026-07-20", metricas: { distancia_km: 60 } },
    { fecha_salida: "2026-08-05", metricas: { distancia_km: 90 } },
  ];
  const result = buildTransportPerformance(journeys);
  assert.equal(result.unit, "km");
  assert.equal(result.currentValue, 90);
  assert.equal(result.previousValue, 100);
  assert.equal(result.tripsInPeriod, 1);
  assert.equal(result.hasComparison, true);
});

test("buildTransportPerformance with no journeys reports sin_datos, not a fabricated zero", () => {
  const result = buildTransportPerformance([]);
  assert.equal(result.state, "sin_datos");
  assert.equal(result.hasComparison, false);
});

test("buildMaterialsPerformance never sums materials across different units — picks the dominant one only", () => {
  const materials = [
    { nombre: "Hormigón", unidad: "m3", ingresos_periodo: 120 },
    { nombre: "Acero", unidad: "kg", ingresos_periodo: 4500 },
    { nombre: "Áridos", unidad: "m3", ingresos_periodo: 80 },
  ];
  const result = buildMaterialsPerformance(materials);
  assert.equal(result.dominantMaterial, "Acero");
  assert.equal(result.unit, "kg");
  assert.equal(result.currentValue, 4500);
  assert.equal(result.otherMaterialsCount, 2);
});

test("buildMaterialsPerformance never fabricates a period comparison it cannot verify", () => {
  const materials = [{ nombre: "Hormigón", unidad: "m3", ingresos_periodo: 120 }];
  const result = buildMaterialsPerformance(materials);
  assert.equal(result.hasComparison, false);
  assert.equal(result.variation, null);
});

test("buildGeiPerformance never fabricates an intensity without a real denominator", () => {
  const gei = buildGeiPerformance({ kpis: { huella_total_tco2e: 42, alcance_1_tco2e: 10, alcance_2_tco2e: 12, alcance_3_tco2e: 20 } });
  assert.equal(gei.intensity, null);
  assert.ok(gei.intensityUnavailableReason.length > 0);
  assert.equal(gei.hasData, true);
});

test("buildGeiPerformance reports hasData: false with no dashboard kpis, not a fabricated zero total", () => {
  const gei = buildGeiPerformance({});
  assert.equal(gei.hasData, false);
  assert.equal(gei.total, null);
});

test("buildEnvironmentalBalance assembles all flows, GEI excluded (kept as its own dimension)", () => {
  const balance = buildEnvironmentalBalance({ records: [], journeys: [], materials: [] });
  assert.equal(balance.length, 9); // 7 physical + transporte + materiales
  assert.ok(!balance.some((flow) => flow.domain === "gei"));
});

test("pickRelevantFlows prioritizes flows with a real comparison over flows without one", () => {
  const balance = [
    { domain: "agua", label: "Agua", state: "con_datos", hasComparison: false, variation: null },
    { domain: "energia", label: "Energía", state: "con_datos", hasComparison: true, variation: 5 },
  ];
  const [first] = pickRelevantFlows(balance, { max: 1 });
  assert.equal(first.domain, "energia");
});

test("pickRelevantFlows never returns more than max, and skips flows without data", () => {
  const balance = [
    { domain: "agua", label: "Agua", state: "sin_datos", hasComparison: false, variation: null },
    { domain: "energia", label: "Energía", state: "con_datos", hasComparison: true, variation: 30 },
    { domain: "residuos", label: "Residuos", state: "con_datos", hasComparison: true, variation: -10 },
    { domain: "ruido", label: "Ruido", state: "con_datos", hasComparison: true, variation: 5 },
  ];
  const picked = pickRelevantFlows(balance, { max: 2 });
  assert.equal(picked.length, 2);
  assert.ok(picked.every((flow) => flow.state === "con_datos"));
});

test("buildMultiFlowNarrative never defaults to a GEI-first sentence when other flows have more signal", () => {
  const balance = [
    { domain: "materiales", label: "Materiales", state: "con_datos", hasComparison: false, variation: null },
    { domain: "residuos", label: "Residuos", state: "con_datos", hasComparison: true, variation: 12 },
  ];
  const narrative = buildMultiFlowNarrative(balance);
  assert.ok(!narrative.toLowerCase().includes("tco2e"));
  assert.ok(narrative.toLowerCase().includes("residuos") || narrative.toLowerCase().includes("materiales"));
});

test("buildMultiFlowNarrative is honest when there is no physical data at all", () => {
  const narrative = buildMultiFlowNarrative([]);
  assert.match(narrative, /no registra suficiente información/);
});
