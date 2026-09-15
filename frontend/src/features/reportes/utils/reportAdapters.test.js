import assert from "node:assert/strict";
import test from "node:test";

import { buildComparativeInsights, buildEnvironmentalReport } from "./reportAdapters.js";

const impact = (overrides) => ({ unidad: "kgCO2e", categoria: "materiales", actividad_nombre: "Hormigón", timestamp: "2026-06-15", valor: 100, ...overrides });

test("comparison.available is false with fewer than two populated months", () => {
  const report = buildEnvironmentalReport([impact({ timestamp: "2026-06-15" })]);
  assert.equal(report.comparison.available, false);
  assert.equal(report.comparison.coverage, "single");
  assert.equal(report.comparison.topMover, null);
});

test("comparison.available is false with zero records", () => {
  const report = buildEnvironmentalReport([]);
  assert.equal(report.comparison.available, false);
  assert.equal(report.comparison.coverage, "none");
});

test("comparison compares only the two most recent populated months, not the whole timeline", () => {
  const impacts = [
    impact({ timestamp: "2026-04-10", valor: 500, actividad_nombre: "Viejo" }),
    impact({ timestamp: "2026-07-10", valor: 100, actividad_nombre: "A" }),
    impact({ timestamp: "2026-08-10", valor: 300, actividad_nombre: "A" }),
  ];
  const report = buildEnvironmentalReport(impacts);
  assert.equal(report.comparison.available, true);
  assert.equal(report.comparison.previousLabel, report.previous.label);
  assert.equal(report.comparison.latestLabel, report.latest.label);
  // topMover must reflect jul->aug (100->300), not abr->jul
  assert.equal(report.comparison.topMover.name, "A");
  assert.equal(report.comparison.topMover.change, 200);
});

test("each source row carries a delta between the latest and previous month only", () => {
  const impacts = [
    impact({ timestamp: "2026-07-10", valor: 100, actividad_nombre: "A" }),
    impact({ timestamp: "2026-08-10", valor: 150, actividad_nombre: "A" }),
    impact({ timestamp: "2026-08-10", valor: 50, actividad_nombre: "B" }),
  ];
  const report = buildEnvironmentalReport(impacts);
  const a = report.sources.find((row) => row.name === "A");
  const b = report.sources.find((row) => row.name === "B");
  assert.equal(a.delta, 50); // (150-100)/100 * 100
  assert.equal(b.delta, null); // new in the latest month, no previous base to divide by
});

test("a source with zero activity in both compared months reads as no change (0), not a fabricated percentage", () => {
  // three months so the source with data only in month 1 (neither latest nor previous) never appears in either month bucket
  const impacts = [
    impact({ timestamp: "2026-05-10", valor: 100, actividad_nombre: "Antiguo" }),
    impact({ timestamp: "2026-07-10", valor: 100, actividad_nombre: "Otro" }),
    impact({ timestamp: "2026-08-10", valor: 100, actividad_nombre: "Otro" }),
  ];
  const report = buildEnvironmentalReport(impacts);
  const antiguo = report.sources.find((row) => row.name === "Antiguo");
  assert.equal(antiguo.delta, 0);
});

test("topMover picks the largest absolute change, positive or negative", () => {
  const impacts = [
    impact({ timestamp: "2026-07-10", valor: 500, actividad_nombre: "Baja" }),
    impact({ timestamp: "2026-08-10", valor: 100, actividad_nombre: "Baja" }),
    impact({ timestamp: "2026-07-10", valor: 10, actividad_nombre: "Sube" }),
    impact({ timestamp: "2026-08-10", valor: 60, actividad_nombre: "Sube" }),
  ];
  const report = buildEnvironmentalReport(impacts);
  assert.equal(report.comparison.topMover.name, "Baja");
  assert.equal(report.comparison.topMover.change, -400);
});

test("buildComparativeInsights returns nothing invented when there is no comparison", () => {
  const report = buildEnvironmentalReport([impact({ timestamp: "2026-06-15" })]);
  const insights = buildComparativeInsights(report);
  assert.deepEqual(insights, []);
});

test("buildComparativeInsights surfaces the principal alza only when the top mover actually rose", () => {
  const impacts = [
    impact({ timestamp: "2026-07-10", valor: 100, actividad_nombre: "A" }),
    impact({ timestamp: "2026-08-10", valor: 400, actividad_nombre: "A" }),
  ];
  const report = buildEnvironmentalReport(impacts);
  const insights = buildComparativeInsights(report);
  assert.ok(insights.some((item) => item.id === "principal-alza"));
});

test("buildComparativeInsights never returns more than 3 items", () => {
  const impacts = [
    impact({ timestamp: "2026-07-10", valor: 100, actividad_nombre: "A", unidad: "kg" }),
    impact({ timestamp: "2026-07-10", valor: 100, actividad_nombre: "A" }),
    impact({ timestamp: "2026-08-10", valor: 400, actividad_nombre: "A" }),
  ];
  const report = buildEnvironmentalReport(impacts);
  const insights = buildComparativeInsights(report);
  assert.ok(insights.length <= 3);
});

test("buildComparativeInsights flags insufficient coverage from real excluded records only", () => {
  const impacts = [impact({ timestamp: "2026-06-15", unidad: "kg" }), impact({ timestamp: "2026-06-16" })];
  const report = buildEnvironmentalReport(impacts);
  assert.equal(report.excludedRecords, 1);
  const insights = buildComparativeInsights(report);
  assert.ok(insights.some((item) => item.id === "cobertura-insuficiente"));
});
