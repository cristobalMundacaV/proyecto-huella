import { api } from "@/shared/services/api";
import { getOrganizationWorks } from "@/features/obras/services/workspaceApi";

const rows = (value) => (Array.isArray(value) ? value : value?.results || []);

export async function getInicioOverview(organizationId) {
  const works = await getOrganizationWorks(organizationId);
  const [problemsResult, evidenceResult, ...contexts] = await Promise.allSettled([
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/problematicas/`).then((result) => rows(result.data)),
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/evidencias/`).then((result) => rows(result.data)),
    ...works.map((work) => api.get(`/organizaciones/${encodeURIComponent(organizationId)}/obras/${work.id || work.obra_id}/contexto/`)),
  ]);
  return {
    works,
    problems: problemsResult.status === "fulfilled" ? problemsResult.value : [],
    evidence: evidenceResult.status === "fulfilled" ? evidenceResult.value : [],
    workContexts: contexts.map((result) => result.status === "fulfilled" ? result.value.data : null).filter(Boolean),
    resourceErrors: { problems: problemsResult.status === "rejected", evidence: evidenceResult.status === "rejected" },
  };
}
