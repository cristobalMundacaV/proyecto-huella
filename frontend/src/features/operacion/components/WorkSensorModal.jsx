import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    getAssets,
} from "@/features/activos/api/assetsApi";

import {
    createSensor,
} from "@/features/sensores/api/sensorsApi";

import {
    Button,
    Input,
    Modal,
    Select,
} from "@/shared/ui";

const SENSOR_TYPE_BY_DOMAIN = {
    energia: "energia",
    agua: "agua",
    combustibles: "combustible",
    transporte: "gps",
    materiales: "mixto",
    residuos: "ambiente",
    ruido: "ambiente",
    "hidrica-suelo": "ambiente",
};

const initialForm = {
    dispositivo_id: "",
    nombre: "",
    activo_operacional: "",
    punto_ambiental: "",
    ubicacion: "",
};

export default function WorkSensorModal({
    open,
    onClose,
    organizationId,
    workId,
    domain,
    points = [],
    onCreated,
}) {
    const [form, setForm] =
        useState(initialForm);

    const [assets, setAssets] =
        useState([]);

    const [saving, setSaving] =
        useState(false);

    const [error, setError] =
        useState("");

    useEffect(() => {
        if (!open) {
            return;
        }

        setForm(initialForm);
        setError("");

        getAssets(
            organizationId,
        )
            .then((data) => {
                setAssets(
                    Array.isArray(data)
                        ? data
                        : data?.results || [],
                );
            })
            .catch(() => {
                setAssets([]);
            });
    }, [
        open,
        organizationId,
    ]);

    const canSubmit =
        useMemo(
            () =>
                Boolean(
                    form.dispositivo_id.trim() &&
                    form.nombre.trim(),
                ),
            [
                form.dispositivo_id,
                form.nombre,
            ],
        );

    async function submit(event) {
        event.preventDefault();

        if (!canSubmit) {
            return;
        }

        setSaving(true);
        setError("");

        try {
            await createSensor(
                organizationId,
                {
                    dispositivo_id:
                        form.dispositivo_id.trim(),
                    nombre:
                        form.nombre.trim(),
                    tipo_sensor:
                        SENSOR_TYPE_BY_DOMAIN[
                        domain
                        ] || "mixto",
                    estado:
                        "operativo",
                    obra:
                        workId,
                    ambito_operacional:
                        domain,
                    punto_ambiental:
                        form.punto_ambiental
                            ? Number(
                                form.punto_ambiental,
                            )
                            : null,
                    activo_operacional:
                        form.activo_operacional
                            ? Number(
                                form.activo_operacional,
                            )
                            : null,
                    ubicacion:
                        form.ubicacion.trim(),
                },
            );

            onClose();
            await onCreated?.();
        } catch (requestError) {
            setError(
                requestError.response?.data
                    ?.punto_ambiental?.[0] ||
                requestError.response?.data
                    ?.dispositivo_id?.[0] ||
                requestError.response?.data
                    ?.detail ||
                "No fue posible vincular el sensor.",
            );
        } finally {
            setSaving(false);
        }
    }

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Vincular sensor"
            description="El sensor quedará asociado a esta obra y ámbito operacional."
        >
            <form
                className="space-y-4"
                onSubmit={submit}
            >
                <Input
                    required
                    label="Identificador del dispositivo"
                    value={
                        form.dispositivo_id
                    }
                    onChange={(event) =>
                        setForm(
                            (current) => ({
                                ...current,
                                dispositivo_id:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                />

                <Input
                    required
                    label="Nombre"
                    value={form.nombre}
                    onChange={(event) =>
                        setForm(
                            (current) => ({
                                ...current,
                                nombre:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                />

                <Select
                    label="Punto ambiental"
                    value={
                        form.punto_ambiental
                    }
                    onChange={(event) =>
                        setForm(
                            (current) => ({
                                ...current,
                                punto_ambiental:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                >
                    <option value="">
                        Sin punto específico
                    </option>

                    {points.map(
                        (point) => (
                            <option
                                key={
                                    point.id
                                }
                                value={
                                    point.id
                                }
                            >
                                {
                                    point.nombre
                                }
                            </option>
                        ),
                    )}
                </Select>

                <Select
                    label="Activo operacional"
                    value={
                        form.activo_operacional
                    }
                    onChange={(event) =>
                        setForm(
                            (current) => ({
                                ...current,
                                activo_operacional:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                >
                    <option value="">
                        Sin activo específico
                    </option>

                    {assets.map(
                        (asset) => (
                            <option
                                key={
                                    asset.id
                                }
                                value={
                                    asset.id
                                }
                            >
                                {
                                    asset.nombre
                                }
                            </option>
                        ),
                    )}
                </Select>

                <Input
                    label="Ubicación"
                    value={
                        form.ubicacion
                    }
                    onChange={(event) =>
                        setForm(
                            (current) => ({
                                ...current,
                                ubicacion:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                />

                {error && (
                    <p className="text-sm text-[var(--danger)]">
                        {error}
                    </p>
                )}

                <div className="flex justify-end gap-2">
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={onClose}
                    >
                        Cancelar
                    </Button>

                    <Button
                        type="submit"
                        disabled={
                            !canSubmit ||
                            saving
                        }
                    >
                        Vincular sensor
                    </Button>
                </div>
            </form>
        </Modal>
    );
}