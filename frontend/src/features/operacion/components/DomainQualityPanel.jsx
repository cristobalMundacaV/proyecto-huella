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


const ACTIVITY_TYPES = {
    energia: [
        "consumo_energia",
        "generacion_energia",
    ],

    agua: [
        "consumo_agua",
    ],

    combustibles: [
        "consumo_combustible_estacionario",
    ],

    transporte: [
        "transporte",
    ],

    materiales: [
        "movimiento_material",
    ],

    residuos: [
        "gestion_residuo",
    ],

    ruido: [
        "monitoreo_ruido",
    ],

    "hidrica-suelo": [
        "gestion_hidrica_suelo",
    ],
};


function belongsToDomain(
    type,
    domain,
) {
    return (
        ACTIVITY_TYPES[
        domain
        ] || []
    ).includes(type);
}


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


export default function DomainQualityPanel({
    domain,
    organizationId,
    workId,
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
                        belongsToDomain(
                            item
                                .observacion_detalle
                                ?.actividad
                                ?.tipo,
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
                        belongsToDomain(
                            item
                                .actividad_detalle
                                ?.tipo,
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

            <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border p-4">
                    <div className="flex items-center gap-2">
                        <ShieldCheck
                            size={18}
                        />

                        <b>
                            {
                                quality.length
                            }{" "}
                            evaluados
                        </b>
                    </div>
                </div>

                <div className="rounded-2xl border p-4">
                    <div className="flex items-center gap-2">
                        <AlertTriangle
                            size={18}
                        />

                        <b>
                            {
                                reviewCount
                            }{" "}
                            requieren atención
                        </b>
                    </div>
                </div>

                <div className="rounded-2xl border p-4">
                    <div className="flex items-center gap-2">
                        <CheckCircle2
                            size={18}
                        />

                        <b>
                            {
                                openDiscrepancies.length
                            }{" "}
                            discrepancias abiertas
                        </b>
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
                                                Fuente
                                            </TableCell>

                                            <TableCell as="th">
                                                Captura
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

                                                return (
                                                    <tr
                                                        key={
                                                            item.id
                                                        }
                                                    >
                                                        <TableCell>
                                                            <b>
                                                                {human(
                                                                    observation?.concepto,
                                                                )}
                                                            </b>

                                                            <span className="block text-xs text-[var(--text-muted)]">
                                                                {observation?.valor !==
                                                                    null &&
                                                                    observation?.valor !==
                                                                    undefined
                                                                    ? `${formatNumber(
                                                                        observation.valor,
                                                                    )} ${observation.unidad || ""}`
                                                                    : observation?.valor_texto ||
                                                                    "Sin valor"}
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
                                                        </TableCell>

                                                        <TableCell>
                                                            {
                                                                observation
                                                                    ?.fuente
                                                                    ?.nombre
                                                            }

                                                            <span className="block text-xs text-[var(--text-muted)]">
                                                                {human(
                                                                    observation
                                                                        ?.fuente
                                                                        ?.tipo,
                                                                )}
                                                            </span>
                                                        </TableCell>

                                                        <TableCell>
                                                            {human(
                                                                observation?.metodo_captura,
                                                            )}
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