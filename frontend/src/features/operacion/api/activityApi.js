import { api } from "@/shared/services/api";

const base = (organizationId) =>
    `/organizaciones/${encodeURIComponent(organizationId)}`;

export const listDataSources = async (
    organizationId,
) =>
    (
        await api.get(
            `${base(organizationId)}/fuentes-datos/`,
        )
    ).data;

export const createDataSource = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/fuentes-datos/`,
            payload,
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