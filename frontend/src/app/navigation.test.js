import assert from "node:assert/strict";
import test from "node:test";

import { getPageContext, getUnifiedNavigation } from "./navigation.js";

const preset = { unitPluralLabel: "Obras", unitLabel: "Obra" };

test("portfolio scope points Inicio/Reportes/Control/Configuración at organization-level routes", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  assert.equal(nav.home.path, "/inicio");
  const [works, reports, control, administration] = nav.groups[0].items;
  assert.equal(works.path, "/obras");
  assert.equal(reports.path, "/reportes");
  assert.equal(control.path, "/gobernanza");
  assert.equal(administration.path, "/administracion");
});

test("obra scope points the SAME five items at that obra's routes, Obras unchanged", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "42" } });
  assert.equal(nav.home.path, "/obras/42/resumen");
  const [works, reports, control, administration] = nav.groups[0].items;
  assert.equal(works.path, "/obras");
  assert.equal(reports.path, "/obras/42/reportes");
  assert.equal(control.path, "/obras/42/control");
  assert.equal(administration.path, "/obras/42/configuracion");
});

test("there is exactly one navigation group (a single unified sidebar, never a second obra menu)", () => {
  const portfolio = getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
  const obra = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: "1" } });
  assert.equal(portfolio.groups.length, 1);
  assert.equal(obra.groups.length, 1);
  assert.equal(portfolio.groups[0].items.length, 4);
  assert.equal(obra.groups[0].items.length, 4);
});

test("an obra scope without an obraId falls back to the portfolio targets", () => {
  const nav = getUnifiedNavigation({ preset, scope: { type: "obra", obraId: null } });
  assert.equal(nav.home.path, "/inicio");
});

test("getPageContext resolves the new obra control/configuración routes by exact pattern", () => {
  assert.equal(getPageContext("/obras/42/control", preset).title, "Control de obra");
  assert.equal(getPageContext("/obras/42/configuracion", preset).title, "Configuración de obra");
});

test("getPageContext falls back to the unified nav item for an untitled path", () => {
  const context = getPageContext("/reportes", preset);
  assert.equal(context.title, "Centro de reportes");
});
