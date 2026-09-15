import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./ObraResumenPage.jsx", import.meta.url), "utf8");

test("obra summary excludes legacy indicators and recent activity", () => {
  assert.equal(source.includes("Indicadores ambientales"), false);
  assert.equal(source.includes("Actividad reciente"), false);
});

test("obra summary renders the required executive sequence — general KPIs, then the multiflow balance, then GEI as its own dimension, then recommendations", () => {
  const labels = ["Obra · Gestión ambiental", "Lectura ejecutiva", "Estado general del período", "EnvironmentalBalanceSection", "Clima / GEI", "GEI por alcance", "id=\"insights\""];
  let cursor = -1;
  labels.forEach((label) => {
    const position = source.indexOf(label, cursor + 1);
    assert.ok(position > cursor, `${label} debe conservar el orden ejecutivo`);
    cursor = position;
  });
});

test("GEI is never presented as the sole measure of environmental performance — the balance section covers every physical flow separately", () => {
  assert.equal(source.includes("EnvironmentalBalanceSection"), true);
  assert.equal(source.includes("buildEnvironmentalBalance"), true);
  assert.equal(source.includes("buildGeiPerformance"), true);
});
