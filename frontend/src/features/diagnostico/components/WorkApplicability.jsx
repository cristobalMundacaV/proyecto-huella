import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    Activity,
    Droplets,
    Fuel,
    Hammer,
    PackageOpen,
    Recycle,
    ShieldCheck,
    Sun,
    Truck,
    Volume2,
    Wrench,
    Zap,
} from "lucide-react";

import {
    Alert,
    StatusBadge,
} from "@/shared/ui";

import {
    updateWorkApplicability,
} from "../api/diagnosticoApi";

const STATES = [
    ["aplica", "Aplica"],
    ["pendiente", "Revisar"],
    ["no_aplica", "No aplica"],
];

const displayState = (value) => value === "aplica" ? "aplica" : value === "no_aplica" ? "no_aplica" : "pendiente";

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

const DOMAINS = [
    { terms: ["generacion propia"], icon: Sun, style: "border-yellow-200 bg-yellow-50/55 text-yellow-700" },
    { terms: ["energia", "electric"], icon: Zap, style: "border-amber-200 bg-amber-50/55 text-amber-700" },
    { terms: ["agua", "hidric", "suelo"], icon: Droplets, style: "border-cyan-200 bg-cyan-50/55 text-cyan-700" },
    { terms: ["combust"], icon: Fuel, style: "border-orange-200 bg-orange-50/55 text-orange-700" },
    { terms: ["transporte", "ruta"], icon: Truck, style: "border-blue-200 bg-blue-50/55 text-blue-700" },
    { terms: ["maquinaria"], icon: Hammer, style: "border-slate-300 bg-slate-50 text-slate-700" },
    { terms: ["mantenimiento"], icon: Wrench, style: "border-indigo-200 bg-indigo-50/55 text-indigo-700" },
    { terms: ["material"], icon: PackageOpen, style: "border-violet-200 bg-violet-50/55 text-violet-700" },
    { terms: ["residuo"], icon: Recycle, style: "border-emerald-200 bg-emerald-50/55 text-emerald-700" },
    { terms: ["continuidad"], icon: ShieldCheck, style: "border-teal-200 bg-teal-50/55 text-teal-700" },
    { terms: ["ruido"], icon: Volume2, style: "border-rose-200 bg-rose-50/55 text-rose-700" },
];

const domainPresentation = (capability) => {
    const text = `${capability?.clave || ""} ${capability?.nombre || ""}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll("_", " ");
    return DOMAINS.find((domain) => domain.terms.some((term) => text.includes(term))) || { icon: Activity, style: "border-cyan-200 bg-cyan-50/50 text-cyan-700" };
};

export default function WorkApplicability({
    organizationId,
    workId,
    capabilities = [],
    applicability = [],
    diagnosticExists,
    readOnly = false,
    onChange,
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

    useEffect(() => {
        setLocalState(
            Object.fromEntries(
                applicability.map(
                    (item) => [
                        item.clave,
                        item.estado_obra,
                    ],
                ),
            ),
        );

        setError("");
        setSavingId(null);
    }, [
        applicability,
        organizationId,
        workId,
    ]);

    const rows = useMemo(
        () =>
            capabilities
                .filter((item) => !["no_aplica", "pendiente_diagnostico"].includes(item.estado))
                .map(
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
            onChange?.(item.capacidad.clave, estado);
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
                {!rows.length && (
                    <div className="rounded-[var(--radius-lg)] border border-emerald-200 bg-emerald-50/60 p-6 text-center md:col-span-2">
                        <p className="font-black text-emerald-900">No hay aspectos ambientales habilitados para esta organización</p>
                        <p className="mt-1 text-sm text-[var(--text-muted)]">Primero habilita los aspectos que la organización necesita gestionar.</p>
                    </div>
                )}
                {rows.map(
                    (item) => {
                        const presentation = domainPresentation(item.capacidad);
                        const DomainIcon = presentation.icon;
                        return (
                        <div
                            key={
                                item.id
                            }
                            className={`rounded-[var(--radius-lg)] border p-4 shadow-[0_12px_28px_rgba(15,23,42,0.05)] ${presentation.style}`}
                        >
                            <div className="flex flex-wrap items-center justify-between gap-3">
                                <div className="flex min-w-0 items-center gap-3">
                                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/80 shadow-sm"><DomainIcon size={21} aria-hidden="true" /></span>
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
                                </div>

                                <StatusBadge
                                    tone={tone(
                                        displayState(item.workState),
                                    )}
                                >
                                    {STATES.find(
                                        ([
                                            value,
                                        ]) =>
                                            value === displayState(item.workState),
                                    )?.[1] ||
                                        "Revisar"}
                                </StatusBadge>
                            </div>

                            {!readOnly && (
                                <fieldset className="mt-4" disabled={!diagnosticExists || savingId === item.id}>
                                    <legend className="sr-only">Aplicabilidad de {item.capacidad?.nombre || "aspecto"}</legend>
                                    <div className="grid grid-cols-3 gap-1 rounded-xl border border-white/80 bg-white/70 p-1">
                                        {STATES.map(([value, label]) => {
                                            const selected = displayState(item.workState) === value;
                                            return (
                                                <button
                                                    key={value}
                                                    type="button"
                                                    aria-pressed={selected}
                                                    onClick={() => change(item, value)}
                                                    className={`rounded-lg px-2 py-2 text-xs font-black transition disabled:cursor-not-allowed disabled:opacity-50 ${selected ? value === "aplica" ? "bg-emerald-600 text-white shadow-sm" : value === "no_aplica" ? "bg-slate-700 text-white shadow-sm" : "bg-amber-100 text-amber-900 shadow-sm" : "text-slate-600 hover:bg-white"}`}
                                                >
                                                    {label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </fieldset>
                            )}
                        </div>
                        );
                    },
                )}
            </div>
        </div>
    );
}
