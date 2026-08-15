import { api } from "@/shared/services/api";

const base = (organizationId) => `/organizaciones/${encodeURIComponent(organizationId)}`;

export async function getWorkOperation(organizationId, workId) {
  const params = { obra: workId };
  const [records, points, journeys, transport, materials, materialEvents] = await Promise.all([
    api.get(`${base(organizationId)}/flujos-ambientales/`, { params }),
    api.get(`${base(organizationId)}/puntos-ambientales/`, { params }),
    api.get(`${base(organizationId)}/viajes-operacionales/`, { params }),
    api.get(`${base(organizationId)}/viajes-operacionales/indicadores/`, { params }),
    api.get(`${base(organizationId)}/obras/${encodeURIComponent(workId)}/materiales/`),
    api.get(`${base(organizationId)}/eventos-materiales/`, { params }),
  ]);
  return {
    records: records.data,
    points: points.data,
    journeys: journeys.data,
    transport: transport.data,
    materials: materials.data,
    materialEvents: materialEvents.data,
  };
}
