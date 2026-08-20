import { api } from "@/shared/services/api";

const base = (organizationId) => `/organizaciones/${encodeURIComponent(organizationId)}`;

export async function getWorkOperation(organizationId, workId) {
  const params = { obra: workId };
  const results = await Promise.allSettled([
    api.get(`${base(organizationId)}/flujos-ambientales/`, { params }),
    api.get(`${base(organizationId)}/puntos-ambientales/`, { params }),
    api.get(`${base(organizationId)}/viajes-operacionales/`, { params }),
    api.get(`${base(organizationId)}/viajes-operacionales/indicadores/`, { params }),
    api.get(`${base(organizationId)}/obras/${encodeURIComponent(workId)}/materiales/`),
    api.get(`${base(organizationId)}/eventos-materiales/`, { params }),
    api.get(
      `${base(organizationId)}/sensores/`,
      { params },
    ),
  ]);
  const resource = (result) => result.status === "fulfilled"
    ? { status: "ready", data: result.value.data }
    : { status: "error", data: null, error: result.reason?.response?.data?.detail || "No fue posible cargar la información." };
  const [
    records,
    points,
    journeys,
    transport,
    materials,
    materialEvents,
    sensors,
  ] = results.map(resource);

  return {
    records,
    points,
    journeys,
    transport,
    materials,
    materialEvents,
    sensors,
  };
}
