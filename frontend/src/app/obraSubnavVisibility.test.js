import assert from "node:assert/strict";
import test from "node:test";

import { getObraContextualSubnav } from "./navigation.js";
import { withObraFlowStates } from "./obraSubnavVisibility.js";

test("a flow marked no_aplica is dropped from the operation group", () => {
  const subnav = withObraFlowStates(getObraContextualSubnav("71"), [
    { clave: "ruido", estado_obra: "no_aplica" },
  ]);
  const labels = subnav.groups[0].items.map((item) => item.label);
  assert.equal(labels.includes("Ruido"), false);
});

test("a flow still pendiente stays visible with a pendiente state, never hidden", () => {
  const subnav = withObraFlowStates(getObraContextualSubnav("71"), [
    { clave: "energia", estado_obra: "pendiente" },
  ]);
  const energia = subnav.groups[0].items.find((item) => item.id === "energy");
  assert.ok(energia, "energia must stay in the list");
  assert.equal(energia.state, "pendiente");
});

test("a flow marked aplica keeps an aplica state", () => {
  const subnav = withObraFlowStates(getObraContextualSubnav("71"), [
    { clave: "agua", estado_obra: "aplica" },
  ]);
  const agua = subnav.groups[0].items.find((item) => item.id === "water");
  assert.equal(agua.state, "aplica");
});

test("resumen operacional and every management item are never gated by applicability", () => {
  const subnav = withObraFlowStates(getObraContextualSubnav("71"), []);
  const overview = subnav.groups[0].items.find((item) => item.id === "operationOverview");
  assert.equal(overview.state, "always");
  assert.equal(subnav.groups[1].items.length, 4);
  assert.ok(subnav.groups[1].items.every((item) => item.state === "always"));
});

test("with no applicability data at all, flows default to pendiente (visible), not hidden", () => {
  const subnav = withObraFlowStates(getObraContextualSubnav("71"), []);
  const flows = subnav.groups[0].items.filter((item) => item.id !== "operationOverview");
  assert.equal(flows.length > 0, true);
  assert.ok(flows.every((item) => item.state === "pendiente"));
});
