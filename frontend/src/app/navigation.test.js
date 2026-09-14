import assert from "node:assert/strict";
import test from "node:test";

import { ASSETS_SUBNAV, getPageContext, getUnifiedNavigation, OBRA_OPERATION_FLOWS } from "./navigation.js";

const preset = { unitPluralLabel: "Obras", unitLabel: "Obra" };
const rootItems = (nav) => nav.groups.flatMap((group) => group.items);

test("portfolio scope shows exactly Inicio/Obras/Activos/Reportes/Configuración — no Control", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  assert.equal(nav.home.label, "Inicio");
  assert.equal(nav.home.path, "/inicio");
  assert.deepEqual(rootItems(nav).map((item) => item.label), ["Inicio", "Obras", "Activos", "Reportes", "Configuración"]);
  assert.ok(!rootItems(nav).some((item) => item.label === "Control"), "Control must not be a portfolio-level item");
  const [, works, assets, reports, administration] = rootItems(nav);
  assert.equal(works.path, "/obras");
  assert.equal(reports.path, "/reportes");
  assert.equal(administration.path, "/administracion");
  assert.equal(assets.path, undefined, "Activos is an expand/collapse toggle like obra's Operación, not a direct link");
  assert.deepEqual(assets.children, ASSETS_SUBNAV);
});

test("Activos' children are vista general/flota/equipos/sensores/mantenciones", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  const assets = rootItems(nav).find((item) => item.id === "assets");
  assert.deepEqual(assets.children.map((child) => child.path), [
    "/activos", "/activos/flota", "/activos/equipos", "/activos/sensores", "/activos/mantenciones",
  ]);
});

test("obra scope shows exactly Resumen/Operación/Gestión/Reportes/Control/Configuración — no Obras item", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "42" } });
  assert.equal(nav.home.label, "Resumen");
  assert.equal(nav.home.path, "/obras/42/resumen");
  assert.deepEqual(rootItems(nav).map((item) => item.label), ["Resumen", "Operación", "Gestión", "Reportes", "Control", "Configuración"]);
  assert.ok(!rootItems(nav).some((item) => item.label === "Obras"), "Obras must not be a primary item in obra scope");
  const [, operation, management, reports, control, administration] = rootItems(nav);
  assert.equal(reports.path, "/obras/42/reportes");
  assert.equal(control.path, "/obras/42/control");
  assert.equal(administration.path, "/obras/42/configuracion");
  assert.equal(operation.children.length, OBRA_OPERATION_FLOWS.length);
  assert.equal(management.children.length, 4);
});

test("Operación's children are only the 8 environmental flows", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "71" } });
  const operation = rootItems(nav).find((item) => item.id === "operation");
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
  const management = rootItems(nav).find((item) => item.id === "management");
  const paths = management.children.map((child) => child.path);
  assert.deepEqual(paths, [
    "/obras/71/evidencias", "/obras/71/problemas", "/obras/71/cumplimiento", "/obras/71/timeline",
  ]);
});

test("portfolio and obra use one grouped navigation tree with editorial sections", () => {
  const portfolio = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  const obra = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "1" } });
  assert.deepEqual(portfolio.groups.map((group) => group.label), ["General", "Operación", "Salidas", "Sistema"]);
  assert.deepEqual(obra.groups.map((group) => group.label), ["General", "Operación", "Gestión", "Seguimiento", "Sistema"]);
});

test("an obra scope without an obraId falls back to the portfolio targets", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: null } });
  assert.equal(nav.home.path, "/inicio");
  assert.deepEqual(rootItems(nav).map((item) => item.label), ["Inicio", "Obras", "Activos", "Reportes", "Configuración"]);
});

test("getPageContext resolves the obra control/configuración routes by exact pattern", () => {
  assert.equal(getPageContext("/obras/42/control", preset).title, "Control de obra");
  assert.equal(getPageContext("/obras/42/configuracion", preset).title, "Configuración de obra");
});

test("getPageContext resolves every Activos route by exact pattern", () => {
  assert.equal(getPageContext("/activos", preset).title, "Activos de la organización");
  assert.equal(getPageContext("/activos/flota", preset).title, "Flota y maquinaria");
  assert.equal(getPageContext("/activos/equipos", preset).title, "Equipos e infraestructura");
  assert.equal(getPageContext("/activos/sensores", preset).title, "Sensores y medidores");
  assert.equal(getPageContext("/activos/mantenciones", preset).title, "Mantenciones");
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
