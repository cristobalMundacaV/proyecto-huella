import test from "node:test";
import assert from "node:assert/strict";
import { filterSelectOptions, normalizeSearchText } from "./search.js";

const options = [
  { value: "biobio", label: "Biobío" },
  { value: "nuble", label: "Ñuble" },
  { value: "los-angeles", label: "Los Ángeles" },
];

test("normaliza mayúsculas y tildes para búsquedas tolerantes", () => {
  assert.equal(normalizeSearchText("  REGIÓN DEL BIOBÍO "), "region del biobio");
  assert.equal(normalizeSearchText("Ñuble"), "nuble");
});

test("filtra opciones sin distinguir tildes ni mayúsculas", () => {
  assert.deepEqual(filterSelectOptions(options, "BIOBIO").map(({ value }) => value), ["biobio"]);
  assert.deepEqual(filterSelectOptions(options, "angeles").map(({ value }) => value), ["los-angeles"]);
  assert.deepEqual(filterSelectOptions(options, "nuble").map(({ value }) => value), ["nuble"]);
});

test("conserva todas las opciones con búsqueda vacía y devuelve vacío sin coincidencias", () => {
  assert.equal(filterSelectOptions(options, "").length, options.length);
  assert.deepEqual(filterSelectOptions(options, "inexistente"), []);
});
