import {
    activityBelongsToDomain,
} from "../utils/operationSelectors";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    AlertTriangle,
    CheckCircle2,
    ShieldCheck,
} from "lucide-react";

import {
    getDiscrepancies,
    getQualityEvaluations,
    updateDiscrepancy,
} from "@/features/professional/api/professionalV2Api";

import {
    Button,
    EmptyState,
    Input,
    Modal,
    SectionHeader,
    Select,
    StatusBadge,
    TableBody,
    TableCell,
    TableHead,
    TableShell,
} from "@/shared/ui";

import {
    formatDateTime,
    formatNumber,
} from "@/shared/utils/formatters";


function human(value) {
    return String(
        value || "",
    )
        .replaceAll(
            "_",
            " ",
        )
        .replace(
            /\b\w/g,
            (character) =>
                character.toUpperCase(),
        );
}


function qualityTone(state) {
    if (
        state === "confiable"
    ) {
        return "success";
    }

    if (
        state ===
        "confiable_con_observaciones"
    ) {
        return "warning";
    }

    if (
        state === "no_confiable" ||
        state === "no_calculable"
    ) {
        return "danger";
    }

    return "warning";
}

function documentaryLabel(validation, fallback) {
    const labels = {
        verificada: "Verificado",
        compatible_incompleta: "Compatible, requiere revisión",
        contradiccion: "Contradice el dato declarado",
        no_pertinente: "No pertinente",
        indeterminada: "En revisión",
        pendiente_procesamiento: "Procesando",
    };
    return labels[validation?.estado] || human(fallback);
}

function DocumentaryValidation({ evidence }) {
    const validation = evidence?.validacion_documental;
    if (!evidence) return "Sin evidencia adjunta";
    return (
        <>
            <b>{evidence.nombre}</b>
            <span className="block text-xs text-[var(--text-muted)]">
                Estado: {documentaryLabel(validation, evidence.estado_documental)}
            </span>
            {validation?.estado === "no_pertinente" && (
                <span className="mt-1 block text-xs text-[var(--danger)]">
                    Este archivo no parece corresponder al respaldo esperado para el dato.
                </span>
            )}
            {validation?.comparaciones?.map((comparison) => (
                <span
                    className="mt-1 block text-xs text-[var(--text-muted)]"
                    key={comparison.campo}
                >
                    {comparison.estado === "contradice" ? "✕" : comparison.estado === "coincide" || comparison.estado === "compatible_por_conversion" ? "✓" : "•"}{" "}
                    {human(comparison.campo)}: {comparison.declarado || "No declarado"}
                    {comparison.documental ? ` / Documento: ${comparison.documental}` : " / No disponible en documento"}
                </span>
            ))}
        </>
    );
}


export default function DomainQualityPanel({
    domain,
    organizationId,
    workId,
    records = [],
}) {
    const [
        state,
        setState,
    ] = useState({
        loading: true,
        quality: [],
        discrepancies: [],
    });

    const [
        resolution,
        setResolution,
    ] = useState(null);

    const [
        busy,
        setBusy,
    ] = useState(false);

    const load = useCallback(
        async () => {
            if (
                !organizationId ||
                !workId
            ) {
                return;
            }

            setState(
                (current) => ({
                    ...current,
                    loading: true,
                }),
            );

            const [
                qualityResult,
                discrepancyResult,
            ] =
                await Promise.allSettled([
                    getQualityEvaluations(
                        organizationId,
                        {
                            obra:
                                workId,
                        },
                    ),

                    getDiscrepancies(
                        organizationId,
                        {
                            obra:
                                workId,
                        },
                    ),
                ]);

            setState({
                loading: false,

                quality:
                    qualityResult.status ===
                        "fulfilled"
                        ? qualityResult.value
                        : [],

                discrepancies:
                    discrepancyResult.status ===
                        "fulfilled"
                        ? discrepancyResult.value
                        : [],
            });
        },
        [
            organizationId,
            workId,
        ],
    );

    useEffect(
        () => {
            load();
        },
        [load],
    );

    const quality =
        useMemo(
            () =>
                state.quality.filter(
                    (item) =>
                        activityBelongsToDomain(
                            item.observacion_detalle?.actividad,
                            domain,
                        ),
                ),
            [
                state.quality,
                domain,
            ],
        );

    const discrepancies =
        useMemo(
            () =>
                state.discrepancies.filter(
                    (item) =>
                        activityBelongsToDomain(
                            item.actividad_detalle,
                            domain,
                        ),
                ),
            [
                state.discrepancies,
                domain,
            ],
        );

    const openDiscrepancies =
        discrepancies.filter(
            (item) =>
                item.estado ===
                "detectada" ||
                item.estado ===
                "requiere_revision",
        );

    const reviewCount =
        quality.filter(
            (item) =>
                item.estado ===
                "requiere_revision" ||
                item.estado ===
                "no_confiable" ||
                item.estado ===
                "no_calculable",
        ).length;

    const recordContextByActivity =
        useMemo(
            () =>
                new Map(
                    records
                        .map(
                            (record) => {
                                const activityId =
                                    typeof record.actividad ===
                                        "object"
                                        ? record.actividad?.id
                                        : record.actividad;

                                return [
                                    String(
                                        activityId ||
                                        "",
                                    ),
                                    {
                                        resourceType:
                                            record.tipo_recurso,

                                        destination:
                                            record.destino_operacional,
                                    },
                                ];
                            },
                        )
                        .filter(
                            ([activityId]) =>
                                Boolean(
                                    activityId,
                                ),
                        ),
                ),
            [records],
        );

    function resourceLabel(
        value,
    ) {
        const labels = {
            diesel: "Diésel",
            gasolina: "Gasolina",
            gas_licuado:
                "Gas licuado",
            gas_natural:
                "Gas natural",
        };

        return (
            labels[value] ||
            human(value)
        );
    }

    async function resolve() {
        if (
            !resolution
                ?.observationId ||
            !resolution
                ?.text
                ?.trim()
        ) {
            return;
        }

        setBusy(true);

        try {
            await updateDiscrepancy(
                organizationId,
                resolution.id,
                {
                    estado:
                        "resuelta",

                    observacion_seleccionada:
                        Number(
                            resolution
                                .observationId,
                        ),

                    resolucion:
                        resolution.text.trim(),
                },
            );

            setResolution(
                null,
            );

            await load();
        } finally {
            setBusy(false);
        }
    }

    return (
        <section className="space-y-5">
            <SectionHeader
                eyebrow="GOBERNANZA DEL DATO"
                title="Calidad y discrepancias"
                description="Separa calidad del dato, confiabilidad de la fuente y contradicciones que requieren una decisión explícita."
            />

            <div className="
                grid gap-4
                md:grid-cols-3
            ">
                <div className="
                    rounded-2xl border
                    border-[var(--border-default)]
                    bg-[var(--bg-surface)]
                    p-5 shadow-sm
                ">
                    <div className="
                        flex items-start
                        justify-between gap-4
                    ">
                        <div>
                            <p className="
                                text-3xl
                                font-black
                                tracking-tight
                            ">
                                {quality.length}
                            </p>

                            <p className="
                                mt-1 font-black
                            ">
                                {quality.length === 1
                                    ? "Registro evaluado"
                                    : "Registros evaluados"}
                            </p>

                            <p className="
                                mt-1 text-xs
                                text-[var(--text-muted)]
                            ">
                                Datos con evaluación
                                de calidad disponible.
                            </p>
                        </div>

                        <span className="
                            flex h-10 w-10
                            items-center
                            justify-center
                            rounded-xl
                            bg-emerald-50
                            text-emerald-700
                        ">
                            <ShieldCheck
                                size={19}
                            />
                        </span>
                    </div>
                </div>

                <div className="
                    rounded-2xl border
                    border-[var(--border-default)]
                    bg-[var(--bg-surface)]
                    p-5 shadow-sm
                ">
                    <div className="
                        flex items-start
                        justify-between gap-4
                    ">
                        <div>
                            <p className="
                                text-3xl
                                font-black
                                tracking-tight
                            ">
                                {reviewCount}
                            </p>

                            <p className="
                                mt-1 font-black
                            ">
                                Requieren atención
                            </p>

                            <p className="
                                mt-1 text-xs
                                text-[var(--text-muted)]
                            ">
                                Registros cuya calidad
                                requiere revisión.
                            </p>
                        </div>

                        <span className="
                            flex h-10 w-10
                            items-center
                            justify-center
                            rounded-xl
                            bg-amber-50
                            text-amber-700
                        ">
                            <AlertTriangle
                                size={19}
                            />
                        </span>
                    </div>
                </div>

                <div className="
                    rounded-2xl border
                    border-[var(--border-default)]
                    bg-[var(--bg-surface)]
                    p-5 shadow-sm
                ">
                    <div className="
                        flex items-start
                        justify-between gap-4
                    ">
                        <div>
                            <p className="
                                text-3xl
                                font-black
                                tracking-tight
                            ">
                                {
                                    openDiscrepancies.length
                                }
                            </p>

                            <p className="
                                mt-1 font-black
                            ">
                                Discrepancias abiertas
                            </p>

                            <p className="
                                mt-1 text-xs
                                text-[var(--text-muted)]
                            ">
                                Contradicciones todavía
                                pendientes de resolución.
                            </p>
                        </div>

                        <span className="
                            flex h-10 w-10
                            items-center
                            justify-center
                            rounded-xl
                            bg-slate-50
                            text-slate-700
                        ">
                            <CheckCircle2
                                size={19}
                            />
                        </span>
                    </div>
                </div>
            </div>

            {state.loading ? (
                <p className="text-sm text-[var(--text-muted)]">
                    Evaluando calidad...
                </p>
            ) : !quality.length &&
                !discrepancies.length ? (
                <EmptyState
                    title="Sin señales de gobernanza"
                    description="Todavía no hay evaluaciones o discrepancias registradas para este ámbito."
                />
            ) : (
                <>
                    {openDiscrepancies.length >
                        0 && (
                            <div className="space-y-3">
                                <h3 className="font-black">
                                    Discrepancias abiertas
                                </h3>

                                <TableShell>
                                    <TableHead>
                                        <tr>
                                            <TableCell as="th">
                                                Concepto
                                            </TableCell>

                                            <TableCell as="th">
                                                Estado
                                            </TableCell>

                                            <TableCell as="th">
                                                Valores
                                            </TableCell>

                                            <TableCell as="th">
                                                Acción
                                            </TableCell>
                                        </tr>
                                    </TableHead>

                                    <TableBody
                                        columns={4}
                                    >
                                        {openDiscrepancies.map(
                                            (
                                                item,
                                            ) => (
                                                <tr
                                                    key={
                                                        item.id
                                                    }
                                                >
                                                    <TableCell>
                                                        <b>
                                                            {human(
                                                                item.concepto,
                                                            )}
                                                        </b>
                                                    </TableCell>

                                                    <TableCell>
                                                        <StatusBadge tone="warning">
                                                            {human(
                                                                item.estado,
                                                            )}
                                                        </StatusBadge>
                                                    </TableCell>

                                                    <TableCell>
                                                        <div className="space-y-1">
                                                            {item.observaciones_detalle?.map(
                                                                (
                                                                    observation,
                                                                ) => (
                                                                    <div
                                                                        key={
                                                                            observation.id
                                                                        }
                                                                        className="text-sm"
                                                                    >
                                                                        <b>
                                                                            {
                                                                                observation
                                                                                    .fuente
                                                                                    ?.nombre
                                                                            }
                                                                        </b>
                                                                        {" · "}
                                                                        {observation.valor !==
                                                                            null
                                                                            ? `${formatNumber(
                                                                                observation.valor,
                                                                            )} ${observation.unidad || ""}`
                                                                            : observation.valor_texto ||
                                                                            "Sin valor"}
                                                                    </div>
                                                                ),
                                                            )}
                                                        </div>
                                                    </TableCell>

                                                    <TableCell>
                                                        <Button
                                                            variant="secondary"
                                                            onClick={() =>
                                                                setResolution(
                                                                    {
                                                                        id:
                                                                            item.id,

                                                                        observations:
                                                                            item.observaciones_detalle ||
                                                                            [],

                                                                        observationId:
                                                                            "",

                                                                        text:
                                                                            "",
                                                                    },
                                                                )
                                                            }
                                                        >
                                                            Resolver
                                                        </Button>
                                                    </TableCell>
                                                </tr>
                                            ),
                                        )}
                                    </TableBody>
                                </TableShell>
                            </div>
                        )}

                    {quality.length >
                        0 && (
                            <div className="space-y-3">
                                <h3 className="font-black">
                                    Calidad de los datos
                                </h3>

                                <TableShell>
                                    <TableHead>
                                        <tr>
                                            <TableCell as="th">
                                                Dato
                                            </TableCell>

                                            <TableCell as="th">
                                                Calidad
                                            </TableCell>

                                            <TableCell as="th">
                                                Respaldo documental
                                            </TableCell>

                                            <TableCell as="th">
                                                Fuente / captura
                                            </TableCell>

                                            <TableCell as="th">
                                                Evaluado
                                            </TableCell>
                                        </tr>
                                    </TableHead>

                                    <TableBody
                                        columns={5}
                                    >
                                        {quality.map(
                                            (
                                                item,
                                            ) => {
                                                const observation =
                                                    item.observacion_detalle;

                                                const activityId =
                                                    observation
                                                        ?.actividad
                                                        ?.id;

                                                const recordContext =
                                                    recordContextByActivity.get(
                                                        String(
                                                            activityId ||
                                                            "",
                                                        ),
                                                    );

                                                const resourceType =
                                                    recordContext?.resourceType;

                                                const destination =
                                                    recordContext?.destination;

                                                const observedValue =
                                                    observation?.valor !==
                                                        null &&
                                                        observation?.valor !==
                                                        undefined
                                                        ? `${formatNumber(
                                                            observation.valor,
                                                        )} ${observation.unidad || ""}`.trim()
                                                        : observation?.valor_texto ||
                                                        "Sin valor";

                                                return (
                                                    <tr
                                                        key={
                                                            item.id
                                                        }
                                                    >
                                                        <TableCell>
                                                            <b>
                                                                {[
                                                                    resourceType
                                                                        ? resourceLabel(
                                                                            resourceType,
                                                                        )
                                                                        : null,

                                                                    observedValue,

                                                                    destination
                                                                        ? human(
                                                                            destination,
                                                                        )
                                                                        : null,
                                                                ]
                                                                    .filter(Boolean)
                                                                    .join(" · ")}
                                                            </b>

                                                            <span className="
        block text-xs
        text-[var(--text-muted)]
    ">
                                                                {human(
                                                                    observation?.concepto,
                                                                )}
                                                            </span>
                                                        </TableCell>

                                                        <TableCell>
                                                            <StatusBadge
                                                                tone={qualityTone(
                                                                    item.estado,
                                                                )}
                                                            >
                                                                {human(
                                                                    item.estado,
                                                                )}
                                                            </StatusBadge>
                                                            <span className="mt-1 block max-w-xs text-xs text-[var(--text-muted)]">
                                                                {item.motivos?.join(" ")}
                                                            </span>
                                                            <span className="mt-1 block text-xs text-[var(--text-muted)]">
                                                                Estado del dato: {human(observation?.estado)}
                                                            </span>
                                                        </TableCell>

                                                        <TableCell>
                                                            <DocumentaryValidation evidence={observation?.evidencia} />
                                                        </TableCell>

                                                        <TableCell>
                                                            {observation?.fuente?.nombre}
                                                            <span className="block text-xs text-[var(--text-muted)]">
                                                                Captura {human(observation?.metodo_captura)}
                                                            </span>
                                                        </TableCell>

                                                        <TableCell>
                                                            {formatDateTime(
                                                                item.fecha_evaluacion,
                                                            )}
                                                        </TableCell>
                                                    </tr>
                                                );
                                            },
                                        )}
                                    </TableBody>
                                </TableShell>
                            </div>
                        )}
                </>
            )}

            <Modal
                open={Boolean(
                    resolution,
                )}
                title="Resolver discrepancia"
                description="Selecciona explícitamente qué observación será utilizada y documenta el criterio de decisión."
                onClose={() =>
                    setResolution(
                        null,
                    )
                }
            >
                {resolution && (
                    <div className="space-y-4">
                        <Select
                            label="Observación seleccionada"
                            value={
                                resolution.observationId
                            }
                            onChange={(
                                event,
                            ) =>
                                setResolution(
                                    (
                                        current,
                                    ) => ({
                                        ...current,

                                        observationId:
                                            event
                                                .target
                                                .value,
                                    }),
                                )
                            }
                        >
                            <option value="">
                                Seleccionar
                            </option>

                            {resolution.observations.map(
                                (
                                    observation,
                                ) => (
                                    <option
                                        key={
                                            observation.id
                                        }
                                        value={
                                            observation.id
                                        }
                                    >
                                        {
                                            observation
                                                .fuente
                                                ?.nombre
                                        }
                                        {" · "}
                                        {observation.valor !==
                                            null
                                            ? `${observation.valor} ${observation.unidad || ""}`
                                            : observation.valor_texto}
                                    </option>
                                ),
                            )}
                        </Select>

                        <Input
                            label="Criterio de resolución"
                            value={
                                resolution.text
                            }
                            onChange={(
                                event,
                            ) =>
                                setResolution(
                                    (
                                        current,
                                    ) => ({
                                        ...current,

                                        text:
                                            event
                                                .target
                                                .value,
                                    }),
                                )
                            }
                        />

                        <div className="flex justify-end gap-2">
                            <Button
                                variant="secondary"
                                onClick={() =>
                                    setResolution(
                                        null,
                                    )
                                }
                            >
                                Cancelar
                            </Button>

                            <Button
                                disabled={
                                    busy ||
                                    !resolution.observationId ||
                                    !resolution.text.trim()
                                }
                                onClick={
                                    resolve
                                }
                            >
                                Confirmar resolución
                            </Button>
                        </div>
                    </div>
                )}
            </Modal>
        </section>
    );
}
