import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    Button,
    Input,
    Modal,
    Select,
} from "@/shared/ui";

import {
    createOperationalActivity,
    listDataSources,
} from "../api/activityApi";

import {
    createSectorRecord,
} from "../api/sectorFlowsApi";

const FLOW_CONFIG = {
    energia: {
        activityType:
            "consumo_energia",
        concept:
            "consumo_energia",
        defaultUnit:
            "kWh",
    },

    agua: {
        activityType:
            "consumo_agua",
        concept:
            "consumo_agua",
        defaultUnit:
            "m3",
    },

    combustibles: {
        activityType:
            "consumo_combustible_estacionario",
        concept:
            "combustible_consumido",
        defaultUnit:
            "L",
    },

    residuos: {
        activityType:
            "gestion_residuo",
        concept:
            "cantidad_residuo",
        defaultUnit:
            "kg",
    },

    ruido: {
        activityType:
            "monitoreo_ruido",
        concept:
            "nivel_ruido",
        defaultUnit:
            "dB(A)",
    },

    "hidrica-suelo": {
        activityType:
            "gestion_hidrica_suelo",
        concept:
            "condicion_ambiental",
        defaultUnit:
            "",
    },
};

const initialForm = {
    value: "",
    unit: "",
    source: "",
    resourceType: "",
    metric: "",
};

export default function ManualFlowRecordModal({
    open,
    onClose,
    organizationId,
    workId,
    domain,
    onCreated,
}) {
    const config =
        FLOW_CONFIG[domain];

    const [
        form,
        setForm,
    ] = useState(initialForm);

    const [
        sources,
        setSources,
    ] = useState([]);

    const [
        loadingSources,
        setLoadingSources,
    ] = useState(false);

    const [
        saving,
        setSaving,
    ] = useState(false);

    const [
        error,
        setError,
    ] = useState("");

    useEffect(() => {
        if (!open) {
            return;
        }

        setForm({
            ...initialForm,
            unit:
                config?.defaultUnit ||
                "",
        });

        setError("");
        setLoadingSources(true);

        listDataSources(
            organizationId,
        )
            .then((data) => {
                setSources(
                    Array.isArray(data)
                        ? data
                        : data?.results ||
                        [],
                );
            })
            .catch(() => {
                setError(
                    "No fue posible cargar las fuentes de datos.",
                );
            })
            .finally(() => {
                setLoadingSources(false);
            });
    }, [
        config?.defaultUnit,
        open,
        organizationId,
    ]);

    const canSubmit = useMemo(
        () =>
            Boolean(
                config &&
                form.value !== "" &&
                form.source,
            ),
        [
            config,
            form.source,
            form.value,
        ],
    );

    async function submit(
        event,
    ) {
        event.preventDefault();

        if (!canSubmit) {
            return;
        }

        setSaving(true);
        setError("");

        try {
            const now =
                new Date().toISOString();

            const activity =
                await createOperationalActivity(
                    organizationId,
                    {
                        obra: workId,
                        tipo:
                            config.activityType,
                        nombre:
                            `Registro manual · ${domain}`,
                        timestamp_inicio:
                            now,
                    },
                );

            const payload = {
                actividad:
                    activity.id,
                obra: workId,
                flujo:
                    domain ===
                        "combustibles"
                        ? "combustible_estacionario"
                        : domain ===
                            "hidrica-suelo"
                            ? "gestion_hidrica_suelo"
                            : domain,
                periodo_inicio:
                    now,
                granularidad:
                    "obra",
                concepto:
                    config.concept,
                valor_numerico:
                    form.value,
                unidad:
                    form.unit,
                fuente:
                    form.source,
            };

            if (
                form.resourceType.trim()
            ) {
                payload.tipo_recurso =
                    form.resourceType.trim();
            }

            if (
                form.metric.trim()
            ) {
                payload.metrica =
                    form.metric.trim();
            }

            await createSectorRecord(
                organizationId,
                payload,
            );

            await onCreated?.();

            onClose();
        } catch (
        requestError
        ) {
            const data =
                requestError.response
                    ?.data;

            setError(
                data?.detail ||
                data?.error ||
                Object.values(
                    data || {},
                )?.flat?.()?.[0] ||
                "No fue posible registrar el dato.",
            );
        } finally {
            setSaving(false);
        }
    }

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Registrar información"
            description="El registro quedará asociado a esta obra y conservará su fuente."
        >
            <form
                className="space-y-4"
                onSubmit={submit}
            >
                <Input
                    required
                    type="number"
                    step="any"
                    label="Valor"
                    value={
                        form.value
                    }
                    onChange={(
                        event,
                    ) =>
                        setForm(
                            (current) => ({
                                ...current,
                                value:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                />

                <Input
                    label="Unidad"
                    value={
                        form.unit
                    }
                    onChange={(
                        event,
                    ) =>
                        setForm(
                            (current) => ({
                                ...current,
                                unit:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                />

                <Select
                    required
                    label="Fuente del dato"
                    value={
                        form.source
                    }
                    disabled={
                        loadingSources
                    }
                    onChange={(
                        event,
                    ) =>
                        setForm(
                            (current) => ({
                                ...current,
                                source:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                >
                    <option value="">
                        Selecciona una fuente
                    </option>

                    {sources.map(
                        (source) => (
                            <option
                                key={
                                    source.id
                                }
                                value={
                                    source.id
                                }
                            >
                                {
                                    source.nombre
                                }
                            </option>
                        ),
                    )}
                </Select>

                <Input
                    label="Tipo o recurso"
                    value={
                        form.resourceType
                    }
                    onChange={(
                        event,
                    ) =>
                        setForm(
                            (current) => ({
                                ...current,
                                resourceType:
                                    event.target
                                        .value,
                            }),
                        )
                    }
                />

                {(domain ===
                    "ruido" ||
                    domain ===
                    "hidrica-suelo") && (
                        <Input
                            label="Métrica"
                            value={
                                form.metric
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        metric:
                                            event.target
                                                .value,
                                    }),
                                )
                            }
                        />
                    )}

                {error && (
                    <p
                        className="text-sm text-[var(--status-danger)]"
                        role="alert"
                    >
                        {error}
                    </p>
                )}

                <div className="flex justify-end gap-2">
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={
                            onClose
                        }
                    >
                        Cancelar
                    </Button>

                    <Button
                        type="submit"
                        loading={
                            saving
                        }
                        disabled={
                            !canSubmit
                        }
                    >
                        Registrar
                    </Button>
                </div>
            </form>
        </Modal>
    );
}