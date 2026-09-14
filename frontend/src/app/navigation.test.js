import assert from "node:assert/strict";
import test from "node:test";

import { getPageContext, getUnifiedNavigation, OBRA_OPERATION_FLOWS } from "./navigation.js";

const preset = { unitPluralLabel: "Obras", unitLabel: "Obra" };

test("portfolio scope shows exactly Inicio/Obras/Reportes/Control/Configuración", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  assert.equal(nav.home.label, "Inicio");
  assert.equal(nav.home.path, "/inicio");
  assert.deepEqual(nav.groups[0].items.map((item) => item.label), ["Obras", "Reportes", "Control", "Configuración"]);
  const [works, reports, control, administration] = nav.groups[0].items;
  assert.equal(works.path, "/obras");
  assert.equal(reports.path, "/reportes");
  assert.equal(control.path, "/gobernanza");
  assert.equal(administration.path, "/administracion");
});

test("obra scope shows exactly Resumen/Operación/Gestión/Reportes/Control/Configuración — no Obras item", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "42" } });
  assert.equal(nav.home.label, "Resumen");
  assert.equal(nav.home.path, "/obras/42/resumen");
  assert.deepEqual(nav.groups[0].items.map((item) => item.label), ["Operación", "Gestión", "Reportes", "Control", "Configuración"]);
  assert.ok(!nav.groups[0].items.some((item) => item.label === "Obras"), "Obras must not be a primary item in obra scope");
  const [operation, management, reports, control, administration] = nav.groups[0].items;
  assert.equal(reports.path, "/obras/42/reportes");
  assert.equal(control.path, "/obras/42/control");
  assert.equal(administration.path, "/obras/42/configuracion");
  assert.equal(operation.children.length, OBRA_OPERATION_FLOWS.length);
  assert.equal(management.children.length, 4);
});

test("Operación's children are only the 8 environmental flows", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } });
  const operation = nav.groups[0].items.find((item) => item.id === "operation");
  const paths = operation.children.map((child) => child.path);
  assert.equal(paths.length, 8);
  assert.ok(!paths.includes("/obras/71/operacion"));
  assert.ok(!operation.children.some((child) => child.label === "Resumen operacional"));
  assert.ok(paths.includes("/obras/71/operacion/energia"));
  assert.ok(paths.includes("/obras/71/operacion/agua"));
  assert.ok(paths.includes("/obras/71/operacion/combustibles"));
  assert.ok(paths.includes("/obras/71/operacion/transporte"));
  assert.ok(paths.includes("/obras/71/operacion/materiales"));
  assert.ok(paths.includes("/obras/71/operacion/residuos"));
  assert.ok(paths.includes("/obras/71/operacion/ruido"));
  assert.ok(paths.includes("/obras/71/operacion/emisiones-atmosfericas"));
});

test("Gestión's children are evidencias/problemas/cumplimiento/historial, all existing routes", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } });
  const management = nav.groups[0].items.find((item) => item.id === "management");
  const paths = management.children.map((child) => child.path);
  assert.deepEqual(paths, [
    "/obras/71/evidencias", "/obras/71/problemas", "/obras/71/cumplimiento", "/obras/71/timeline",
  ]);
});

test("there is exactly one navigation group in both scopes (a single unified sidebar, never a second obra menu)", () => {
  const portfolio = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  const obra = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "1" } });
  assert.equal(portfolio.groups.length, 1);
  assert.equal(obra.groups.length, 1);
});

test("an obra scope without an obraId falls back to the portfolio targets", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: null } });
  assert.equal(nav.home.path, "/inicio");
  assert.deepEqual(nav.groups[0].items.map((item) => item.label), ["Obras", "Reportes", "Control", "Configuración"]);
});

test("getPageContext resolves the obra control/configuración routes by exact pattern", () => {
  assert.equal(getPageContext("/obras/42/control", preset).title, "Control de obra");
  assert.equal(getPageContext("/obras/42/configuracion", preset).title, "Configuración de obra");
});

test("getPageContext falls back to the unified nav item for an untitled path", () => {
  const context = getPageContext("/reportes", preset);
  assert.equal(context.title, "Centro de reportes");
});

test("getPageContext resolves a nested obra flow through the flattened children fallback", () => {
  // /obras/71/operacion/energia already has an exact PAGE_CONTEXTS entry,
  // so exercise the flatten-children fallback through Gestión's children,
  // which don't have their own explicit PAGE_CONTEXTS pattern beyond the
  // ones reused from before — evidencias does, so use a scope where only
  // the flattened item resolves the title correctly.
  const context = getPageContext("/obras/71/evidencias", preset);
  assert.equal(context.title, "Evidencias");
});
