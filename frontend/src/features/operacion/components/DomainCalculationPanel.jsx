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
    calculationMethodologyPresentation,
    domainActivities,
    isCalculationSelectable,
    resourceData,
} from "../utils/operationSelectors";
import { eligibilityPresentation } from "../utils/operationalPresentation";


export default function DomainCalculationPanel({
    domain,
    operation,
    organizationId,
    onCalculated,
}) {
    const activities =
        useMemo(
            () =>
                domainActivities(
                    resourceData(operation.records, []),
                    domain,
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
                                const [eligibilityResult, calculationsResult] =
                                    await Promise.allSettled([
                                        getActivityEligibility(
                                            organizationId,
                                            activity.id,
                                        ),

                                        getActivityCalculations(
                                            organizationId,
                                            activity.id,
                                        ),
                                    ]);

                                const eligibility = eligibilityResult.status === "fulfilled"
                                    ? eligibilityResult.value
                                    : {
                                        estado: "no_calculable",
                                        razon: "No fue posible evaluar esta actividad.",
                                        motivos: [eligibilityResult.reason?.response?.data?.detail || "La elegibilidad no está disponible."],
                                    };
                                return {
                                    activity,
                                    eligibility,
                                    calculations: calculationsResult.status === "fulfilled" ? calculationsResult.value : [],
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

            {!activities.length ? (
                <EmptyState
                    icon={Calculator}
                    title="Sin actividades para evaluar"
                    description="No existen actividades registradas en este dominio para evaluar."
                />
            ) : !rows.length ? (
                <p className="text-sm text-[var(--text-muted)]">Evaluando elegibilidad y factores aplicables...</p>
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

                                const selectable = isCalculationSelectable(
                                    row.eligibility,
                                );
                                const methodology = calculationMethodologyPresentation(
                                    row.eligibility,
                                );
                                const eligibilityStatus = eligibilityPresentation(
                                    row.eligibility,
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
                                                tone={eligibilityStatus.tone}
                                            >
                                                {eligibilityStatus.label}
                                            </StatusBadge>
                                            <span className="mt-1 block max-w-xs text-xs text-[var(--text-muted)]">
                                                {eligibilityStatus.message}
                                            </span>
                                        </TableCell>

                                        <TableCell>
                                            {methodology.methodology?.nombre || methodology.label}

                                            {methodology.methodology?.version && (
                                                    <span className="block text-xs text-[var(--text-muted)]">
                                                        v
                                                        {methodology.methodology.version}
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

                                                    {eligibilityStatus.label}
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
