import assert from "node:assert/strict";
import test from "node:test";

import { FLOW_SECTIONS, flowBaseFromPathname, sectionFromPathname } from "./flowWorkspaceSections.js";

test("FLOW_SECTIONS is exactly Resumen | Registros | Tendencias | Calidad | Sensores, in that order", () => {
  assert.deepEqual(FLOW_SECTIONS, ["resumen", "registros", "tendencias", "calidad", "sensores"]);
});

test("sectionFromPathname defaults to resumen for the flow's own root path", () => {
  assert.equal(sectionFromPathname("/obras/1/operacion/agua"), "resumen");
  assert.equal(sectionFromPathname("/obras/1/operacion/agua/"), "resumen");
});

test("sectionFromPathname recognizes each real section as a deep link", () => {
  for (const section of ["registros", "tendencias", "calidad", "sensores"]) {
    assert.equal(sectionFromPathname(`/obras/1/operacion/agua/${section}`), section);
  }
});

test("sectionFromPathname never treats an unknown trailing segment as a section — falls back to resumen", () => {
  assert.equal(sectionFromPathname("/obras/1/operacion/agua/algo-inventado"), "resumen");
  assert.equal(sectionFromPathname(""), "resumen");
  assert.equal(sectionFromPathname(undefined), "resumen");
});

test("flowBaseFromPathname strips the section segment to recover the flow's own root", () => {
  assert.equal(flowBaseFromPathname("/obras/1/operacion/agua/registros", "registros"), "/obras/1/operacion/agua");
  assert.equal(flowBaseFromPathname("/obras/1/operacion/agua/calidad", "calidad"), "/obras/1/operacion/agua");
});

test("flowBaseFromPathname on the resumen path only trims a trailing slash, never a real segment", () => {
  assert.equal(flowBaseFromPathname("/obras/1/operacion/agua", "resumen"), "/obras/1/operacion/agua");
  assert.equal(flowBaseFromPathname("/obras/1/operacion/agua/", "resumen"), "/obras/1/operacion/agua");
});

test("every flow domain in the router (energia, agua, combustibles, transporte, materiales, residuos, ruido, emisiones-atmosfericas, suelo) round-trips through base+section without cross-contaminating the domain segment", () => {
  const domains = ["energia", "agua", "combustibles", "transporte", "materiales", "residuos", "ruido", "emisiones-atmosfericas", "suelo"];
  for (const domain of domains) {
    for (const section of FLOW_SECTIONS) {
      const path = section === "resumen" ? `/obras/42/operacion/${domain}` : `/obras/42/operacion/${domain}/${section}`;
      assert.equal(sectionFromPathname(path), section);
      assert.equal(flowBaseFromPathname(path, section), `/obras/42/operacion/${domain}`);
    }
  }
});
