import assert from "node:assert/strict";
import test from "node:test";

import { hasIncompleteConfiguration, isNewTenant } from "./onboardingGate.js";

test("a tenant with zero obras is new, regardless of legacy registros_count", () => {
  assert.equal(isNewTenant({ obras_count: 0, registros_count: 0 }), true);
  assert.equal(isNewTenant(undefined), true);
});

test("a tenant with at least one obra is never treated as new, even with 0 legacy registros", () => {
  assert.equal(isNewTenant({ obras_count: 2, registros_count: 0 }), false);
  assert.equal(isNewTenant({ obras_count: 1, registros_count: 500 }), false);
});

test("incomplete configuration banner reflects onboarding_completado explicitly, not its absence", () => {
  assert.equal(hasIncompleteConfiguration({ onboarding_completado: false }), true);
  assert.equal(hasIncompleteConfiguration({ onboarding_completado: true }), false);
  assert.equal(hasIncompleteConfiguration({}), false);
  assert.equal(hasIncompleteConfiguration(undefined), false);
});
