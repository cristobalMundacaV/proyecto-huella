import { api } from "@/shared/services/api";

const base = (organizationId) =>
    `/organizaciones/${encodeURIComponent(organizationId)}`;

export const listOperationalMaterials = async (organizationId) =>
    (
        await api.get(
            `${base(organizationId)}/materiales-operacionales/`,
        )
    ).data;

export const createOperationalMaterial = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/materiales-operacionales/`,
            payload,
        )
    ).data;

export const getOperationalMaterial = async (
    organizationId,
    materialId,
) =>
    (
        await api.get(
            `${base(organizationId)}/materiales-operacionales/${encodeURIComponent(materialId)}/`,
        )
    ).data;

export const updateOperationalMaterial = async (
    organizationId,
    materialId,
    payload,
) =>
    (
        await api.patch(
            `${base(organizationId)}/materiales-operacionales/${encodeURIComponent(materialId)}/`,
            payload,
        )
    ).data;

export const listMaterialLots = async (
    organizationId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/lotes-materiales/`,
            { params },
        )
    ).data;

export const createMaterialLot = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/lotes-materiales/`,
            payload,
        )
    ).data;

export const listMaterialEvents = async (
    organizationId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/eventos-materiales/`,
            { params },
        )
    ).data;

export const createMaterialEvent = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/eventos-materiales/`,
            payload,
        )
    ).data;

export const getMaterialEvent = async (
    organizationId,
    eventId,
) =>
    (
        await api.get(
            `${base(organizationId)}/eventos-materiales/${encodeURIComponent(eventId)}/`,
        )
    ).data;

export const updateMaterialEvent = async (
    organizationId,
    eventId,
    payload,
) =>
    (
        await api.patch(
            `${base(organizationId)}/eventos-materiales/${encodeURIComponent(eventId)}/`,
            payload,
        )
    ).data;

export const getMaterialBalance = async (
    organizationId,
    materialId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/materiales-operacionales/${encodeURIComponent(materialId)}/balance/`,
            { params },
        )
    ).data;

export const getMaterialLineage = async (
    organizationId,
    materialId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/materiales-operacionales/${encodeURIComponent(materialId)}/lineage/`,
            { params },
        )
    ).data;

export const getMaterialIndicators = async (organizationId) =>
    (
        await api.get(
            `${base(organizationId)}/materiales-operacionales/indicadores/`,
        )
    ).data;