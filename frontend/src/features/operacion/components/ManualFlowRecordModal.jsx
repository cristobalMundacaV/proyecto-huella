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
    createDataSource,
} from "../api/activityApi";

import {
    uploadEvidence,
} from "@/features/datos/services/dataApi";

import {
    createEnvironmentalPoint,
    createSectorRecord,
    listEnvironmentalPoints,
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

    point: "",
    newPointName: "",
    newPointCode: "",
    newPointType: "",
    newPointLocation: "",

    newSourceName: "",
    newSourceType: "manual",

    evidenceFile: null,
    evidenceName: "",
    evidenceType: "otro",
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
        points,
        setPoints,
    ] = useState([]);

    const [
        loadingSources,
        setLoadingSources,
    ] = useState(false);

    const [
        loadingPoints,
        setLoadingPoints,
    ] = useState(false);

    const [
        creatingSource,
        setCreatingSource,
    ] = useState(false);

    const [
        creatingPoint,
        setCreatingPoint,
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
        setLoadingPoints(true);

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
        listEnvironmentalPoints(
            organizationId,
            {
                obra: workId,
            },
        )
            .then((data) => {
                setPoints(
                    Array.isArray(data)
                        ? data
                        : data?.results ||
                        [],
                );
            })
            .catch(() => {
                setError(
                    "No fue posible cargar los puntos ambientales.",
                );
            })
            .finally(() => {
                setLoadingPoints(false);
            });
    }, [
        config?.defaultUnit,
        open,
        organizationId,
        workId,
    ]);

    async function createPoint() {
        const name =
            form.newPointName.trim();

        const code =
            form.newPointCode.trim();

        if (!name || !code) {
            setError(
                "Ingresa nombre y código para el punto ambiental.",
            );
            return;
        }

        setCreatingPoint(true);
        setError("");

        try {
            const created =
                await createEnvironmentalPoint(
                    organizationId,
                    {
                        obra: workId,
                        nombre: name,
                        codigo: code,
                        tipo:
                            form.newPointType.trim() ||
                            "punto_medicion",
                        ubicacion:
                            form.newPointLocation.trim(),
                    },
                );

            setPoints(
                (current) => [
                    ...current,
                    created,
                ],
            );

            setForm(
                (current) => ({
                    ...current,
                    point:
                        String(created.id),
                    newPointName: "",
                    newPointCode: "",
                    newPointType: "",
                    newPointLocation: "",
                }),
            );
        } catch (requestError) {
            setError(
                requestError
                    .response?.data
                    ?.detail ||
                requestError
                    .response?.data
                    ?.error ||
                "No fue posible crear el punto ambiental.",
            );
        } finally {
            setCreatingPoint(false);
        }
    }

    async function createSource() {
        const name =
            form.newSourceName.trim();

        if (!name) {
            setError(
                "Ingresa un nombre para la nueva fuente.",
            );
            return;
        }

        setCreatingSource(true);
        setError("");

        try {
            const created =
                await createDataSource(
                    organizationId,
                    {
                        nombre: name,
                        tipo:
                            form.newSourceType,
                        descripcion:
                            `Fuente creada durante captura manual de ${domain}.`,
                        activa: true,
                    },
                );

            setSources(
                (current) => [
                    ...current,
                    created,
                ],
            );

            setForm(
                (current) => ({
                    ...current,
                    source:
                        String(
                            created.id,
                        ),
                    newSourceName:
                        "",
                }),
            );
        } catch (requestError) {
            setError(
                requestError
                    .response?.data
                    ?.detail ||
                requestError
                    .response?.data
                    ?.error ||
                "No fue posible crear la fuente.",
            );
        } finally {
            setCreatingSource(false);
        }
    }

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
            let evidenceId = null;

            if (form.evidenceFile) {
                const evidenceData =
                    new FormData();

                evidenceData.append(
                    "archivo",
                    form.evidenceFile,
                );

                evidenceData.append(
                    "nombre",
                    form.evidenceName.trim() ||
                    form.evidenceFile.name,
                );

                evidenceData.append(
                    "tipo_evidencia",
                    form.evidenceType,
                );

                evidenceData.append(
                    "estado_documental",
                    "pendiente",
                );

                evidenceData.append(
                    "obra",
                    workId,
                );

                const evidence =
                    await uploadEvidence(
                        organizationId,
                        evidenceData,
                    );

                evidenceId =
                    evidence.id;
            }
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
                punto:
                    form.point || null,
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
                    form.point
                        ? "punto"
                        : "obra",
                concepto:
                    config.concept,
                valor_numerico:
                    form.value,
                unidad:
                    form.unit,
                fuente:
                    form.source,
                evidencia:
                    evidenceId,
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
                <Select
                    label="Punto ambiental"
                    value={
                        form.point
                    }
                    disabled={
                        loadingPoints
                    }
                    onChange={(
                        event,
                    ) =>
                        setForm(
                            (current) => ({
                                ...current,
                                point:
                                    event.target.value,
                            }),
                        )
                    }
                >
                    <option value="">
                        Registro general de la obra
                    </option>

                    {points.map(
                        (point) => (
                            <option
                                key={point.id}
                                value={point.id}
                            >
                                {point.nombre}
                            </option>
                        ),
                    )}
                </Select>
                <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] p-4">
                    <p className="text-sm font-black">
                        ¿El punto no existe?
                    </p>

                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <Input
                            label="Nombre del punto"
                            value={
                                form.newPointName
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        newPointName:
                                            event.target.value,
                                    }),
                                )
                            }
                        />

                        <Input
                            label="Código"
                            value={
                                form.newPointCode
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        newPointCode:
                                            event.target.value,
                                    }),
                                )
                            }
                        />

                        <Input
                            label="Tipo"
                            placeholder="Ej: medidor_agua"
                            value={
                                form.newPointType
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        newPointType:
                                            event.target.value,
                                    }),
                                )
                            }
                        />

                        <Input
                            label="Ubicación"
                            placeholder="Ej: acceso norte"
                            value={
                                form.newPointLocation
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        newPointLocation:
                                            event.target.value,
                                    }),
                                )
                            }
                        />
                    </div>

                    <div className="mt-3">
                        <Button
                            type="button"
                            variant="secondary"
                            loading={
                                creatingPoint
                            }
                            onClick={
                                createPoint
                            }
                        >
                            Crear punto
                        </Button>
                    </div>
                </div>
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
                <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] p-4">
                    <p className="text-sm font-black">
                        ¿La fuente no existe?
                    </p>

                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <Input
                            label="Nombre de nueva fuente"
                            value={
                                form.newSourceName
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        newSourceName:
                                            event.target.value,
                                    }),
                                )
                            }
                        />

                        <Select
                            label="Tipo de fuente"
                            value={
                                form.newSourceType
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        newSourceType:
                                            event.target.value,
                                    }),
                                )
                            }
                        >
                            <option value="manual">
                                Registro manual
                            </option>

                            <option value="documento">
                                Documento
                            </option>

                            <option value="sensor">
                                Sensor
                            </option>

                            <option value="integracion">
                                Integración
                            </option>
                        </Select>
                    </div>

                    <div className="mt-3">
                        <Button
                            type="button"
                            variant="secondary"
                            loading={
                                creatingSource
                            }
                            onClick={
                                createSource
                            }
                        >
                            Crear fuente
                        </Button>
                    </div>
                </div>
                <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] p-4">
                    <p className="text-sm font-black">
                        Evidencia opcional
                    </p>

                    <div className="mt-3 space-y-3">
                        <Input
                            label="Nombre del documento"
                            value={
                                form.evidenceName
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        evidenceName:
                                            event.target.value,
                                    }),
                                )
                            }
                        />

                        <Select
                            label="Tipo de evidencia"
                            value={
                                form.evidenceType
                            }
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        evidenceType:
                                            event.target.value,
                                    }),
                                )
                            }
                        >
                            <option value="otro">
                                Otro documento
                            </option>

                            <option value="boleta_electrica">
                                Boleta eléctrica
                            </option>

                            <option value="factura_combustible">
                                Factura de combustible
                            </option>

                            <option value="registro_retiro_residuos">
                                Retiro de residuos
                            </option>

                            <option value="ticket_pesaje">
                                Ticket de pesaje
                            </option>

                            <option value="documento_transporte">
                                Documento de transporte
                            </option>
                        </Select>

                        <Input
                            type="file"
                            label="Archivo"
                            onChange={(
                                event,
                            ) =>
                                setForm(
                                    (current) => ({
                                        ...current,
                                        evidenceFile:
                                            event.target.files?.[0] ||
                                            null,
                                    }),
                                )
                            }
                        />
                    </div>
                </div>
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