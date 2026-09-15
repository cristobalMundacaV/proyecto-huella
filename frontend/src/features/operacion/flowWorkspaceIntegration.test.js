import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), "utf8");

const shell = read("./components/OperationDomainShell.jsx");
const sectorDomainPage = read("./pages/SectorDomainPage.jsx");
const materialsPage = read("./pages/MaterialsPage.jsx");
const transportPage = read("./pages/TransportPage.jsx");
const wastePage = read("./pages/WastePage.jsx");

test("OperationDomainShell renders the flow's internal subnav — every flow workspace gets it for free", () => {
  assert.match(shell, /<FlowWorkspaceNav\s*\/>/);
});

test("every flow page reads the active section instead of assuming resumen", () => {
  for (const source of [sectorDomainPage, materialsPage, transportPage]) {
    assert.match(source, /useFlowSection\(\)/);
  }
});

test("SectorDomainPage never leaves tendencias/calidad/sensores blank when the flow is not applicable or pending", () => {
  for (const section of ["tendencias", "calidad", "sensores"]) {
    assert.match(sectorDomainPage, new RegExp(`section === "${section}" && noApplicable`), `${section} must handle noApplicable`);
    assert.match(sectorDomainPage, new RegExp(`section === "${section}" && unresolved`), `${section} must handle unresolved`);
  }
});

test("MaterialsPage never leaves tendencias/calidad/sensores blank when materiales is not applicable or pending", () => {
  for (const section of ["tendencias", "calidad", "sensores"]) {
    assert.match(materialsPage, new RegExp(`section === "${section}" && noApplicable`), `${section} must handle noApplicable`);
    assert.match(materialsPage, new RegExp(`section === "${section}" && unresolved`), `${section} must handle unresolved`);
  }
});

test("TransportPage never leaves tendencias/calidad/sensores blank when transporte is not applicable or pending", () => {
  for (const section of ["tendencias", "calidad", "sensores"]) {
    assert.match(transportPage, new RegExp(`section === "${section}" && noApplicable`), `${section} must handle noApplicable`);
    assert.match(transportPage, new RegExp(`section === "${section}" && unresolved`), `${section} must handle unresolved`);
  }
});

test("Registros never got duplicated into Resumen for any of the four flow pages", () => {
  // the big table/list block must only render under section === "registros"
  assert.match(sectorDomainPage, /section === "registros" && \(noApplicable/);
  assert.match(materialsPage, /section === "registros" && \(noApplicable/);
  assert.match(transportPage, /section === "registros" && \(noApplicable/);
});

test("Sensores and Calidad panels are gated to their own section, not shown on every tab", () => {
  for (const source of [sectorDomainPage, materialsPage, transportPage]) {
    assert.match(source, /section === "sensores" && !noApplicable && !unresolved && <DomainSensorsPanel/);
    assert.match(source, /section === "calidad" && !noApplicable && !unresolved/);
  }
});

test("FlowQuickRead only appears in Resumen, never duplicated across other sections", () => {
  for (const source of [sectorDomainPage, materialsPage, transportPage]) {
    const occurrences = source.match(/<FlowQuickRead/g) || [];
    assert.equal(occurrences.length, 1, "FlowQuickRead should be rendered exactly once");
    assert.match(source, /section === "resumen"[^}]*<FlowQuickRead|section === "resumen" &&\s*<FlowQuickRead/s);
  }
});

test("WastePage delegates residuos' own applicability handling to SectorDomainPage instead of duplicating it", () => {
  assert.match(wastePage, /<SectorDomainPage domain="residuos"\s*\/>/);
  assert.equal(wastePage.includes("noApplicable"), false, "WastePage's own blocks are supplementary and must not re-implement applicability gating");
});

test("legacy flow routes (no :section) are preserved for every domain — no deep-link-only regression", () => {
  const router = read("../../app/router/router.jsx");
  for (const domain of ["energia", "agua", "combustibles", "transporte", "materiales", "residuos", "ruido", "emisiones-atmosfericas", "suelo"]) {
    assert.match(router, new RegExp(`<Route path="operacion/${domain}" element=`));
  }
});
