import test from "node:test";
import assert from "node:assert/strict";

import { evidenceDetailPath } from "./evidencePaths.js";

test("la evidencia conserva contexto de obra cuando existe", () => {
  assert.equal(evidenceDetailPath(42, 71), "/obras/71/evidencias/42");
});

test("la evidencia global conserva navegación global", () => {
  assert.equal(evidenceDetailPath(42), "/datos/evidencias/42");
});
