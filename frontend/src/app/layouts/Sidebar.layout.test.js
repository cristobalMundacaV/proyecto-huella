import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./Sidebar.jsx", import.meta.url), "utf8");

test("the obra subnav sits in the SAME scroll region as the primary nav, not a separate flex-pushed block", () => {
  // The regression: GeneralNavigation's own <nav> carried flex-1/overflow,
  // so it grew to fill the aside and pushed ObraActiveSubnav (its DOM
  // sibling) to the bottom behind a huge empty gap. The fix moves
  // flex-1/overflow to ONE wrapper containing both.
  const wrapperStart = source.indexOf('<div className="min-h-0 flex-1 overflow-y-auto');
  assert.ok(wrapperStart > -1, "there must be exactly one flex-1/overflow wrapper around the nav content");

  const generalNavPosition = source.indexOf("<GeneralNavigation", wrapperStart);
  const obraSubnavPosition = source.indexOf("<ObraActiveSubnav", wrapperStart);
  const wrapperClose = source.indexOf("</aside>", wrapperStart);

  assert.ok(generalNavPosition > wrapperStart, "GeneralNavigation must be inside the shared scroll wrapper");
  assert.ok(obraSubnavPosition > generalNavPosition, "ObraActiveSubnav must render immediately after GeneralNavigation, in the same flow");
  assert.ok(obraSubnavPosition < wrapperClose, "ObraActiveSubnav must be inside the same wrapper, not a sibling of <aside>");
});

test("GeneralNavigation's own <nav> no longer carries its own flex-1/overflow (that caused the bug)", () => {
  const navFunctionStart = source.indexOf("function GeneralNavigation");
  const navFunctionBody = source.slice(navFunctionStart, navFunctionStart + 700);
  assert.ok(!navFunctionBody.includes("flex-1"), "flex-1 must live on the shared wrapper, not on GeneralNavigation's own <nav>");
  assert.ok(!navFunctionBody.includes("overflow-y-auto"), "scroll must live on the shared wrapper, not on GeneralNavigation's own <nav>");
});

test("no stray push-to-bottom pattern (mt-auto / justify-between) exists in the sidebar", () => {
  assert.equal(source.includes("mt-auto"), false);
  assert.equal(source.includes("justify-between"), false);
});
