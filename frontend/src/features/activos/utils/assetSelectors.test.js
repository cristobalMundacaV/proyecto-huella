import assert from "node:assert/strict";
import test from "node:test";

import { buildAssetsSummary, fleetBucket, maintenanceAvailability, upcomingMaintenances } from "./assetSelectors.js";

const TODAY = new Date("2026-09-14T00:00:00Z");

test("fleetBucket classifies fuera_servicio and retirado as fuera de servicio", () => {
  assert.equal(fleetBucket({ estado: "fuera_servicio", mantenimientos: [] }), "fuera_servicio");
  assert.equal(fleetBucket({ estado: "retirado", mantenimientos: [] }), "fuera_servicio");
});

test("fleetBucket classifies an active maintenance as en_mantencion, ahead of any other signal", () => {
  const asset = { estado: "operativo", mantenimientos: [{ estado: "en_proceso" }] };
  assert.equal(fleetBucket(asset), "en_mantencion");
});

test("fleetBucket classifies requiere_revision and any open (non in-progress) maintenance as mantencion_proxima", () => {
  assert.equal(fleetBucket({ estado: "requiere_revision", mantenimientos: [] }), "mantencion_proxima");
  assert.equal(fleetBucket({ estado: "operativo", mantenimientos: [{ estado: "programado" }] }), "mantencion_proxima");
  assert.equal(fleetBucket({ estado: "operativo", mantenimientos: [{ estado: "vencido" }] }), "mantencion_proxima");
});

test("fleetBucket defaults to operativo when nothing else applies", () => {
  assert.equal(fleetBucket({ estado: "operativo", mantenimientos: [{ estado: "realizado" }] }), "operativo");
  assert.equal(fleetBucket({ estado: "operativo" }), "operativo");
});

test("maintenanceAvailability flags a still-programado record whose date already passed as vencida, not proxima", () => {
  const asset = { mantenimientos: [{ estado: "programado", fecha_programada: "2026-01-01" }] };
  assert.equal(maintenanceAvailability(asset, { today: TODAY }), "vencida");
});

test("maintenanceAvailability reads proxima for a future programado record", () => {
  const asset = { mantenimientos: [{ estado: "programado", fecha_programada: "2026-12-01" }] };
  assert.equal(maintenanceAvailability(asset, { today: TODAY }), "proxima");
});

test("maintenanceAvailability reads al_dia when every record is closed", () => {
  const asset = { mantenimientos: [{ estado: "realizado", fecha_programada: "2026-01-01" }] };
  assert.equal(maintenanceAvailability(asset, { today: TODAY }), "al_dia");
});

test("upcomingMaintenances sorts vencida before proxima, then by date", () => {
  const assets = [
    { id: 1, nombre: "Camión 1", mantenimientos: [{ id: "a", estado: "programado", fecha_programada: "2027-01-01" }] },
    { id: 2, nombre: "Camión 2", mantenimientos: [{ id: "b", estado: "programado", fecha_programada: "2026-01-01" }] },
    { id: 3, nombre: "Camión 3", mantenimientos: [{ id: "c", estado: "vencido", fecha_programada: "2025-01-01" }] },
    { id: 4, nombre: "Camión 4", mantenimientos: [{ id: "d", estado: "realizado", fecha_programada: "2020-01-01" }] },
  ];
  const rows = upcomingMaintenances(assets, { today: TODAY });
  assert.deepEqual(rows.map((row) => row.id), ["c", "b", "a"]);
  assert.equal(rows[0].priority, "vencida");
  assert.equal(rows[1].priority, "vencida");
  assert.equal(rows[2].priority, "proxima");
});

test("upcomingMaintenances respects a limit", () => {
  const assets = [{ id: 1, nombre: "A", mantenimientos: [{ id: "a", estado: "programado", fecha_programada: "2027-01-01" }, { id: "b", estado: "programado", fecha_programada: "2027-02-01" }] }];
  assert.equal(upcomingMaintenances(assets, { today: TODAY, limit: 1 }).length, 1);
});

test("buildAssetsSummary counts totals, fleet buckets and byType from real fields only", () => {
  const assets = [
    { id: 1, tipo: "vehiculo", estado: "operativo", sensores_count: 2, mantenimientos: [] },
    { id: 2, tipo: "vehiculo", estado: "requiere_revision", sensores_count: 0, mantenimientos: [] },
    { id: 3, tipo: "maquinaria", estado: "fuera_servicio", sensores_count: 0, mantenimientos: [] },
  ];
  const summary = buildAssetsSummary(assets, { today: TODAY });
  assert.equal(summary.total, 3);
  assert.equal(summary.operativos, 1);
  assert.equal(summary.requierenMantencion, 1);
  assert.equal(summary.fueraDeServicio, 1);
  assert.equal(summary.conTelemetria, 1);
  assert.equal(summary.asignadosAObra, 0);
  assert.equal(summary.sinAsignar, 3);
  assert.deepEqual(summary.byType.map((row) => row.name), ["Vehículo", "Maquinaria"]);
});

test("buildAssetsSummary never fabricates an obra assignment (no such field exists on the model)", () => {
  const summary = buildAssetsSummary([{ id: 1, tipo: "equipo", estado: "operativo", sensores_count: 0, mantenimientos: [] }], { today: TODAY });
  assert.equal(summary.asignadosAObra, 0);
  assert.equal(summary.sinAsignar, summary.total);
});

test("buildAssetsSummary on an empty list returns all-zero, not undefined/NaN", () => {
  const summary = buildAssetsSummary([], { today: TODAY });
  assert.equal(summary.total, 0);
  assert.equal(summary.operativos, 0);
  assert.equal(summary.conTelemetria, 0);
  assert.deepEqual(summary.byType, []);
  assert.deepEqual(summary.upcomingMaintenances, []);
});
