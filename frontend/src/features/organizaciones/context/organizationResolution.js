export function resolveActiveOrganizationId(organizations, persistedId = "") {
  const normalized = Array.isArray(organizations) ? organizations : [];

  if (normalized.length === 0) return "";
  if (normalized.length === 1) return String(normalized[0].organizacion_id);

  const persisted = String(persistedId || "");
  return normalized.some(
    (organization) => String(organization.organizacion_id) === persisted,
  )
    ? persisted
    : "";
}

export function resolveOrganizationAccess({ resolving, error, organizations, activeOrganization }) {
  if (resolving) return "resolving";
  if (error) return "error";
  if (!organizations.length) return "no-organization";
  if (activeOrganization) return "ready";
  return organizations.length > 1 ? "selection-required" : "resolving";
}

export function organizationDestination(organization, fallback = "/inicio") {
  return organization?.onboarding_completado === false ? "/onboarding" : fallback;
}

export function resolveOnboardingScreen({ organizationLoading, organizationsResolved = true, organizationError, activeOrganizationId, organizationCount, onboardingStatus, hasState }) {
  if (organizationLoading || !organizationsResolved) return "resolving-organization";
  if (organizationError) return "organization-error";
  if (!activeOrganizationId && organizationCount > 1) return "organization-selector";
  if (!activeOrganizationId) return "no-organization";
  if (onboardingStatus === "error") return "onboarding-error";
  if (onboardingStatus === "idle" || onboardingStatus === "loading") return "loading-onboarding";
  return hasState ? "ready" : "onboarding-error";
}
