import {
    useEffect,
    useMemo,
    useRef,
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
    Button,
    StatusBadge,
} from "@/shared/ui";

import { Link } from "react-router-dom";
import Toast from "@/shared/components/Toast";

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

    const [toast, setToast] = useState(null);
    const toastSequenceRef = useRef(0);
    const showToast = (value) => {
        toastSequenceRef.current += 1;
        setToast({ ...value, id: toastSequenceRef.current });
    };

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

        setToast(null);
        setSavingId(null);
    }, [
        applicability,
        organizationId,
        workId,
    ]);

    const rows = useMemo(
        () =>
            capabilities
                .filter((item) => item.estado !== "no_aplica")
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
        setToast(null);

        try {
            const updated = await updateWorkApplicability(
                organizationId,
                workId,
                item.capacidad.id,
                estado,
            );

            const persistedState = updated.estado;
            setLocalState(
                (current) => ({
                    ...current,
                    [item.capacidad
                        .clave]:
                        persistedState,
                }),
            );
            onChange?.(item.capacidad.clave, persistedState);
            window.dispatchEvent(new CustomEvent("carbono-zero:work-applicability-updated", {
                detail: { organizationId, workId, key: item.capacidad.clave, estado: persistedState },
            }));
            showToast({ message: "Aspecto actualizado", subtitle: `${item.capacidad.nombre} quedó marcado como ${STATES.find(([value]) => value === displayState(persistedState))?.[1] || persistedState}.` });
        } catch (requestError) {
            showToast({ tone: "error", message: "No pudimos actualizar el aspecto", subtitle: requestError.response?.data?.detail || requestError.response?.data?.estado?.[0] || "Inténtalo nuevamente." });
        } finally {
            setSavingId(null);
        }
    }

    async function useOrganizationConfiguration() {
        setSavingId("all");
        setToast(null);

        try {
            const updates = await Promise.all(rows.map((item) => updateWorkApplicability(
                organizationId,
                workId,
                item.capacidad.id,
                "aplica",
            )));

            const inherited = Object.fromEntries(rows.map((item, index) => [item.capacidad.clave, updates[index].estado]));
            setLocalState((current) => ({ ...current, ...inherited }));
            rows.forEach((item) => {
                const key = item.capacidad.clave;
                onChange?.(key, inherited[key]);
                window.dispatchEvent(new CustomEvent("carbono-zero:work-applicability-updated", {
                    detail: { organizationId, workId, key, estado: inherited[key] },
                }));
            });
            showToast({ message: "Configuración aplicada", subtitle: "Se heredaron los aspectos ambientales de la organización." });
        } catch (requestError) {
            showToast({ tone: "error", message: "No pudimos aplicar la configuración", subtitle: requestError.response?.data?.detail || "Inténtalo nuevamente." });
        } finally {
            setSavingId(null);
        }
    }

    return (
        <div className="space-y-3">
            <Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} />
            {!diagnosticExists && (
                <Alert>
                    Guarda primero el contexto de la obra para definir su aplicabilidad ambiental.
                </Alert>
            )}

            {rows.length > 0 && !readOnly && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-emerald-200 bg-emerald-50/55 p-4">
                    <div>
                        <p className="font-black text-emerald-950">Propuesta inicial</p>
                        <p className="mt-1 text-sm text-slate-600">Puedes heredar la configuración de la organización y ajustar cada aspecto antes de finalizar.</p>
                    </div>
                    <Button variant="secondary" loading={savingId === "all"} disabled={!diagnosticExists} onClick={useOrganizationConfiguration}>
                        {savingId === "all" ? "Aplicando configuración..." : "Usar configuración de la organización"}
                    </Button>
                </div>
            )}

            <div className="grid gap-3 md:grid-cols-2">
                {!rows.length && (
                    <div className="rounded-[var(--radius-lg)] border border-emerald-200 bg-emerald-50/60 p-6 text-center md:col-span-2">
                        <p className="font-black text-emerald-900">Tu organización aún no tiene aspectos ambientales configurados</p>
                        <p className="mt-1 text-sm text-[var(--text-muted)]">Configura primero el universo ambiental de la organización para heredarlo en esta obra.</p>
                        <Link to="/administracion/estructura-operacional" className="mt-4 inline-flex min-h-10 items-center rounded-xl bg-emerald-700 px-4 text-sm font-black text-white shadow-sm hover:bg-emerald-800">
                            Configurar aspectos de la organización
                        </Link>
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
                                <fieldset className="mt-4" disabled={!diagnosticExists || savingId === item.id || savingId === "all"}>
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
                                                    className={`rounded-lg border px-2 py-2 text-xs font-black transition disabled:cursor-not-allowed disabled:opacity-50 ${selected ? value === "aplica" ? "border-emerald-200 bg-emerald-50 text-emerald-800 shadow-sm" : value === "no_aplica" ? "border-slate-200 bg-slate-100 text-slate-700 shadow-sm" : "border-slate-300 bg-white text-slate-800 shadow-sm ring-1 ring-slate-200" : "border-transparent text-slate-600 hover:border-slate-200 hover:bg-white"}`}
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
