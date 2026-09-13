import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./ObraResumenPage.jsx", import.meta.url), "utf8");

test("obra summary excludes legacy indicators and recent activity", () => {
  assert.equal(source.includes("Indicadores ambientales"), false);
  assert.equal(source.includes("Actividad reciente"), false);
});

test("obra summary renders the required executive sequence", () => {
  const labels = ["Obra · Gestión ambiental", "Lectura ejecutiva", "Indicadores principales", "GEI por alcance", "Estado por flujo", "id=\"insights\""];
  let cursor = -1;
  labels.forEach((label) => {
    const position = source.indexOf(label);
    assert.ok(position > cursor, `${label} debe conservar el orden ejecutivo`);
    cursor = position;
  });
});
