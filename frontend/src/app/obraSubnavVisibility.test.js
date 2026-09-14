import assert from "node:assert/strict";
import test from "node:test";

import { getUnifiedNavigation } from "./navigation.js";
import { withObraFlowStates } from "./obraSubnavVisibility.js";

const preset = { unitPluralLabel: "Obras", unitLabel: "Obra" };

function operationChildren(navigation) {
  return navigation.groups[0].items.find((item) => item.id === "operation").children;
}

test("a flow marked no_aplica is dropped from Operación's children", () => {
  const nav = withObraFlowStates(
    getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } }),
    [{ clave: "ruido", estado_obra: "no_aplica" }],
  );
  const labels = operationChildren(nav).map((item) => item.label);
  assert.equal(labels.includes("Ruido"), false);
});

test("a flow still pendiente stays visible with a pendiente state, never hidden", () => {
  const nav = withObraFlowStates(
    getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } }),
    [{ clave: "energia", estado_obra: "pendiente" }],
  );
  const energia = operationChildren(nav).find((item) => item.id === "energy");
  assert.ok(energia, "energia must stay in the list");
  assert.equal(energia.state, "pendiente");
});

test("a flow marked aplica keeps an aplica state", () => {
  const nav = withObraFlowStates(
    getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } }),
    [{ clave: "agua", estado_obra: "aplica" }],
  );
  const agua = operationChildren(nav).find((item) => item.id === "water");
  assert.equal(agua.state, "aplica");
});

test("every gestión item remains outside operation applicability", () => {
  const nav = withObraFlowStates(getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } }), []);
  assert.equal(operationChildren(nav).some((item) => item.id === "operationOverview"), false);
  const management = nav.groups[0].items.find((item) => item.id === "management");
  assert.equal(management.children.length, 4);
});

test("with no applicability data at all, flows default to pendiente (visible), not hidden", () => {
  const nav = withObraFlowStates(getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } }), []);
  const flows = operationChildren(nav);
  assert.equal(flows.length > 0, true);
  assert.ok(flows.every((item) => item.state === "pendiente"));
});

test("portfolio-scope navigation passes through untouched (no operation item to gate)", () => {
  const nav = withObraFlowStates(getUnifiedNavigation({ preset, scope: { type: "portfolio" } }), []);
  assert.ok(!nav.groups[0].items.some((item) => item.id === "operation"));
});
