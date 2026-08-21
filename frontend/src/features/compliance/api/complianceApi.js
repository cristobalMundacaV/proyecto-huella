import {
    api,
} from "@/shared/services/api";


const base = (id) =>
    `/organizaciones/${encodeURIComponent(id)}`;


export const getComplianceSummary =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId
                )}/cumplimiento-ambiental/resumen/`,
                {
                    params,
                },
            )
        ).data;


export const getComplianceDocuments =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId
                )}/documentos-ambientales/`,
                {
                    params,
                },
            )
        ).data;


export const getComplianceAlerts =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId
                )}/alertas-cumplimiento/`,
                {
                    params,
                },
            )
        ).data;


export const getEnvironmentalVariables =
    async (
        organizationId,
        params = {},
    ) =>
        (
            await api.get(
                `${base(
                    organizationId
                )}/variables-ambientales/`,
                {
                    params,
                },
            )
        ).data;