import { api } from "@/shared/services/api";

const base = (organizationId) =>
    `/organizaciones/${encodeURIComponent(organizationId)}`;

export const listEnvironmentalPoints = async (
    organizationId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/puntos-ambientales/`,
            { params },
        )
    ).data;

export const createEnvironmentalPoint = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/puntos-ambientales/`,
            payload,
        )
    ).data;

export const listSectorRecords = async (
    organizationId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/flujos-ambientales/`,
            { params },
        )
    ).data;

export const createSectorRecord = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/flujos-ambientales/`,
            payload,
        )
    ).data;

export const getSectorRecord = async (
    organizationId,
    recordId,
) =>
    (
        await api.get(
            `${base(organizationId)}/flujos-ambientales/${encodeURIComponent(recordId)}/`,
        )
    ).data;

export const updateSectorRecord = async (
    organizationId,
    recordId,
    payload,
) =>
    (
        await api.patch(
            `${base(organizationId)}/flujos-ambientales/${encodeURIComponent(recordId)}/`,
            payload,
        )
    ).data;

export const getSectorIndicators = async (
    organizationId,
    params = {},
) =>
    (
        await api.get(
            `${base(organizationId)}/flujos-ambientales/indicadores/`,
            { params },
        )
    ).data;

export const createManualSectorRecord = async (
    organizationId,
    payload,
) =>
    (
        await api.post(
            `${base(organizationId)}/flujos-ambientales/registro-manual/`,
            payload,
            { skipOperationalWorkspace: true },
        )
    ).data;

export const listEvidenceTypes = async (domain) =>
    (
        await api.get(
            "/tipos-evidencia/",
            { params: { dominio: domain } },
        )
    ).data;

export const listWasteTypes = async () =>
    (
        await api.get("/tipos-residuo/")
    ).data;

export const processEvidenceVersion = async (organizationId, evidenceId, versionId) =>
    (
        await api.post(
            `${base(organizationId)}/evidencias/${encodeURIComponent(evidenceId)}/versiones/${encodeURIComponent(versionId)}/procesar/`,
            {},
        )
    ).data;
