import {
    api,
} from "@/shared/services/api";

const base = (id) =>
    `/organizaciones/${encodeURIComponent(id)}`;

export const getSensors = async (
    id,
    params = {},
) =>
    (
        await api.get(
            `${base(id)}/sensores/`,
            { params },
        )
    ).data;

export const getSensor = async (
    id,
    sensorId,
) =>
    (
        await api.get(
            `${base(id)}/sensores/${sensorId}/`,
        )
    ).data;

export const createSensor = async (
    id,
    data,
) =>
    (
        await api.post(
            `${base(id)}/sensores/`,
            data,
        )
    ).data;

export const createInstallation = async (
    id,
    sensorId,
    data,
) =>
    (
        await api.post(
            `${base(id)}/sensores/${sensorId}/instalaciones/`,
            data,
        )
    ).data;

export const createCalibration = async (
    id,
    sensorId,
    data,
) =>
    (
        await api.post(
            `${base(id)}/sensores/${sensorId}/calibraciones/`,
            data,
        )
    ).data;

export const createReading = async (
    id,
    sensorId,
    data,
) =>
    (
        await api.post(
            `${base(id)}/sensores/${sensorId}/lecturas/`,
            data,
        )
    ).data;