import { api } from "@/shared/services/api";

const base = (id) => `/organizaciones/${encodeURIComponent(id)}`;
export const getDiagnostico = async (id, workId = null) =>
    (
        await api.get(
            `${base(id)}/diagnostico-ambiental/`,
            workId
                ? { params: { obra: workId } }
                : undefined,
        )
    ).data;

export const saveDiagnostico = async (
    id,
    data,
    exists,
    workId = null,
) =>
    (
        await api[exists ? "patch" : "post"](
            `${base(id)}/diagnostico-ambiental/`,
            workId
                ? {
                    ...data,
                    obra: workId,
                }
                : data,
        )
    ).data;
export const getCapacidades = async (id) => (await api.get(`${base(id)}/capacidades-ambientales/`)).data;
export const updateCapacidad = async (id, capacidadId, data) => (await api.patch(`${base(id)}/capacidades-ambientales/${capacidadId}/`, data)).data;
export const getUnidades = async (id) => (await api.get(`${base(id)}/unidades-operacionales/`)).data;
export const createUnidad = async (id, data) => (await api.post(`${base(id)}/unidades-operacionales/`, data)).data;
export const getProcesos = async (id) => (await api.get(`${base(id)}/procesos-operacionales/`)).data;
export const createProceso = async (id, data) => (await api.post(`${base(id)}/procesos-operacionales/`, data)).data;
export const getPreparacion = async (id) => (await api.get(`${base(id)}/preparacion-ambiental/`)).data;

export const updateWorkApplicability = async (
    organizationId,
    workId,
    capabilityId,
    estado,
) =>
    (
        await api.patch(
            `${base(organizationId)}/obras/${encodeURIComponent(workId)}/aplicabilidades/${encodeURIComponent(capabilityId)}/`,
            { estado },
        )
    ).data;