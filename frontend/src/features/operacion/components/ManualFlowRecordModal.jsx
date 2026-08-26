import {
    useEffect,
    useMemo,
    useState,
} from "react";
import { ClipboardPlus } from "lucide-react";

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
        modes: [
            {
                value: "consumo",
                label: "Consumo de energía",
                activityType:
                    "consumo_energia",
                flow:
                    "energia",
                concept:
                    "consumo_energia",
            },
            {
                value: "generacion",
                label: "Generación propia",
                activityType:
                    "generacion_energia",
                flow:
                    "generacion_propia",
                concept:
                    "energia_generada",
            },
        ],
        defaultUnit:
            "kWh",
        requiresResourceType:
            true,
        defaultPointType:
            "punto_energia",
        resourceTypes: [
            {
                value: "red_electrica",
                label: "Red eléctrica",
            },
            {
                value: "generador",
                label: "Generador",
            },
            {
                value: "solar_fotovoltaica",
                label: "Solar fotovoltaica",
            },
            {
                value: "otra",
                label: "Otra fuente",
            },
        ],
    },

    agua: {
        activityType:
            "consumo_agua",
        concept:
            "consumo_agua",
        defaultUnit:
            "m3",
        requiresResourceType:
            true,
        defaultPointType:
            "punto_agua",
        resourceTypes: [
            {
                value: "red_publica",
                label: "Red pública",
            },
            {
                value: "pozo",
                label: "Pozo",
            },
            {
                value: "camion_aljibe",
                label: "Camión aljibe",
            },
            {
                value: "agua_lluvia",
                label: "Agua lluvia",
            },
            {
                value: "agua_reutilizada",
                label: "Agua reutilizada",
            },
            {
                value: "otra",
                label: "Otra fuente de agua",
            },
        ],
    },

    combustibles: {
        activityType:
            "consumo_combustible_estacionario",
        concept:
            "combustible_consumido",
        defaultUnit:
            "L",
        requiresResourceType:
            true,
        defaultPointType:
            "punto_combustible",
        uses: [
            { value: "generador", label: "Generador" },
            { value: "maquinaria", label: "Maquinaria" },
            { value: "vehiculo", label: "Vehículo" },
            { value: "equipo_menor", label: "Equipo menor" },
            { value: "calefaccion", label: "Calefacción" },
            { value: "otro", label: "Otro" },
        ],
        resourceTypes: [
            {
                value: "diesel",
                label: "Diésel",
            },
            {
                value: "gasolina",
                label: "Gasolina",
            },
            {
                value: "gas_licuado",
                label: "Gas licuado",
            },
            {
                value: "gas_natural",
                label: "Gas natural",
            },
            {
                value: "otro",
                label: "Otro combustible",
            },
        ],


    },

    residuos: {
        activityType:
            "gestion_residuo",
        concept:
            "cantidad_residuo",
        defaultUnit:
            "kg",
        requiresDestination:
            true,
        requiresResourceType:
            true,
        resourceTypes: [
            {
                value: "no_peligroso",
                label: "Residuo no peligroso",
            },
            {
                value: "peligroso",
                label: "Residuo peligroso",
            },
        ],
        destinations: [
            {
                value: "residuo",
                label: "Residuo sin destino definido",
            },
            {
                value: "reutilizacion",
                label: "Reutilización",
            },
            {
                value: "reciclaje",
                label: "Reciclaje",
            },
            {
                value: "valorizacion",
                label: "Valorización",
            },
            {
                value: "disposicion",
                label: "Disposición final",
            },
            {
                value: "subproducto_reutilizado",
                label: "Subproducto reutilizado",
            },
        ],
    },

    ruido: {
        activityType:
            "monitoreo_ruido",
        concept:
            "nivel_ruido",
        defaultUnit:
            "dB(A)",
        requiresMetric:
            true,
        defaultMetric:
            "Leq",
        defaultPointType:
            "punto_ruido",
        metrics: [
            {
                value: "Leq",
                label: "Leq",
            },
            {
                value: "Lmax",
                label: "Lmax",
            },
            {
                value: "Lmin",
                label: "Lmin",
            },
        ],
    },

    "emisiones-atmosfericas": {
        flow:
            "emisiones_atmosfericas",
        activityType:
            "monitoreo_emisiones_atmosfericas",
        concept:
            "concentracion_emision",
        defaultUnit:
            "mg/m3",
        requiresResourceType:
            true,
        defaultPointType:
            "punto_emision",
        resourceTypes: [
            { value: "material_particulado", label: "Material particulado / polvo" },
            { value: "fuente_movil", label: "Fuente móvil" },
            { value: "fuente_estacionaria", label: "Fuente estacionaria" },
            { value: "otra", label: "Otra fuente" },
        ],
    },

    suelo: {
        activityType:
            "gestion_suelo",
        concept:
            "superficie_intervenida",
        defaultUnit:
            "m2",
        defaultPointType:
            "punto_suelo",
        modes: [
            {
                value: "superficie",
                label: "Superficie intervenida",
                activityType: "gestion_suelo",
                flow: "suelo",
                concept: "superficie_intervenida",
                valueType: "number",
                unit: "m2",
            },
            {
                value: "erosion",
                label: "Erosión observada",
                activityType: "gestion_suelo",
                flow: "suelo",
                concept: "erosion_observada",
                valueType: "text",
                unit: "",
            },
            {
                value: "contaminacion",
                label: "Afectación o contaminación",
                activityType: "gestion_suelo",
                flow: "suelo",
                concept: "afectacion_suelo",
                valueType: "text",
                unit: "",
            },
        ],
    },

    "hidrica-suelo": {
        activityType:
            "gestion_hidrica_suelo",
        concept:
            "superficie_intervenida",
        defaultUnit:
            "m2",
        defaultPointType:
            "punto_drenaje",
        modes: [
            {
                value: "superficie",
                label: "Superficie intervenida",
                activityType:
                    "gestion_hidrica_suelo",
                flow:
                    "gestion_hidrica_suelo",
                concept:
                    "superficie_intervenida",
                valueType:
                    "number",
                unit:
                    "m2",
            },
            {
                value: "desborde",
                label: "Desborde observado",
                activityType:
                    "gestion_hidrica_suelo",
                flow:
                    "gestion_hidrica_suelo",
                concept:
                    "desborde",
                valueType:
                    "text",
                unit:
                    "",
            },
            {
                value: "erosion",
                label: "Erosión observada",
                activityType:
                    "gestion_hidrica_suelo",
                flow:
                    "gestion_hidrica_suelo",
                concept:
                    "erosion_observada",
                valueType:
                    "text",
                unit:
                    "",
            },
        ],
    },
};

const initialForm = {
    mode: "consumo",
    value: "",
    unit: "",
    source: "",
    resourceType: "",
    metric: "",
    destination: "",

    recordDate: "",
    use: "",

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
            mode:
                config?.modes?.[0]?.value ||
                initialForm.mode,
            unit:
                config?.modes?.[0]?.unit ||
                config?.defaultUnit ||
                "",
            metric:
                config?.defaultMetric ||
                "",
            recordDate:
                new Date().toISOString().slice(0, 10),
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
        config?.defaultMetric,
        config?.defaultUnit,
        config?.modes,
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
                            config?.defaultPointType ||
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
                form.source &&
                (
                    domain !== "combustibles" ||
                    form.recordDate
                ) &&
                (
                    !config.requiresResourceType ||
                    form.resourceType
                ) &&
                (
                    !config.requiresDestination ||
                    form.destination
                ) &&
                (
                    !config.requiresMetric ||
                    form.metric
                )
            ),
        [
            config,
            domain,
            form.destination,
            form.metric,
            form.recordDate,
            form.resourceType,
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

            const operationalTimestamp =
                domain === "combustibles" && form.recordDate
                    ? `${form.recordDate}T12:00:00`
                    : now;
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
            const selectedMode =
                config.modes?.find(
                    (mode) =>
                        mode.value ===
                        form.mode,
                );
            const valueType =
                selectedMode?.valueType ||
                "number";
            const activity =
                await createOperationalActivity(
                    organizationId,
                    {
                        obra: workId,
                        tipo:
                            selectedMode?.activityType ||
                            config.activityType,
                        nombre:
                            `Registro manual · ${domain}`,
                        timestamp_inicio:
                            operationalTimestamp,
                    },
                );

            const payload = {
                actividad:
                    activity.id,
                obra: workId,
                punto:
                    form.point || null,
                flujo:
                    selectedMode?.flow ||
                    config.flow ||
                    (
                        domain ===
                            "combustibles"
                            ? "combustible_estacionario"
                            : domain ===
                                "hidrica-suelo"
                                ? "gestion_hidrica_suelo"
                                : domain
                    ),
                periodo_inicio:
                    operationalTimestamp,
                granularidad:
                    form.point
                        ? "punto"
                        : "obra",
                concepto:
                    selectedMode?.concept ||
                    config.concept,
                valor_numerico:
                    valueType === "number"
                        ? form.value
                        : null,
                valor_texto:
                    valueType === "text"
                        ? form.value
                        : "",
                unidad:
                    form.unit,
                fuente:
                    form.source,
                evidencia:
                    evidenceId,
                destino_operacional:
                    form.destination || "",
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
            onClose={() => { if (!saving) onClose(); }}
            eyebrow="REGISTRO OPERACIONAL"
            icon={ClipboardPlus}
            title={domain === "combustibles" ? "Registrar combustible" : "Registrar información"}
            description={
                domain === "combustibles"
                    ? "Registra el consumo real de combustible y conserva su origen y trazabilidad."
                    : "El registro quedará asociado a esta obra y conservará su fuente."
            }
            footer={<div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={saving} onClick={onClose}>Cancelar</Button><Button form="manual-flow-form" type="submit" loading={saving} disabled={!canSubmit}>Registrar</Button></div>}
        >
            <form
                id="manual-flow-form"
                className="space-y-4"
                onSubmit={submit}
            >
                {config.resourceTypes && (
                    <Select
                        required={config.requiresResourceType}
                        label={
                            domain === "combustibles"
                                ? "Tipo de combustible"
                                : "Tipo de recurso"
                        }
                        value={form.resourceType}
                        onChange={(event) =>
                            setForm((current) => ({
                                ...current,
                                resourceType: event.target.value,
                            }))
                        }
                    >
                        <option value="">
                            {domain === "combustibles"
                                ? "Selecciona un combustible"
                                : "Selecciona un tipo"}
                        </option>

                        {config.resourceTypes.map((resource) => (
                            <option
                                key={resource.value}
                                value={resource.value}
                            >
                                {resource.label}
                            </option>
                        ))}
                    </Select>
                )}

                {config.modes && (
                    <Select
                        label="Tipo de registro"
                        value={
                            form.mode
                        }
                        onChange={(
                            event,
                        ) => {
                            const nextMode =
                                config.modes.find(
                                    (mode) =>
                                        mode.value ===
                                        event.target.value,
                                );

                            setForm(
                                (current) => ({
                                    ...current,
                                    mode:
                                        event.target.value,
                                    value:
                                        "",
                                    unit:
                                        nextMode?.unit ??
                                        config.defaultUnit ??
                                        "",
                                }),
                            );
                        }}
                    >
                        {config.modes.map(
                            (mode) => (
                                <option
                                    key={
                                        mode.value
                                    }
                                    value={
                                        mode.value
                                    }
                                >
                                    {
                                        mode.label
                                    }
                                </option>
                            ),
                        )}
                    </Select>
                )}
                {config.destinations && (
                    <Select
                        required={
                            config.requiresDestination
                        }
                        label="Destino del residuo"
                        value={
                            form.destination
                        }
                        onChange={(
                            event,
                        ) =>
                            setForm(
                                (current) => ({
                                    ...current,
                                    destination:
                                        event.target.value,
                                }),
                            )
                        }
                    >
                        <option value="">
                            Selecciona un destino
                        </option>

                        {config.destinations.map(
                            (destination) => (
                                <option
                                    key={
                                        destination.value
                                    }
                                    value={
                                        destination.value
                                    }
                                >
                                    {
                                        destination.label
                                    }
                                </option>
                            ),
                        )}
                    </Select>
                )}
                <Input
                    required
                    type={
                        config.modes?.find(
                            (mode) =>
                                mode.value ===
                                form.mode,
                        )?.valueType === "text"
                            ? "text"
                            : "number"
                    }
                    step="any"
                    label={
                        config.modes?.find(
                            (mode) =>
                                mode.value ===
                                form.mode,
                        )?.valueType === "text"
                            ? "Observación"
                            : domain === "combustibles"
                                ? "Cantidad"
                                : "Valor"
                    }
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

                {domain === "combustibles" && (
                    <Input
                        required
                        type="date"
                        label="Fecha del registro"
                        value={form.recordDate}
                        onChange={(event) =>
                            setForm((current) => ({
                                ...current,
                                recordDate: event.target.value,
                            }))
                        }
                    />
                )}

                {domain === "combustibles" && config.uses && (
                    <Select
                        label="Uso / destino"
                        value={form.use}
                        onChange={(event) =>
                            setForm((current) => ({
                                ...current,
                                use: event.target.value,
                            }))
                        }
                    >
                        <option value="">
                            Selecciona un uso
                        </option>

                        {config.uses.map((use) => (
                            <option
                                key={use.value}
                                value={use.value}
                            >
                                {use.label}
                            </option>
                        ))}
                    </Select>
                )}

                <Select
                    label={domain === "combustibles" ? "Punto / ubicación" : "Punto ambiental"}
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
                            placeholder={
                                domain === "agua"
                                    ? "Ej: medidor_agua"
                                    : domain === "energia"
                                        ? "Ej: medidor_tablero_principal"
                                        : domain === "combustibles"
                                            ? "Ej: estanque_generador_01"
                                            : "Ej: punto_monitoreo"
                            }
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

                <Select
                    required
                    label={domain === "combustibles" ? "Origen del dato" : "Fuente del dato"}
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
                        {domain === "combustibles"
                            ? "Respaldo del registro"
                            : "Evidencia opcional"}
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
                {config.resourceTypes ? (
                    <Select
                        required={
                            config.requiresResourceType
                        }
                        label={
                            domain === "agua"
                                ? "Fuente de abastecimiento"
                                : domain === "energia"
                                    ? "Origen de la energía"
                                    : domain === "combustibles"
                                        ? "Tipo de combustible"
                                        : "Tipo de recurso"
                        }
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
                                        event.target.value,
                                }),
                            )
                        }
                    >
                        <option value="">
                            Selecciona un tipo
                        </option>

                        {config.resourceTypes.map(
                            (resource) => (
                                <option
                                    key={
                                        resource.value
                                    }
                                    value={
                                        resource.value
                                    }
                                >
                                    {
                                        resource.label
                                    }
                                </option>
                            ),
                        )}
                    </Select>
                ) : (
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
                                        event.target.value,
                                }),
                            )
                        }
                    />
                )}

                {config.metrics ? (
                    <Select
                        required={
                            config.requiresMetric
                        }
                        label="Métrica acústica"
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
                                        event.target.value,
                                }),
                            )
                        }
                    >
                        {config.metrics.map(
                            (metric) => (
                                <option
                                    key={
                                        metric.value
                                    }
                                    value={
                                        metric.value
                                    }
                                >
                                    {
                                        metric.label
                                    }
                                </option>
                            ),
                        )}
                    </Select>
                ) : domain === "hidrica-suelo" ? (
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
                                        event.target.value,
                                }),
                            )
                        }
                    />
                ) : null}

                {error && (
                    <p
                        className="text-sm text-[var(--status-danger)]"
                        role="alert"
                    >
                        {error}
                    </p>
                )}

            </form>
        </Modal>
    );
}
