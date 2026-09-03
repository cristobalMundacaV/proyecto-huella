import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { assetDraft, assetPayload, selectableVehicleAssets } from "./assetVehicleContract.js";

test("creación UI envía una especialización de vehículo válida y opcional", () => {
  const payload = assetPayload(assetDraft({
    codigo: "CAM-EPN-01",
    nombre: "Camión obra Parque Norte 01",
  }));
  assert.equal(payload.tipo, "vehiculo");
  assert.deepEqual(payload.vehiculo, {
    patente: "", marca: "", modelo: "", anio: null,
    tipo_vehiculo: "", combustible: "", capacidad_carga: null,
    unidad_capacidad_carga: "", numero_ejes: null,
  });
});

test("edición precarga y actualiza la especialización existente", () => {
  const draft = assetDraft({
    id: 8, codigo: "CAM-EPN-01", nombre: "Camión obra Parque Norte 01",
    tipo: "vehiculo", estado: "operativo",
    vehiculo: { id: 31, patente: "ABCD-12", marca: "Volvo" },
  });
  draft.vehiculo.modelo = "FMX";
  const payload = assetPayload(draft);
  assert.equal(payload.vehiculo.patente, "ABCD-12");
  assert.equal(payload.vehiculo.marca, "Volvo");
  assert.equal(payload.vehiculo.modelo, "FMX");
  assert.equal("id" in payload.vehiculo, false);
});

test("Transporte ignora legacy sin especialización y muestra vehículos reales", () => {
  const valid = { id: 1, nombre: "Camión obra Parque Norte 01", tipo: "vehiculo", vehiculo: { id: 21 } };
  assert.deepEqual(selectableVehicleAssets([
    valid,
    { id: 2, nombre: "Legacy", tipo: "vehiculo" },
    { id: 3, nombre: "Especialización vacía", tipo: "vehiculo", vehiculo: {} },
    { id: 4, nombre: "Excavadora", tipo: "maquinaria", vehiculo: { id: 22 } },
  ]), [valid]);
});

test("Activos y Transporte consumen el contrato compartido", () => {
  const assetsPage = readFileSync(new URL("../pages/ActivosPage.jsx", import.meta.url), "utf8");
  const transportModal = readFileSync(
    new URL("../../operacion/components/TransportRecordModal.jsx", import.meta.url),
    "utf8",
  );
  assert.match(assetsPage, /assetPayload\(dialog\)/);
  assert.match(assetsPage, /dialog\?\.tipo === "vehiculo"/);
  assert.match(assetsPage, /value=\{dialog\.vehiculo\?\.\[field\]/);
  assert.match(transportModal, /selectableVehicleAssets\(vehicles\)/);
  assert.match(transportModal, /value=\{item\.vehiculo\.id\}/);
  assert.doesNotMatch(transportModal, /item\.vehiculo\?\.id \|\|/);
});
