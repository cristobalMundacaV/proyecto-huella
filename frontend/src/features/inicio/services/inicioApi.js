import { api } from "@/shared/services/api";
import { getOrganizationWorks } from "@/features/obras/services/workspaceApi";

const rows = (value) => (Array.isArray(value) ? value : value?.results || []);

export async function getInicioOverview(organizationId) {
  const [works, problems, evidence] = await Promise.all([
    getOrganizationWorks(organizationId),
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/problematicas/`).then((result) => rows(result.data)),
    api.get(`/organizaciones/${encodeURIComponent(organizationId)}/evidencias/`).then((result) => rows(result.data)),
  ]);
  const contexts = await Promise.allSettled(
    works.map((work) => api.get(`/organizaciones/${encodeURIComponent(organizationId)}/obras/${work.id || work.obra_id}/contexto/`)),
  );
  return {
    works,
    problems,
    evidence,
    workContexts: contexts.map((result) => result.status === "fulfilled" ? result.value.data : null).filter(Boolean),
  };
}
