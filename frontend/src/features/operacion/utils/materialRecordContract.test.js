import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MATERIAL_OPERATIONAL_CATEGORIES, MATERIAL_OPERATIONAL_UNITS, compatibleMaterialReceptions, createMaterialMovementTechnicalCode, materialActivityPayload, materialEventPayload, operationalMaterialPayload } from "./materialRecordContract.js";

test("crea material operacional sin metadata manual y con unidad gobernada", () => {
  const payload = operationalMaterialPayload({ name: " Cemento Portland ", category: "cemento", baseUnit: "kg", supplier: " Proveedor Demo ", description: "" });
  assert.deepEqual(payload, { nombre: "Cemento Portland", categoria: "cemento", unidad_base: "kg", proveedor_fabricante: "Proveedor Demo", descripcion: "", activo: true });
  assert.deepEqual(MATERIAL_OPERATIONAL_UNITS.map((item) => item.value), ["kg", "t", "m3", "L", "unidad"]);
  assert.equal(Object.hasOwn(payload, "metadata"), false);
  assert.equal(Object.hasOwn(payload, "codigo"), false);
  assert.deepEqual(MATERIAL_OPERATIONAL_CATEGORIES.map((item) => item.value), ["cemento", "hormigon", "acero", "madera", "aridos", "ladrillos_bloques", "yeso_placas", "vidrio", "aluminio_otros_metales", "aislacion", "pinturas_revestimientos", "plasticos_pvc", "tuberias", "asfalto", "prefabricados", "otros"]);
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

test("evento con respaldo usa multipart y conserva los campos documentales", () => {
  const evidence = new Blob(["pdf de prueba"], { type: "application/pdf" });
  Object.defineProperty(evidence, "name", { value: "guia.pdf" });
  const form = { material: "7", type: "recepcion", amount: "10000", unit: "kg", source: "9", evidenceFile: evidence, evidenceType: "guia_despacho", evidenceName: "Guia cemento" };
  const payload = materialEventPayload({ activityId: 88, workId: 71, form, timestamp: "2026-09-11T12:00:00.000Z" });
  assert.equal(payload instanceof FormData, true);
  assert.equal(payload.get("evidencia_archivo").type, "application/pdf");
  assert.equal(payload.get("evidencia_archivo").size, evidence.size);
  assert.equal(payload.get("evidencia_tipo"), "guia_despacho");
  assert.equal(payload.get("evidencia_nombre"), "Guia cemento");
});

test("uso incluye recepcion seleccionada y las candidatas respetan material, obra, unidad y fecha", () => {
  const timestamp = "2026-09-11T12:00:00.000Z";
  const form = { material: "7", type: "uso", amount: "2500", unit: "kg", source: "9", originReception: "31" };
  assert.equal(materialEventPayload({ activityId: 88, workId: 71, form, timestamp }).evento_origen, 31);
  const base = { tipo: "recepcion", material: 7, obra: 71, cantidad_detalle: { unidad: "kg" }, fecha_hora: "2026-09-04T12:00:00.000Z" };
  const candidates = compatibleMaterialReceptions([
    { ...base, id: 31 }, { ...base, id: 32, material: 8 }, { ...base, id: 33, obra: 72 },
    { ...base, id: 34, cantidad_detalle: { unidad: "t" } }, { ...base, id: 35, fecha_hora: "2026-09-12T12:00:00.000Z" },
    { ...base, id: 36, tipo: "uso" },
  ], { materialId: 7, workId: 71, unit: "kg", timestamp });
  assert.deepEqual(candidates.map((item) => item.id), [31]);
});

test("movimiento sin recepcion elegida conserva compatibilidad legacy", () => {
  const form = { material: "7", type: "uso", amount: "1", unit: "kg", source: "9", originReception: "" };
  const payload = materialEventPayload({ activityId: 88, workId: 71, form, timestamp: "2026-09-11T12:00:00.000Z" });
  assert.equal(Object.hasOwn(payload, "evento_origen"), false);
});

test("modal filtra fuentes y conserva estándar operacional, errores y selección creada", () => {
  const modal = readFileSync(new URL("../components/MaterialEventModal.jsx", import.meta.url), "utf8");
  assert.match(modal, /listDataSources\(organizationId, "materiales"\)/);
  assert.match(modal, /listEvidenceTypes\("materiales"\)/);
  assert.match(modal, /\+ Agregar respaldo/);
  assert.match(modal, /material: String\(created\.id\)/);
  assert.match(modal, /unit: created\.unidad_base/);
  assert.match(modal, /humanizeApiError/);
  assert.match(modal, /<Toast/);
  assert.match(modal, /<Alert tone="danger"/);
  assert.match(modal, /eyebrow="REGISTRO OPERACIONAL"/);
  assert.match(modal, /Recepción de origen/);
  assert.match(modal, /compatibleReceptions\.length === 1/);
  assert.doesNotMatch(modal, /form\.code/);
  assert.doesNotMatch(modal, /technicalSpecification/);
  for (const title of ["Material", "Movimiento", "Trazabilidad"]) assert.match(modal, new RegExp(`title="${title}"`));
});
