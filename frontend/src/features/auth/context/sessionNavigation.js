export const SESSION_NAVIGATION_KEYS = [
  "carbono_zero.activeOrganizacionId",
  "carbono_zero.operationalWorkspaceId",
];

export function clearSessionNavigationContext(storage = globalThis.window?.localStorage) {
  if (!storage) return;
  SESSION_NAVIGATION_KEYS.forEach((key) => storage.removeItem(key));
}
