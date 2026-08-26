import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    Calculator,
    CheckCircle2,
    TriangleAlert,
} from "lucide-react";

import {
    Button,
    EmptyState,
    SectionHeader,
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

import {
    calculateActivity,
    getActivityCalculations,
    getActivityEligibility,
} from "../api/calculationApi";

import {
    resourceData,
} from "../utils/operationSelectors";


const TYPES = {
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

    "emisiones-atmosfericas": [
        "monitoreo_emisiones_atmosfericas",
    ],

    suelo: [
        "gestion_suelo",
    ],

    "hidrica-suelo": [
        "gestion_hidrica_suelo",
    ],
};


function belongs(
    activity,
    domain,
) {
    return (
        TYPES[
        domain
        ] || []
    ).includes(
        activity.tipo
    );
}


export default function DomainCalculationPanel({
    domain,
    operation,
    organizationId,
    onCalculated,
}) {
    const activities =
        useMemo(
            () =>
                resourceData(
                    operation.records,
                    [],
                )
                    .map(
                        (item) =>
                            item.actividad,
                    )
                    .filter(Boolean)
                    .filter(
                        (activity) =>
                            belongs(
                                activity,
                                domain,
                            ),
                    ),
            [
                operation.records,
                domain,
            ],
        );

    const [
        rows,
        setRows,
    ] = useState([]);

    const [
        busy,
        setBusy,
    ] = useState(null);

    useEffect(
        () => {
            let active = true;

            async function load() {
                const results =
                    await Promise.all(
                        activities.map(
                            async (
                                activity,
                            ) => {
                                const [
                                    eligibility,
                                    calculations,
                                ] =
                                    await Promise.all([
                                        getActivityEligibility(
                                            organizationId,
                                            activity.id,
                                        ),

                                        getActivityCalculations(
                                            organizationId,
                                            activity.id,
                                        ),
                                    ]);

                                return {
                                    activity,
                                    eligibility,
                                    calculations,
                                };
                            },
                        ),
                    );

                if (active) {
                    setRows(
                        results
                    );
                }
            }

            if (
                organizationId &&
                activities.length
            ) {
                load();
            } else {
                setRows([]);
            }

            return () => {
                active = false;
            };
        },
        [
            activities,
            organizationId,
        ],
    );

    async function calculate(
        row,
    ) {
        setBusy(
            row.activity.id
        );

        try {
            await calculateActivity(
                organizationId,
                row.activity.id,
            );

            const calculations =
                await getActivityCalculations(
                    organizationId,
                    row.activity.id,
                );

            setRows(
                (current) =>
                    current.map(
                        (item) =>
                            item.activity.id ===
                                row.activity.id
                                ? {
                                    ...item,
                                    calculations,
                                }
                                : item,
                    ),
            );

            await onCalculated?.();
        } finally {
            setBusy(null);
        }
    }

    return (
        <section className="space-y-4">
            <SectionHeader
                eyebrow="CÁLCULO DETERMINÍSTICO"
                title="Cálculos ambientales"
                description="La metodología, los factores y los datos utilizados permanecen trazables y versionados."
            />

            {!rows.length ? (
                <EmptyState
                    icon={Calculator}
                    title="Sin actividades calculables"
                    description="Los cálculos aparecerán cuando existan actividades con datos suficientes y gobernados."
                />
            ) : (
                <TableShell>
                    <TableHead>
                        <tr>
                            <TableCell as="th">
                                Actividad
                            </TableCell>

                            <TableCell as="th">
                                Elegibilidad
                            </TableCell>

                            <TableCell as="th">
                                Método
                            </TableCell>

                            <TableCell as="th">
                                Último resultado
                            </TableCell>

                            <TableCell as="th">
                                Acción
                            </TableCell>
                        </tr>
                    </TableHead>

                    <TableBody
                        columns={5}
                    >
                        {rows.map(
                            (row) => {
                                const last =
                                    row.calculations?.[
                                    row.calculations
                                        .length -
                                    1
                                    ];

                                const selectable =
                                    Boolean(
                                        row
                                            .eligibility
                                            ?.metodologia_seleccionada,
                                    );

                                return (
                                    <tr
                                        key={
                                            row
                                                .activity
                                                .id
                                        }
                                    >
                                        <TableCell>
                                            <b>
                                                {
                                                    row
                                                        .activity
                                                        .nombre
                                                }
                                            </b>
                                        </TableCell>

                                        <TableCell>
                                            <StatusBadge
                                                tone={
                                                    selectable
                                                        ? "success"
                                                        : "warning"
                                                }
                                            >
                                                {
                                                    row
                                                        .eligibility
                                                        ?.estado
                                                }
                                            </StatusBadge>
                                        </TableCell>

                                        <TableCell>
                                            {row
                                                .eligibility
                                                ?.metodologia_seleccionada
                                                ?.nombre ||
                                                "Sin metodología"}

                                            {row
                                                .eligibility
                                                ?.metodologia_seleccionada
                                                ?.version && (
                                                    <span className="block text-xs text-[var(--text-muted)]">
                                                        v
                                                        {
                                                            row
                                                                .eligibility
                                                                .metodologia_seleccionada
                                                                .version
                                                        }
                                                    </span>
                                                )}
                                        </TableCell>

                                        <TableCell>
                                            {last ? (
                                                <>
                                                    <b>
                                                        {formatNumber(
                                                            last.resultado,
                                                        )}{" "}
                                                        {
                                                            last.unidad_resultado
                                                        }
                                                    </b>

                                                    <span className="block text-xs text-[var(--text-muted)]">
                                                        {formatDateTime(
                                                            last.fecha_calculo,
                                                        )}
                                                    </span>
                                                </>
                                            ) : (
                                                "Sin cálculo"
                                            )}
                                        </TableCell>

                                        <TableCell>
                                            {selectable ? (
                                                <Button
                                                    variant="secondary"
                                                    disabled={
                                                        busy ===
                                                        row
                                                            .activity
                                                            .id
                                                    }
                                                    onClick={() =>
                                                        calculate(
                                                            row,
                                                        )
                                                    }
                                                >
                                                    <CheckCircle2
                                                        size={
                                                            16
                                                        }
                                                    />

                                                    Calcular
                                                </Button>
                                            ) : (
                                                <span className="flex items-center gap-1 text-sm text-[var(--text-muted)]">
                                                    <TriangleAlert
                                                        size={
                                                            15
                                                        }
                                                    />

                                                    Faltan datos
                                                </span>
                                            )}
                                        </TableCell>
                                    </tr>
                                );
                            },
                        )}
                    </TableBody>
                </TableShell>
            )}
        </section>
    );
}
