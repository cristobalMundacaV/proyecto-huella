import { api } from "@/shared/services/api";

const base = (organizationId) =>
    `/organizaciones/${encodeURIComponent(organizationId)}`;

export const listRoutes = async (organizationId) =>
    (
        await api.get(
            `${base(organizationId)}/rutas-operacionales/`,
        )
    ).data;

export const createRoute = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/rutas-operacionales/`,
            payload,
        )
    ).data;

export const listJourneys = async (
    organizationId,
    workId = null,
) =>
    (
        await api.get(
            `${base(organizationId)}/viajes-operacionales/`,
            workId
                ? { params: { obra: workId } }
                : undefined,
        )
    ).data;

export const createJourney = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/viajes-operacionales/`,
            payload,
        )
    ).data;

export const getJourney = async (
    organizationId,
    journeyId,
) =>
    (
        await api.get(
            `${base(organizationId)}/viajes-operacionales/${encodeURIComponent(journeyId)}/`,
        )
    ).data;

export const updateJourney = async (
    organizationId,
    journeyId,
    payload,
) =>
    (
        await api.patch(
            `${base(organizationId)}/viajes-operacionales/${encodeURIComponent(journeyId)}/`,
            payload,
        )
    ).data;

export const getJourneyIndicators = async (
    organizationId,
    workId = null,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/viajes-operacionales/indicadores/`,
            {
                params: {
                    ...params,
                    ...(workId ? { obra: workId } : {}),
                },
            },
        )
    ).data;