import assert from "node:assert/strict";
import test from "node:test";

import { resolveActiveOrganizationId, resolveOnboardingScreen } from "./organizationResolution.js";

const organization = (id) => ({ organizacion_id: id });

test("autoselecciona una organización sin preferencia persistida", () => {
  assert.equal(resolveActiveOrganizationId([organization("A")]), "A");
});

test("normaliza una preferencia válida cuando existe una organización", () => {
  assert.equal(resolveActiveOrganizationId([organization(7)], 7), "7");
});

test("reemplaza el tenant histórico por el único tenant autorizado", () => {
  assert.equal(resolveActiveOrganizationId([organization("B")], "A"), "B");
});

test("limpia una preferencia inválida cuando existen varias organizaciones", () => {
  assert.equal(resolveActiveOrganizationId([organization("B"), organization("C")], "A"), "");
});

test("conserva una preferencia autorizada entre varias organizaciones", () => {
  assert.equal(resolveActiveOrganizationId([organization("A"), organization("B")], "B"), "B");
});

test("no selecciona organización cuando no existen membresías", () => {
  assert.equal(resolveActiveOrganizationId([], "A"), "");
});

test("un error de organizaciones produce una pantalla de error visible", () => {
  assert.equal(resolveOnboardingScreen({ organizationLoading: false, organizationError: "fallo", activeOrganizationId: "", organizationCount: 0, onboardingStatus: "idle", hasState: false }), "organization-error");
});

test("un error de onboarding no se confunde con el loader", () => {
  assert.equal(resolveOnboardingScreen({ organizationLoading: false, organizationError: "", activeOrganizationId: "B", organizationCount: 1, onboardingStatus: "error", hasState: false }), "onboarding-error");
});
