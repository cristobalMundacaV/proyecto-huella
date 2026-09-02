import { api } from "@/shared/services/api";

const base = (organizationId) =>
    `/organizaciones/${encodeURIComponent(organizationId)}`;

export const listDataSources = async (
    organizationId,
    domain,
) =>
    (
        await api.get(
            `${base(organizationId)}/fuentes-datos/`,
            { params: domain ? { dominio: domain } : {} },
        )
    ).data;

export const createDataSource = async (
    organizationId,
    payload,
    domain,
) =>
    (
        await api.post(
            `${base(organizationId)}/fuentes-datos/`,
            payload,
            { params: domain ? { dominio: domain } : {} },
        )
    ).data;

export const createOperationalActivity = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/actividades-operacionales/`,
            payload,
        )
    ).data;
