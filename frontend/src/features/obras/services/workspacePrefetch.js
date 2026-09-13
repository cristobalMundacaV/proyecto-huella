import { getWorkWorkspace } from "./workspaceApi";
import { getObraDashboard } from "./obraDashboardApi";

/** Lightweight, module-level prefetch cache — deliberately NOT a query
 * library (no re-architecture): the context selector fires this on
 * hover/focus of an obra option, and `ObraWorkspaceLayout` reuses the same
 * in-flight/resolved promises instead of firing a second request when the
 * user actually clicks through shortly after. Entries expire quickly so a
 * stale hover from minutes ago is never silently reused. */
const TTL_MS = 20000;
const cache = new Map();

function key(organizationId, obraId) {
  return `${organizationId}:${obraId}`;
}

export function prefetchWork(organizationId, obraId, { withDashboard = true } = {}) {
  if (!organizationId || !obraId) return;
  const cacheKey = key(organizationId, obraId);
  const existing = cache.get(cacheKey);
  if (existing && existing.expiresAt > Date.now()) return;
  cache.set(cacheKey, {
    workspace: getWorkWorkspace(organizationId, obraId),
    dashboard: withDashboard ? getObraDashboard(organizationId, obraId, { relative_months: 3 }) : null,
    expiresAt: Date.now() + TTL_MS,
  });
}

export function consumePrefetchedWork(organizationId, obraId) {
  const cacheKey = key(organizationId, obraId);
  const entry = cache.get(cacheKey);
  if (!entry || entry.expiresAt <= Date.now()) return null;
  cache.delete(cacheKey);
  return entry;
}
