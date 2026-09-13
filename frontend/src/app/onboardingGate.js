/** Whether an organization is "really new" (should see the onboarding
 * "Tu organización está lista" screen) instead of the executive dashboard.
 *
 * Deliberately based on `obras_count` — never `registros_count`, which only
 * counts the legacy `RegistroEmision` model and is 0 for any tenant built
 * entirely on the modern v2 stack (materials/activities/calculations),
 * even one with real obras, dashboards and reports. A tenant with at least
 * one obra always has real operational content, so it always gets the
 * dashboard — see docs/product onboarding gate rules.
 */
export function isNewTenant(organization) {
  return Number(organization?.obras_count || 0) === 0;
}

/** Whether an existing (non-new) tenant is missing the structural
 * side-effects of the onboarding flow (areas/capacidades) — shown as a
 * "Configuración incompleta" banner on the dashboard rather than a second
 * onboarding screen. `onboarding_completado` alone is not reliable (a
 * seeded/legacy tenant can have it hardcoded true without ever having
 * created areas or capacidades), so this only reflects what the backend
 * explicitly reports having repaired/pending, when available. */
export function hasIncompleteConfiguration(organization) {
  return organization?.onboarding_completado === false;
}
