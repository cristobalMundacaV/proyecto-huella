import {
    useEffect,
    useLayoutEffect,
    useRef,
    useState,
} from "react";

import {
    Plus,
    Trash2,
} from "lucide-react";

import {
    useOutletContext,
    useParams,
} from "react-router-dom";

import { useAuth } from "@/features/auth/context/AuthContext";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
    Alert,
    Button,
    Card,
    CardContent,
    EmptyState,
    ErrorState,
    Input,
    LoadingState,
    SectionHeader,
    Select,
    StatusBadge,
    Textarea,
} from "@/shared/ui";

import WorkApplicability from "../components/WorkApplicability";

import {
    saveDiagnostico,
} from "../api/diagnosticoApi";

import {
    useDiagnostico,
} from "../hooks/useDiagnostico";

const STATES = [
    ["pendiente", "Pendiente"],
    ["en_progreso", "En progreso"],
    ["completado", "Completado"],
    [
        "requiere_actualizacion",
        "Requiere actualización",
    ],
];

const GROUPS = [
    [
        "proceso",
        "Procesos identificados",
    ],
    [
        "informacion_disponible",
        "Información disponible",
    ],
    [
        "informacion_faltante",
        "Información pendiente",
    ],
    [
        "fuente",
        "Fuentes conocidas",
    ],
    [
        "brecha",
        "Brechas de contexto",
    ],
];

const emptyForm = {
    estado: "pendiente",
    objetivo_principal: "",
    descripcion_contexto: "",
    observaciones: "",
};

const keyFor = (item) =>
    item.id
        ? `id-${item.id}`
        : item.localId;

const statusTone = (value) =>
    value === "completado"
        ? "success"
        : value ===
            "requiere_actualizacion"
            ? "warning"
            : "neutral";

export default function WorkDiagnosticPage() {
    const { obraId } = useParams();

    const workspace =
        useOutletContext();

    const { user } = useAuth();

    const {
        activeOrganizacionId,
    } = useOrganizacionActiva();

    const state = useDiagnostico(
        activeOrganizacionId,
        obraId,
    );

    const [
        form,
        setForm,
    ] = useState(emptyForm);

    const [
        elementos,
        setElementos,
    ] = useState([]);

    const [
        dirtyItems,
        setDirtyItems,
    ] = useState(
        () => new Set(),
    );

    const [
        deletedIds,
        setDeletedIds,
    ] = useState([]);

    const [
        formDirty,
        setFormDirty,
    ] = useState(false);

    const [
        saving,
        setSaving,
    ] = useState(false);

    const [
        mutationError,
        setMutationError,
    ] = useState("");

    const [
        success,
        setSuccess,
    ] = useState("");

    const activeScopeRef =
        useRef(
            `${activeOrganizacionId}:${obraId}`,
        );

    useLayoutEffect(() => {
        activeScopeRef.current =
            `${activeOrganizacionId}:${obraId}`;
    }, [
        activeOrganizacionId,
        obraId,
    ]);

    useEffect(() => {
        if (
            state.diagnostico
                .status !== "ready"
        ) {
            return;
        }

        const diagnostic =
            state.diagnostico.data;

        setForm(
            diagnostic
                ? {
                    estado:
                        diagnostic.estado,
                    objetivo_principal:
                        diagnostic.objetivo_principal ||
                        "",
                    descripcion_contexto:
                        diagnostic.descripcion_contexto ||
                        "",
                    observaciones:
                        diagnostic.observaciones ||
                        "",
                }
                : emptyForm,
        );

        setElementos(
            diagnostic?.elementos ||
            [],
        );

        setDirtyItems(
            new Set(),
        );

        setDeletedIds([]);

        setFormDirty(false);
    }, [
        state.diagnostico.data,
        state.diagnostico.status,
    ]);

    const setField = (
        field,
        value,
    ) => {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));

        setFormDirty(true);
        setSuccess("");
    };

    function addElement(tipo) {
        const localId =
            `new-${Date.now()}-${Math.random()}`;

        setElementos((items) => [
            ...items,
            {
                localId,
                tipo,
                nombre: "",
                descripcion: "",
            },
        ]);

        setDirtyItems(
            (current) =>
                new Set(current).add(
                    localId,
                ),
        );
    }

    function updateElement(
        item,
        field,
        value,
    ) {
        const key = keyFor(item);

        setElementos((items) =>
            items.map((current) =>
                keyFor(current) === key
                    ? {
                        ...current,
                        [field]: value,
                    }
                    : current,
            ),
        );

        setDirtyItems(
            (current) =>
                new Set(current).add(key),
        );

        setSuccess("");
    }

    function removeElement(item) {
        setElementos((items) =>
            items.filter(
                (current) =>
                    keyFor(current) !==
                    keyFor(item),
            ),
        );

        if (item.id) {
            setDeletedIds((ids) => [
                ...ids,
                item.id,
            ]);
        }

        setSuccess("");
    }

    async function save() {
        const organizationId =
            activeOrganizacionId;

        const scopeKey =
            `${organizationId}:${obraId}`;

        setSaving(true);
        setMutationError("");
        setSuccess("");

        try {
            const changed =
                elementos
                    .filter((item) =>
                        dirtyItems.has(
                            keyFor(item),
                        ),
                    )
                    .map(
                        ({
                            id,
                            tipo,
                            nombre,
                            descripcion,
                        }) => ({
                            ...(id
                                ? { id }
                                : {}),
                            tipo,
                            nombre,
                            descripcion,
                        }),
                    );

            const payload = {
                ...form,

                elementos: [
                    ...changed,

                    ...deletedIds.map(
                        (id) => ({
                            id,
                            eliminar: true,
                        }),
                    ),
                ],
            };

            await saveDiagnostico(
                organizationId,
                payload,
                Boolean(
                    state.diagnostico
                        .data,
                ),
                obraId,
            );

            if (
                activeScopeRef.current !==
                scopeKey
            ) {
                return;
            }

            await state.reload();

            setSuccess(
                "Contexto ambiental de la obra guardado.",
            );
        } catch (error) {
            setMutationError(
                error.response?.data
                    ?.error ||
                error.response?.data
                    ?.detail ||
                "No se pudo guardar el diagnóstico de la obra.",
            );
        } finally {
            setSaving(false);
        }
    }

    const scopeKey =
        activeOrganizacionId
            ? `${activeOrganizacionId}:${obraId}`
            : "";

    if (
        !activeOrganizacionId
    ) {
        return (
            <EmptyState
                title="Sin organización activa"
                description="Selecciona una organización para revisar esta obra."
            />
        );
    }

    if (
        state.scopeKey !==
        scopeKey ||
        state.diagnostico
            .status === "loading"
    ) {
        return (
            <LoadingState label="Cargando diagnóstico de la obra" />
        );
    }

    const diagnostic =
        state.diagnostico.data;

    const canSave =
        !user?.is_demo &&
        (
            formDirty ||
            dirtyItems.size >
            0 ||
            deletedIds.length >
            0
        );

    return (
        <section className="space-y-6">
            <SectionHeader
                eyebrow="CONTEXTO AMBIENTAL"
                title="Diagnóstico de la obra"
                description="Define qué ocurre en esta obra, qué información existe y qué ámbitos ambientales deben gestionarse."
            />

            <div className="grid gap-3 md:grid-cols-3">
                <Info
                    label="Obra"
                    value={
                        workspace?.obra
                            ?.nombre ||
                        "Sin datos"
                    }
                />

                <Info
                    label="Estado"
                    value={
                        diagnostic ? (
                            <StatusBadge
                                tone={statusTone(
                                    diagnostic.estado,
                                )}
                            >
                                {STATES.find(
                                    ([value]) =>
                                        value ===
                                        diagnostic.estado,
                                )?.[1] ||
                                    diagnostic.estado}
                            </StatusBadge>
                        ) : (
                            "Sin diagnóstico"
                        )
                    }
                />

                <Info
                    label="Cobertura"
                    value={
                        state.preparacion
                            .status === "ready"
                            ? state.preparacion
                                .data
                                ?.siguiente_paso ||
                            "Sin datos"
                            : "Cargando…"
                    }
                />
            </div>

            {user?.is_demo && (
                <Alert title="Solo lectura en modo demo">
                    Puedes revisar el contexto,
                    pero no modificarlo.
                </Alert>
            )}

            {mutationError && (
                <Alert tone="danger">
                    {mutationError}
                </Alert>
            )}

            {success && (
                <Alert tone="success">
                    {success}
                </Alert>
            )}

            {state.diagnostico
                .status === "error" ? (
                <ErrorState
                    description={
                        state.diagnostico
                            .error
                    }
                    onRetry={
                        state.reload
                    }
                />
            ) : (
                <Card>
                    <CardContent>
                        <div className="grid gap-4 sm:grid-cols-2">
                            <Select
                                label="Estado"
                                value={
                                    form.estado
                                }
                                disabled={
                                    user?.is_demo
                                }
                                onChange={(
                                    event,
                                ) =>
                                    setField(
                                        "estado",
                                        event.target
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
                                            key={value}
                                            value={value}
                                        >
                                            {label}
                                        </option>
                                    ),
                                )}
                            </Select>

                            <Input
                                label="Objetivo o necesidad principal"
                                value={
                                    form.objetivo_principal
                                }
                                disabled={
                                    user?.is_demo
                                }
                                onChange={(
                                    event,
                                ) =>
                                    setField(
                                        "objetivo_principal",
                                        event.target
                                            .value,
                                    )
                                }
                            />

                            <Textarea
                                label="Contexto de la obra"
                                rows={4}
                                value={
                                    form.descripcion_contexto
                                }
                                disabled={
                                    user?.is_demo
                                }
                                onChange={(
                                    event,
                                ) =>
                                    setField(
                                        "descripcion_contexto",
                                        event.target
                                            .value,
                                    )
                                }
                            />

                            <Textarea
                                label="Observaciones"
                                rows={4}
                                value={
                                    form.observaciones
                                }
                                disabled={
                                    user?.is_demo
                                }
                                onChange={(
                                    event,
                                ) =>
                                    setField(
                                        "observaciones",
                                        event.target
                                            .value,
                                    )
                                }
                            />
                        </div>
                    </CardContent>
                </Card>
            )}

            {state.diagnostico
                .status ===
                "ready" && (
                    <section className="space-y-4">
                        <div>
                            <h2 className="text-lg font-black">
                                Información disponible y pendiente
                            </h2>

                            <p className="text-sm text-[var(--text-muted)]">
                                Registra el contexto necesario para determinar qué ámbitos aplican a esta obra.
                            </p>
                        </div>

                        <div className="grid gap-4 lg:grid-cols-2">
                            {GROUPS.map(
                                ([
                                    type,
                                    title,
                                ]) => (
                                    <ElementGroup
                                        key={type}
                                        type={type}
                                        title={title}
                                        items={elementos.filter(
                                            (item) =>
                                                item.tipo ===
                                                type,
                                        )}
                                        readOnly={
                                            user?.is_demo
                                        }
                                        onAdd={
                                            addElement
                                        }
                                        onUpdate={
                                            updateElement
                                        }
                                        onRemove={
                                            removeElement
                                        }
                                    />
                                ),
                            )}
                        </div>
                    </section>
                )}

            <section className="space-y-4">
                <div>
                    <h2 className="text-lg font-black">
                        Aplicabilidad ambiental
                    </h2>

                    <p className="text-sm text-[var(--text-muted)]">
                        Define qué capacidades ambientales aplican al contexto real de esta obra.
                    </p>
                </div>

                {state.capacidades
                    .status ===
                    "loading" ? (
                    <LoadingState
                        inline
                        label="Cargando aplicabilidad"
                    />
                ) : state
                    .capacidades
                    .status ===
                    "error" ? (
                    <ErrorState
                        description={
                            state.capacidades
                                .error
                        }
                    />
                ) : !state
                    .capacidades
                    .data.length ? (
                    <EmptyState
                        title="Sin capacidades registradas"
                        description="No hay aplicabilidad disponible para mostrar."
                    />
                ) : (
                    <WorkApplicability
                        organizationId={
                            activeOrganizacionId
                        }
                        workId={obraId}
                        capabilities={
                            state.capacidades.data
                        }
                        applicability={
                            workspace?.context
                                ?.diagnostico_obra
                                ?.aplicabilidad ||
                            []
                        }
                        diagnosticExists={
                            Boolean(diagnostic)
                        }
                        readOnly={
                            user?.is_demo
                        }
                    />
                )}
            </section>

            {!user?.is_demo &&
                state.diagnostico
                    .status ===
                "ready" && (
                    <div className="flex justify-end">
                        <Button
                            loading={
                                saving
                            }
                            disabled={
                                !canSave
                            }
                            onClick={save}
                        >
                            {diagnostic
                                ? "Guardar cambios"
                                : "Guardar contexto"}
                        </Button>
                    </div>
                )}
        </section>
    );
}

function Info({
    label,
    value,
}) {
    return (
        <Card>
            <CardContent>
                <p className="text-xs font-bold uppercase text-[var(--text-muted)]">
                    {label}
                </p>

                <div className="mt-1 font-semibold">
                    {value ??
                        "Sin datos"}
                </div>
            </CardContent>
        </Card>
    );
}

function ElementGroup({
    type,
    title,
    items,
    readOnly,
    onAdd,
    onUpdate,
    onRemove,
}) {
    return (
        <Card>
            <CardContent>
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-black">
                        {title}
                    </h3>

                    {!readOnly && (
                        <Button
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                                onAdd(type)
                            }
                        >
                            <Plus
                                size={15}
                                aria-hidden="true"
                            />
                            Agregar
                        </Button>
                    )}
                </div>

                <div className="mt-4 space-y-3">
                    {!items.length && (
                        <p className="text-sm text-[var(--text-muted)]">
                            Sin información registrada.
                        </p>
                    )}

                    {items.map(
                        (item) => (
                            <div
                                key={keyFor(
                                    item,
                                )}
                                className="rounded-[var(--radius-md)] border border-[var(--border-default)] p-3"
                            >
                                <div className="flex gap-2">
                                    <input
                                        aria-label={`Nombre en ${title}`}
                                        value={
                                            item.nombre ||
                                            ""
                                        }
                                        disabled={
                                            readOnly
                                        }
                                        onChange={(
                                            event,
                                        ) =>
                                            onUpdate(
                                                item,
                                                "nombre",
                                                event
                                                    .target
                                                    .value,
                                            )
                                        }
                                        className="min-w-0 flex-1 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-sm focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-50"
                                    />

                                    {!readOnly && (
                                        <Button
                                            variant="danger"
                                            size="sm"
                                            aria-label={`Eliminar ${item.nombre || title}`}
                                            onClick={() =>
                                                onRemove(
                                                    item,
                                                )
                                            }
                                        >
                                            <Trash2
                                                size={16}
                                                aria-hidden="true"
                                            />
                                        </Button>
                                    )}
                                </div>

                                <textarea
                                    aria-label={`Descripción en ${title}`}
                                    rows={2}
                                    value={
                                        item.descripcion ||
                                        ""
                                    }
                                    disabled={
                                        readOnly
                                    }
                                    onChange={(
                                        event,
                                    ) =>
                                        onUpdate(
                                            item,
                                            "descripcion",
                                            event.target
                                                .value,
                                        )
                                    }
                                    className="mt-2 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-sm focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-50"
                                />
                            </div>
                        ),
                    )}
                </div>
            </CardContent>
        </Card>
    );
}