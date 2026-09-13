import { api } from "@/shared/services/api";
import { getOrganizationWorks } from "@/features/obras/services/workspaceApi";
import { getObraDashboard } from "@/features/obras/services/obraDashboardApi";

const rows = (value) => (Array.isArray(value) ? value : value?.results || []);

export async function getInicioOverview(organizationId) {
  const works = await getOrganizationWorks(organizationId);
  const [problemsResult, evidenceResult, ...workResults] = await Promise.allSettled([
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/problematicas/`).then((result) => rows(result.data)),
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/evidencias/`).then((result) => rows(result.data)),
    ...works.map((work) => api.get(`/organizaciones/${encodeURIComponent(organizationId)}/obras/${work.id || work.obra_id}/contexto/`)),
    ...works.map((work) => getObraDashboard(organizationId, work.id || work.obra_id, { relative_months: 3 })),
  ]);
  const contexts = workResults.slice(0, works.length);
  const dashboards = workResults.slice(works.length);
  const workContextErrors = contexts.flatMap((result, index) =>
    result.status === "rejected" ? [String(works[index].id || works[index].obra_id)] : [],
  );
  return {
    works,
    problems: problemsResult.status === "fulfilled" ? problemsResult.value : [],
    evidence: evidenceResult.status === "fulfilled" ? evidenceResult.value : [],
    workContexts: contexts.map((result) => result.status === "fulfilled" ? result.value.data : null).filter(Boolean),
    workDashboards: dashboards.map((result, index) => result.status === "fulfilled" ? result.value : { obra_id: works[index].id || works[index].obra_id, unavailable: true }),
    workContextErrors,
    resourceErrors: { problems: problemsResult.status === "rejected", evidence: evidenceResult.status === "rejected" },
  };
}
