import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./Sidebar.jsx", import.meta.url), "utf8");

test("there is a single navigation tree — no separate obra subnav component reintroduced", () => {
  assert.equal(source.includes("ObraActiveSubnav"), false, "the separate 'OBRA ACTIVA' block must not come back");
  assert.equal(source.includes("SubnavItem"), false, "obra flows must render through the same NavItem as everything else");
  assert.equal(source.includes("getObraContextualSubnav"), false, "obra nav must be merged into getUnifiedNavigation, not a second function");
});

test("GeneralNavigation owns the single scrollable region again (no wrapper div needed without a sibling to push down)", () => {
  const navFunctionStart = source.indexOf("function GeneralNavigation");
  const navFunctionBody = source.slice(navFunctionStart, navFunctionStart + 700);
  assert.ok(navFunctionBody.includes("flex-1"), "flex-1 must live on GeneralNavigation's own <nav> now that it is the only nav region");
  assert.ok(navFunctionBody.includes("overflow-y-auto"));
});

test("no stray push-to-bottom pattern (mt-auto / justify-between) exists in the sidebar", () => {
  assert.equal(source.includes("mt-auto"), false);
  assert.equal(source.includes("justify-between"), false);
});

test("the context selector offers 'Ver todas las obras'", () => {
  assert.ok(source.includes("Ver todas las obras"));
});

test("desktop collapse is persisted and mobile keeps the sidebar expanded", () => {
  assert.ok(source.includes("carbono-zero.sidebar-collapsed"));
  assert.ok(source.includes("lg:w-[76px]"));
  assert.ok(source.includes("lg:w-[288px]"));
});
