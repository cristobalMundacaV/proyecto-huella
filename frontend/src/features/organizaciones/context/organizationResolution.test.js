import assert from "node:assert/strict";
import test from "node:test";

import { organizationDestination, resolveActiveOrganizationId, resolveOnboardingScreen, resolveOrganizationAccess } from "./organizationResolution.js";

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

test("la hidratación pendiente nunca se interpreta como usuario sin organización", () => {
  assert.equal(resolveOnboardingScreen({ organizationLoading: false, organizationsResolved: false, organizationError: "", activeOrganizationId: "", organizationCount: 0, onboardingStatus: "idle", hasState: false }), "resolving-organization");
});

test("solo muestra estado vacío después de completar la resolución", () => {
  assert.equal(resolveOnboardingScreen({ organizationLoading: false, organizationsResolved: true, organizationError: "", activeOrganizationId: "", organizationCount: 0, onboardingStatus: "idle", hasState: false }), "no-organization");
});

test("una organización única recupera el tenant aunque la preferencia haya expirado", () => {
  assert.equal(resolveActiveOrganizationId([organization("tenant-vigente")], "tenant-antiguo"), "tenant-vigente");
});

test("una organización resuelta nunca requiere selector", () => {
  const organizations = [organization("A")];
  assert.equal(resolveOrganizationAccess({ resolving: false, error: "", organizations, activeOrganization: organizations[0] }), "ready");
});

test("dos organizaciones sin activa requieren una decisión real", () => {
  assert.equal(resolveOrganizationAccess({ resolving: false, error: "", organizations: [organization("A"), organization("B")], activeOrganization: null }), "selection-required");
});

test("dos organizaciones conservan una activa válida sin mostrar selector", () => {
  const organizations = [organization("A"), organization("B")];
  assert.equal(resolveOrganizationAccess({ resolving: false, error: "", organizations, activeOrganization: organizations[1] }), "ready");
});

test("cero organizaciones produce un estado explícito", () => {
  assert.equal(resolveOrganizationAccess({ resolving: false, error: "", organizations: [], activeOrganization: null }), "no-organization");
});

test("la resolución pendiente evita un selector transitorio", () => {
  assert.equal(resolveOrganizationAccess({ resolving: true, error: "", organizations: [], activeOrganization: null }), "resolving");
});

test("la máquina explícita solo deja loading mientras la resolución está activa", () => {
  assert.equal(resolveOrganizationAccess({ status: "idle", organizations: [], activeOrganization: null }), "resolving");
  assert.equal(resolveOrganizationAccess({ status: "loading", organizations: [], activeOrganization: null }), "resolving");
  assert.equal(resolveOrganizationAccess({ status: "empty", organizations: [], activeOrganization: null }), "no-organization");
  assert.equal(resolveOrganizationAccess({ status: "error", organizations: [], activeOrganization: null }), "error");
  assert.equal(resolveOrganizationAccess({ status: "selection_required", organizations: [organization("A"), organization("B")], activeOrganization: null }), "selection-required");
  assert.equal(resolveOrganizationAccess({ status: "ready", organizations: [organization("A")], activeOrganization: organization("A") }), "ready");
});

test("el destino respeta onboarding pendiente o completado", () => {
  assert.equal(organizationDestination({ onboarding_completado: false }), "/onboarding");
  assert.equal(organizationDestination({ onboarding_completado: true }), "/inicio");
});
