import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MATERIAL_OPERATIONAL_UNITS, createMaterialMovementTechnicalCode, materialActivityPayload, materialEventPayload, operationalMaterialPayload } from "./materialRecordContract.js";

test("crea material operacional sin metadata manual y con unidad gobernada", () => {
  const payload = operationalMaterialPayload({ code: " CEM-EPN-01 ", name: " Cemento Portland ", category: " cemento ", baseUnit: "kg", supplier: " Proveedor Demo ", description: "", technicalSpecification: "" });
  assert.deepEqual(payload, { codigo: "CEM-EPN-01", nombre: "Cemento Portland", categoria: "cemento", unidad_base: "kg", proveedor_fabricante: "Proveedor Demo", descripcion: "", especificacion_tecnica: "", activo: true });
  assert.deepEqual(MATERIAL_OPERATIONAL_UNITS.map((item) => item.value), ["kg", "t", "m3", "L", "unidad"]);
  assert.equal(Object.hasOwn(payload, "metadata"), false);
});

test("actividad usa identidad MATMOV y evento conserva el contrato operacional", () => {
  const code = createMaterialMovementTechnicalCode();
  const timestamp = "2026-09-11T12:00:00.000Z";
  const form = { material: "7", type: "recepcion", amount: "10000", unit: "kg", source: "9" };
  const activity = materialActivityPayload({ workId: 71, form, material: { nombre: "Cemento Portland" }, timestamp, code });
  const event = materialEventPayload({ activityId: 88, workId: 71, form, timestamp });
  assert.match(code, /^MATMOV-.+/);
  assert.deepEqual(activity, { codigo: code, obra: 71, tipo: "movimiento_material", nombre: "recepcion de Cemento Portland", timestamp_inicio: timestamp });
  assert.deepEqual(event, { material: 7, actividad: 88, obra: 71, tipo: "recepcion", fecha_hora: timestamp, cantidad: "10000", unidad: "kg", fuente: 9 });
});

test("modal filtra fuentes y conserva estÃ¡ndar operacional, errores y selecciÃ³n creada", () => {
  const modal = readFileSync(new URL("../components/MaterialEventModal.jsx", import.meta.url), "utf8");
  assert.match(modal, /listDataSources\(organizationId, "materiales"\)/);
  assert.match(modal, /material: String\(created\.id\)/);
  assert.match(modal, /unit: created\.unidad_base/);
  assert.match(modal, /humanizeApiError/);
  assert.match(modal, /<Toast/);
  assert.match(modal, /<Alert tone="danger"/);
  assert.match(modal, /eyebrow="REGISTRO OPERACIONAL"/);
  for (const title of ["Material", "Movimiento", "Trazabilidad"]) assert.match(modal, new RegExp(`title="${title}"`));
});
