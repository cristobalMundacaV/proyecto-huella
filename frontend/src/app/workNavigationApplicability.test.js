import assert from "node:assert/strict";
import test from "node:test";

import {
  getConfirmedWorkCapabilityKeys,
  hasPendingWorkApplicability,
  isWorkModuleConfirmed,
} from "./workNavigationApplicability.js";

test("solo confirma capacidades marcadas como aplica", () => {
  const confirmed = getConfirmedWorkCapabilityKeys([
    { clave: "agua", estado_obra: "aplica" },
    { clave: "energia", estado_obra: "pendiente" },
    { clave: "ruido", estado_obra: "no_determinado" },
    { clave: "transporte", estado_obra: "no_aplica" },
    { clave: "materiales", estado_obra: "sin_datos" },
  ]);

  assert.deepEqual([...confirmed], ["agua"]);
});

test("detecta estados pendientes sin tratar no aplica como pendiente", () => {
  assert.equal(hasPendingWorkApplicability([
    { clave: "agua", estado_obra: "no_aplica" },
    { clave: "energia", estado_obra: "aplica" },
  ]), false);
  assert.equal(hasPendingWorkApplicability([
    { clave: "ruido", estado_obra: "pendiente" },
  ]), true);
});

test("habilita un modulo agregado cuando al menos una capacidad relacionada aplica", () => {
  const confirmed = new Set(["residuos_peligrosos"]);
  assert.equal(isWorkModuleConfirmed({
    domain: "residuos",
    capabilities: ["residuos_no_peligrosos", "residuos_peligrosos"],
  }, confirmed), true);
});
