import test from "node:test";
import assert from "node:assert/strict";

import { compatibleDomainTotals, domainActivities, domainRecords } from "./operationSelectors.js";

test("Combustibles conserva registros genericos, moviles y estacionarios", () => {
  const records = [
    { flujo: "combustible", actividad_detalle: { id: 1, tipo: "consumo_combustible" } },
    { flujo: "combustible_movil", actividad_detalle: { id: 2, tipo: "consumo_combustible" } },
    { flujo: "combustible_estacionario", actividad_detalle: { id: 3, tipo: "consumo_combustible_estacionario" } },
    { flujo: "agua", actividad_detalle: { id: 4, tipo: "consumo_agua" } },
  ];

  assert.deepEqual(domainRecords(records, "combustibles").map((item) => item.flujo), [
    "combustible", "combustible_movil", "combustible_estacionario",
  ]);
  assert.deepEqual(domainActivities(records, "combustibles").map((item) => item.id), [1, 2, 3]);
});

test("el KPI usa totales compatibles del backend y mantiene unidades separadas", () => {
  const indicators = {
    flujos: [
      { flujo: "combustible_movil", concepto: "combustible_consumido" },
      { flujo: "combustible_estacionario", concepto: "combustible_consumido" },
    ],
    totales_compatibles: [
      { concepto: "combustible_consumido", unidad: "L", total: 300 },
      { concepto: "combustible_consumido", unidad: "kg", total: 25 },
      { concepto: "consumo_agua", unidad: "m3", total: 10 },
    ],
  };

  assert.deepEqual(compatibleDomainTotals(indicators, "combustibles"), [
    { concepto: "combustible_consumido", unidad: "L", total: 300 },
    { concepto: "combustible_consumido", unidad: "kg", total: 25 },
  ]);
});
