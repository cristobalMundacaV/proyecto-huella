import { api } from "@/shared/services/api";
import { getOrganizationWorks } from "@/features/obras/services/workspaceApi";

const rows = (value) => (Array.isArray(value) ? value : value?.results || []);

/** Raw org-level rows (problems, evidence, per-work context) used for the
 * "Requiere tu atención" priorities list. Aggregated environmental KPIs
 * (huella, riesgo, readiness) come from the single `dashboard-portafolio`
 * motor via `getOrganizationDashboard` — never recomputed here from a loop
 * over each obra's own dashboard. */
export async function getInicioOverview(organizationId) {
  const works = await getOrganizationWorks(organizationId);
  const [problemsResult, evidenceResult, ...contexts] = await Promise.allSettled([
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/problematicas/`).then((result) => rows(result.data)),
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/evidencias/`).then((result) => rows(result.data)),
    ...works.map((work) => api.get(`/organizaciones/${encodeURIComponent(organizationId)}/obras/${work.id || work.obra_id}/contexto/`)),
  ]);
  const workContextErrors = contexts.flatMap((result, index) =>
    result.status === "rejected" ? [String(works[index].id || works[index].obra_id)] : [],
  );
  return {
    works,
    problems: problemsResult.status === "fulfilled" ? problemsResult.value : [],
    evidence: evidenceResult.status === "fulfilled" ? evidenceResult.value : [],
    workContexts: contexts.map((result) => result.status === "fulfilled" ? result.value.data : null).filter(Boolean),
    workContextErrors,
    resourceErrors: { problems: problemsResult.status === "rejected", evidence: evidenceResult.status === "rejected" },
  };
}
