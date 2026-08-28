import assert from "node:assert/strict";
import test from "node:test";

import { captureStateInfo, eligibilityStateInfo } from "./canonicalDataState.js";

test("presenta la elegibilidad resuelta por backend sin recalcularla", () => {
  assert.equal(eligibilityStateInfo({ estado: "calculable_completo" }).label, "Listo para evaluación");
  assert.equal(eligibilityStateInfo({ estado: "calculable_incompleto" }).label, "Listo para evaluación");
  assert.equal(eligibilityStateInfo({ estado: "no_calculable" }).label, "No elegible");
  assert.equal(eligibilityStateInfo({ estado: "requiere_revision" }).label, "Requiere revisión");
});

test("distingue captura, incompletitud y revisión", () => {
  assert.equal(captureStateInfo("completado").label, "Capturado");
  assert.equal(captureStateInfo("recibido").label, "Incompleto");
  assert.equal(captureStateInfo("observada").label, "Requiere revisión");
});
