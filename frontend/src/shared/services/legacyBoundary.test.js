import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

function sourceFiles(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = resolve(directory, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(js|jsx)$/.test(name) && !name.endsWith(".test.js") ? [path] : [];
  });
}

function consumersOf(symbol) {
  return sourceFiles(sourceRoot)
    .filter((path) => readFileSync(path, "utf8").includes(symbol))
    .map((path) => relative(sourceRoot, path).replaceAll("\\", "/"))
    .sort();
}

test("los writers legacy visibles permanecen limitados a consumidores de compatibilidad", () => {
  assert.deepEqual(consumersOf("createRegistroEmision"), [
    "shared/components/ImportarEvidenciaObraModal.jsx",
    "shared/services/api.js",
  ]);
  assert.deepEqual(consumersOf("createEmpresaRegistroAmbiental"), [
    "presets/aserradero/pages/AserraderoModulePage.jsx",
    "shared/services/api.js",
  ]);
  assert.deepEqual(consumersOf("createTransporteLoteForestal"), [
    "presets/aserradero/pages/LotesForestalesPage.jsx",
    "shared/services/api.js",
  ]);
});

test("los clientes legacy sin consumidores fueron retirados", () => {
  [
    "aplicarFactorRegistroEmision",
    "confirmRegistroEmisionImport",
    "createFactorEmision",
    "createTransporteObra",
    "getObraDetail",
    "previewRegistroEmisionImport",
    "updateFactorEmision",
  ].forEach((symbol) => assert.deepEqual(consumersOf(symbol), [], symbol));
});
