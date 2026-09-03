import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  createJourneyTechnicalCode,
  transportActivityPayload,
  transportJourneyPayload,
} from "./transportRecordContract.js";

const form = {
  vehicle: "21",
  origin: " Bodega proveedor Los Ángeles ",
  destination: " Edificio Parque Norte ",
  distance: "35",
  load: "8",
  fuel: "12",
  source: "9",
  loadState: "cargado",
  tripType: "ida",
};

test("actividad y viaje comparten una identidad técnica válida", () => {
  const code = createJourneyTechnicalCode();
  const timestamp = "2026-09-11T12:00:00.000Z";
  const activity = transportActivityPayload({ workId: 71, form, timestamp, code });
  const journey = transportJourneyPayload({ activityId: 88, form, timestamp, code });

  assert.match(code, /^VIAJE-.+/);
  assert.equal(activity.codigo, code);
  assert.equal(journey.codigo, code);
  assert.equal(activity.obra, 71);
  assert.equal(activity.tipo, "transporte");
  assert.equal(activity.nombre, "Viaje Bodega proveedor Los Ángeles → Edificio Parque Norte");
  assert.equal(journey.distancia, "35");
  assert.equal(journey.carga, "8");
  assert.equal(journey.combustible, "12");
});

test("modal conserva trazabilidad, errores visibles y estándar operacional", () => {
  const modal = readFileSync(
    new URL("../components/TransportRecordModal.jsx", import.meta.url),
    "utf8",
  );
  assert.match(modal, /listDataSources\(organizationId, "transporte"\)/);
  assert.match(modal, /humanizeApiError/);
  assert.match(modal, /<Toast/);
  assert.match(modal, /<Alert tone="danger"/);
  assert.match(modal, /eyebrow="REGISTRO OPERACIONAL"/);
  for (const title of ["Trayecto", "Magnitudes", "Contexto", "Trazabilidad"]) {
    assert.match(modal, new RegExp(`title="${title}"`));
  }
});
