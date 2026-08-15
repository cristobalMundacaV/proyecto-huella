import { api } from "@/shared/services/api";

const rows = (value) => (Array.isArray(value) ? value : value?.results || []);
const base = (organizationId, workId) =>
  `/organizaciones/${encodeURIComponent(organizationId)}/obras/${encodeURIComponent(workId)}`;

export async function getOrganizationWorks(organizationId) {
  return rows((await api.get(`/organizaciones/${encodeURIComponent(organizationId)}/obras/`)).data);
}

export async function createOrganizationWork(organizationId, payload) {
  return (await api.post(`/organizaciones/${encodeURIComponent(organizationId)}/obras/`, {
    ...payload,
    organizacion_id: organizationId,
  })).data;
}

export async function getWorkWorkspace(organizationId, routeId) {
  const works = await getOrganizationWorks(organizationId);
  const work = works.find((item) =>
    [item.id, item.obra_id, item.codigo_obra].some((value) => String(value) === String(routeId)),
  );
  if (!work) {
    const error = new Error("No se encontró la obra");
    error.response = { status: 404 };
    throw error;
  }
  const workId = work.id || work.obra_id;
  const [context, timeline, indicators] = await Promise.all([
    api.get(`${base(organizationId, workId)}/contexto/`),
    api.get(`${base(organizationId, workId)}/timeline/`),
    api.get(`${base(organizationId, workId)}/indicadores/`),
  ]);
  return { obra: { ...work, ...context.data?.obra }, context: context.data, timeline: timeline.data, indicators: indicators.data };
}
