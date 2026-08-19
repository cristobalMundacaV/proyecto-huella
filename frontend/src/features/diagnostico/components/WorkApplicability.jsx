import {
    useMemo,
    useState,
} from "react";

import {
    Alert,
    Select,
    StatusBadge,
} from "@/shared/ui";

import {
    updateWorkApplicability,
} from "../api/diagnosticoApi";

const STATES = [
    [
        "no_determinado",
        "Por definir",
    ],
    [
        "pendiente",
        "Pendiente",
    ],
    [
        "aplica",
        "Aplica",
    ],
    [
        "no_aplica",
        "No aplica",
    ],
    [
        "sin_datos",
        "Sin datos",
    ],
];

const tone = (value) =>
    value === "aplica"
        ? "success"
        : [
            "pendiente",
            "no_determinado",
            "sin_datos",
        ].includes(value)
            ? "warning"
            : "neutral";

export default function WorkApplicability({
    organizationId,
    workId,
    capabilities = [],
    applicability = [],
    diagnosticExists,
    readOnly = false,
}) {
    const [
        localState,
        setLocalState,
    ] = useState(() =>
        Object.fromEntries(
            applicability.map(
                (item) => [
                    item.clave,
                    item.estado_obra,
                ],
            ),
        ),
    );

    const [
        savingId,
        setSavingId,
    ] = useState(null);

    const [
        error,
        setError,
    ] = useState("");

    const rows = useMemo(
        () =>
            capabilities.map(
                (item) => ({
                    ...item,
                    workState:
                        localState[
                        item.capacidad
                            ?.clave
                        ] ||
                        "no_determinado",
                }),
            ),
        [
            capabilities,
            localState,
        ],
    );

    async function change(
        item,
        estado,
    ) {
        setSavingId(item.id);
        setError("");

        try {
            await updateWorkApplicability(
                organizationId,
                workId,
                item.capacidad.id,
                estado,
            );

            setLocalState(
                (current) => ({
                    ...current,
                    [item.capacidad
                        .clave]:
                        estado,
                }),
            );
        } catch (requestError) {
            setError(
                requestError
                    .response?.data
                    ?.detail ||
                requestError
                    .response?.data
                    ?.estado?.[0] ||
                "No se pudo actualizar la aplicabilidad de esta obra.",
            );
        } finally {
            setSavingId(null);
        }
    }

    return (
        <div className="space-y-3">
            {!diagnosticExists && (
                <Alert>
                    Guarda primero el contexto de la obra para definir su aplicabilidad ambiental.
                </Alert>
            )}

            {error && (
                <Alert tone="danger">
                    {error}
                </Alert>
            )}

            <div className="grid gap-3 md:grid-cols-2">
                {rows.map(
                    (item) => (
                        <div
                            key={
                                item.id
                            }
                            className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-4"
                        >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <h3 className="font-black">
                                        {item
                                            .capacidad
                                            ?.nombre ||
                                            "Capacidad"}
                                    </h3>

                                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                                        Aplicabilidad específica de esta obra.
                                    </p>
                                </div>

                                <StatusBadge
                                    tone={tone(
                                        item.workState,
                                    )}
                                >
                                    {STATES.find(
                                        ([
                                            value,
                                        ]) =>
                                            value ===
                                            item.workState,
                                    )?.[1] ||
                                        item.workState}
                                </StatusBadge>
                            </div>

                            {!readOnly && (
                                <div className="mt-4">
                                    <Select
                                        label={`Aplicabilidad de ${item.capacidad?.nombre || "capacidad"}`}
                                        value={
                                            item.workState
                                        }
                                        disabled={
                                            !diagnosticExists ||
                                            savingId ===
                                            item.id
                                        }
                                        onChange={(
                                            event,
                                        ) =>
                                            change(
                                                item,
                                                event
                                                    .target
                                                    .value,
                                            )
                                        }
                                    >
                                        {STATES.map(
                                            ([
                                                value,
                                                label,
                                            ]) => (
                                                <option
                                                    key={
                                                        value
                                                    }
                                                    value={
                                                        value
                                                    }
                                                >
                                                    {
                                                        label
                                                    }
                                                </option>
                                            ),
                                        )}
                                    </Select>
                                </div>
                            )}
                        </div>
                    ),
                )}
            </div>
        </div>
    );
}
