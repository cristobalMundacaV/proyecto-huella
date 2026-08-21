import {
    api,
} from "@/shared/services/api";


const base = (id) =>
    `/organizaciones/${encodeURIComponent(id)}`;


export const getActivityEligibility =
    async (
        organizationId,
        activityId,
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/actividades-operacionales/${activityId}/elegibilidad/`,
            )
        ).data;


export const calculateActivity =
    async (
        organizationId,
        activityId,
        payload = {},
    ) =>
        (
            await api.post(
                `${base(
                    organizationId,
                )}/actividades-operacionales/${activityId}/calcular/`,
                payload,
            )
        ).data;


export const getActivityCalculations =
    async (
        organizationId,
        activityId,
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/actividades-operacionales/${activityId}/calculos/`,
            )
        ).data;


export const getCalculation =
    async (
        organizationId,
        calculationId,
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/calculos/${calculationId}/`,
            )
        ).data;


export const getEnvironmentalImpacts =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/impactos-ambientales/`,
                { params },
            )
        ).data;


export const getIndicators =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/indicadores/`,
                { params },
            )
        ).data;


export const getIndicatorSeries =
    async (
        organizationId,
        indicatorId,
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/indicadores/${indicatorId}/serie/`,
            )
        ).data;


export const getBaselines =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId,
                )}/lineas-base/`,
                { params },
            )
        ).data;


export const buildBaseline =
    async (
        organizationId,
        indicatorId,
    ) =>
        (
            await api.post(
                `${base(
                    organizationId,
                )}/lineas-base/`,
                {
                    indicador:
                        indicatorId,
                },
            )
        ).data;