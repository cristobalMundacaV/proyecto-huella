import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const router = readFileSync(new URL("./router.jsx", import.meta.url), "utf8");

test("la raíz renderiza la landing pública sin entrar a guards autenticados", () => {
  assert.match(router, /<Route path="\/" element=\{<CarbonoZeroLanding \/>\} \/>/);
  assert.doesNotMatch(
    router,
    /<Route element=\{<AuthenticatedLayout \/>\}>\s*<Route index/,
  );
  assert.doesNotMatch(router, /<Route index element=\{<Navigate to="\/inicio" replace \/>\} \/>/);
});

test("conserva los index de saas, obra y operación", () => {
  assert.match(router, /<Route index element=\{<SaaSDashboardPage \/>\} \/>/);
  assert.match(router, /<Route index element=\{<Navigate to="resumen" replace \/>\} \/>/);
  assert.match(router, /<Route index element=\{<OperacionOverviewPage \/>\} \/>/);
  assert.equal(router.match(/<Route index /g)?.length, 3);
});
