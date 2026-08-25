import {
    useEffect,
    useLayoutEffect,
    useRef,
    useState,
} from "react";

import {
    Building2,
    Check,
    CircleHelp,
    ClipboardCheck,
    Gauge,
} from "lucide-react";

import {
    useOutletContext,
    useNavigate,
    useParams,
} from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useAuth } from "@/features/auth/context/AuthContext";
import { usePermissions } from "@/features/auth/hooks/usePermissions";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
    Alert,
    Button,
    Card,
    CardContent,
    EmptyState,
    ErrorState,
    Input,
    SectionHeader,
    Select,
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

const STEPS = ["Contexto", "Aplicabilidad", "Resumen"];

const emptyForm = {
    estado: "pendiente",
    objetivo_principal: "",
    descripcion_contexto: "",
    observaciones: "",
};

const STATE_STYLES = {
    completado: "text-emerald-700",
    en_progreso: "text-amber-700",
    pendiente: "text-amber-700",
    requiere_actualizacion: "text-rose-700",
};

const PROFILE_LABELS = {
    edificacion: "Edificación",
    construccion: "Construcción",
    infraestructura: "Infraestructura",
    industrial: "Industrial",
};

const profileLabel = (value) => PROFILE_LABELS[value] || String(value || "Sin datos").replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

const TONE_STYLES = {
    amber: { card: "border-amber-200 bg-amber-50/55", icon: "bg-amber-100 text-amber-700", item: "border-amber-100 bg-white/85" },
    blue: { card: "border-blue-200 bg-blue-50/50", icon: "bg-blue-100 text-blue-700", item: "border-blue-100 bg-white/85" },
    cyan: { card: "border-cyan-200 bg-cyan-50/50", icon: "bg-cyan-100 text-cyan-800", item: "border-cyan-100 bg-white/85" },
    green: { card: "border-emerald-200 bg-emerald-50/55", icon: "bg-emerald-100 text-emerald-700", item: "border-emerald-100 bg-white/85" },
    rose: { card: "border-rose-200 bg-rose-50/50", icon: "bg-rose-100 text-rose-700", item: "border-rose-100 bg-white/85" },
};

export default function WorkDiagnosticPage() {
    const { can } = usePermissions();
    const canManageProfile = can("environmental_profile.manage");
    const canManageApplicability = can("environmental_profile.applicability_manage");
    const { obraId } = useParams();
    const navigate = useNavigate();

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

    const [
        activeStep,
        setActiveStep,
    ] = useState(0);

    const [
        applicabilityState,
        setApplicabilityState,
    ] = useState({});

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

        setFormDirty(false);
    }, [
        state.diagnostico.data,
        state.diagnostico.status,
    ]);

    useEffect(() => {
        const applicability = workspace?.context?.diagnostico_obra?.aplicabilidad || [];
        setApplicabilityState(Object.fromEntries(applicability.map((item) => [item.clave, item.estado_obra])));
    }, [workspace?.context?.diagnostico_obra?.aplicabilidad]);

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

    async function save(overrides = {}) {
        const organizationId =
            activeOrganizacionId;

        const scopeKey =
            `${organizationId}:${obraId}`;

        setSaving(true);
        setMutationError("");
        setSuccess("");

        try {
            const payload = {
                ...form,
                ...overrides,
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
                return false;
            }

            await state.reload();

            if (overrides.estado) {
                setForm((current) => ({ ...current, estado: overrides.estado }));
            }

            setSuccess(
                "Contexto ambiental de la obra guardado.",
            );
            return true;
        } catch (error) {
            setMutationError(
                error.response?.data
                    ?.error ||
                error.response?.data
                    ?.detail ||
                "No se pudo guardar el perfil ambiental de la obra.",
            );
            return false;
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
            <PlatformLoader
                title="Preparando perfil ambiental"
                description="Estamos cargando el contexto y la configuración ambiental de esta obra."
            />
        );
    }

    const diagnostic =
        state.diagnostico.data;

    const canSave =
        !user?.is_demo &&
        formDirty;

    const diagnosticState = diagnostic?.estado || "pendiente";
    const diagnosticStateLabel = diagnostic
        ? STATES.find(([value]) => value === diagnosticState)?.[1] || diagnosticState
        : "Perfil sin configurar";
    const workProfile = workspace?.obra?.perfil_ambiental || workspace?.obra?.perfil || workspace?.obra?.tipo_obra;
    const coverage = state.preparacion.status === "ready"
        ? state.preparacion.data?.siguiente_paso || "Sin datos"
        : "Cargando…";
    const workApplicability = workspace?.context?.diagnostico_obra?.aplicabilidad || [];
    const enabledCapabilityKeys = new Set(
        state.capacidades.data
            .filter((item) => item.estado !== "no_aplica")
            .map((item) => item.capacidad?.clave),
    );
    const enabledStates = Object.entries(applicabilityState).filter(([key]) => enabledCapabilityKeys.has(key));
    const applicableAspects = enabledStates.filter(([, value]) => value === "aplica").length;
    const nonApplicableAspects = enabledStates.filter(([, value]) => value === "no_aplica").length;
    const aspectsToReview = enabledStates.length - applicableAspects - nonApplicableAspects;
    const hasRegisteredContext = Boolean(form.objetivo_principal.trim() || form.descripcion_contexto.trim() || form.observaciones.trim());

    return (
        <section className="space-y-6">
            <SectionHeader
                eyebrow="CONTEXTO AMBIENTAL"
                title="Perfil ambiental de la obra"
                description="Define el contexto ambiental de esta obra y determina qué ámbitos deben formar parte de su gestión."
            />

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <Info
                    label="Obra"
                    icon={Building2}
                    tone="cyan"
                    value={
                        workspace?.obra
                            ?.nombre ||
                        "Sin datos"
                    }
                />

                <Info
                    label="Estado"
                    icon={Gauge}
                    tone={diagnosticState === "completado" ? "green" : diagnosticState === "requiere_actualizacion" ? "rose" : "amber"}
                    value={diagnosticStateLabel}
                    valueClassName={STATE_STYLES[diagnosticState] || "text-slate-700"}
                />

                <Info
                    label="Cobertura"
                    icon={CircleHelp}
                    tone={diagnosticState === "completado" ? "green" : "amber"}
                    value={coverage}
                    emphasis={diagnosticState !== "completado"}
                />

                <Info
                    label="Perfil ambiental"
                    icon={ClipboardCheck}
                    tone="blue"
                    value={profileLabel(workProfile)}
                    valueClassName="text-blue-800"
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

            <nav aria-label="Etapas del perfil ambiental" className="grid gap-2 rounded-[var(--radius-lg)] border border-emerald-100 bg-emerald-50/45 p-2 sm:grid-cols-3">
                {STEPS.map((step, index) => (
                    <button
                        key={step}
                        type="button"
                        onClick={() => setActiveStep(index)}
                        className={`flex min-h-12 items-center gap-3 rounded-[var(--radius-md)] px-3 text-left text-sm font-black transition ${activeStep === index ? "bg-white text-emerald-800 shadow-sm ring-1 ring-emerald-200" : "text-slate-600 hover:bg-white/70"}`}
                    >
                        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs ${activeStep > index ? "bg-emerald-600 text-white" : activeStep === index ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"}`}>
                            {activeStep > index ? <Check size={14} aria-hidden="true" /> : index + 1}
                        </span>
                        {step}
                    </button>
                ))}
            </nav>

            {activeStep === 0 && (state.diagnostico
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
                <Card className="border-emerald-100 bg-[linear-gradient(135deg,rgba(236,253,245,0.62),rgba(255,255,255,0.98))] shadow-[0_16px_38px_rgba(15,23,42,0.06)]">
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
                                label="Objetivo ambiental de esta obra"
                                placeholder="Ej.: Consolidar consumos, residuos y emisiones para detectar desviaciones y mantener trazabilidad mensual."
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
                                label="Contexto operacional de la obra"
                                placeholder="Ej.: Obra habitacional en etapa de obra gruesa, con excavaciones, transporte de materiales, maquinaria, consumo de combustibles y generación de residuos."
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
                                label="Condiciones, restricciones o antecedentes relevantes"
                                placeholder="Ej.: Faena cercana a sector residencial, restricciones horarias, retiro de residuos mediante terceros y maquinaria subcontratada."
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
            ))}

            {activeStep === 1 && <section className="space-y-4">
                <div>
                        <h2 className="text-lg font-black">Aspectos ambientales de esta obra</h2>

                    <p className="text-sm text-[var(--text-muted)]">
                        Estos aspectos provienen de la configuración de tu organización. Confirma cuáles aplican realmente en esta obra.
                    </p>
                </div>

                {state.capacidades
                    .status ===
                    "loading" ? (
                    <ApplicabilitySkeleton />
                ) : state
                    .capacidades
                    .status ===
                    "error" ? (
                    <ErrorState
                        title="No pudimos cargar la configuración ambiental"
                        description={
                            state.capacidades
                                .error
                        }
                        onRetry={state.reload}
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
                        applicability={workApplicability}
                        onChange={(key, value) => setApplicabilityState((current) => ({ ...current, [key]: value }))}
                        diagnosticExists={
                            Boolean(diagnostic)
                        }
                        readOnly={
                            user?.is_demo || !canManageApplicability
                        }
                    />
                )}
            </section>}

            {activeStep === 2 && (
                <section className="space-y-4">
                    <div>
                        <h2 className="text-lg font-black">Resumen del perfil</h2>
                        <p className="text-sm text-[var(--text-muted)]">Una lectura breve del contexto registrado y de la gestión ambiental confirmada.</p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        <SummaryMetric label="Contexto registrado" value={hasRegisteredContext ? "Sí" : "Pendiente"} tone={hasRegisteredContext ? "green" : "amber"} />
                        <SummaryMetric label="Aspectos aplicables" value={applicableAspects} tone="green" />
                        <SummaryMetric label="Aspectos por revisar" value={aspectsToReview} tone="amber" />
                        <SummaryMetric label="Aspectos no aplicables" value={nonApplicableAspects} />
                    </div>

                    <div className="rounded-[var(--radius-lg)] border border-emerald-200 bg-emerald-50/65 p-5">
                        <p className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">Próximo paso recomendado</p>
                        <p className="mt-2 font-black text-slate-900">
                            {applicableAspects === 0
                                ? "Confirma al menos un aspecto ambiental aplicable a esta obra."
                                : "Comenzar a incorporar información real de la obra."}
                        </p>
                        <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">Carbono Zero irá enriqueciendo este perfil con datos y evidencias reales, sin extender este levantamiento inicial.</p>
                    </div>
                </section>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border-default)] pt-5">
                <Button variant="secondary" disabled={activeStep === 0 || saving} onClick={() => setActiveStep((step) => Math.max(0, step - 1))}>
                    Anterior
                </Button>

                <div className="flex flex-wrap justify-end gap-2">
                    {!user?.is_demo && canManageProfile && state.diagnostico.status === "ready" && activeStep === 0 && canSave && (
                        <Button variant="secondary" loading={saving} onClick={save}>Guardar cambios</Button>
                    )}
                    {activeStep < STEPS.length - 1 && (
                        <Button
                            loading={saving}
                            onClick={async () => {
                                if (activeStep === 0 && (canSave || !diagnostic)) {
                                    const saved = await save();
                                    if (!saved) return;
                                }
                                setActiveStep((step) => Math.min(STEPS.length - 1, step + 1));
                            }}
                        >
                            {activeStep === 0 ? "Guardar y continuar" : "Continuar"}
                        </Button>
                    )}
                    {activeStep === STEPS.length - 1 && !user?.is_demo && canManageProfile && (
                        <Button
                            loading={saving}
                            disabled={!diagnostic}
                            onClick={async () => {
                                const saved = await save({ estado: "completado" });
                                if (saved) navigate(`/obras/${obraId}/resumen`, { replace: true });
                            }}
                        >
                            Finalizar perfil
                        </Button>
                    )}
                </div>
            </div>
        </section>
    );
}
function SummaryMetric({ label, value, tone = "slate" }) {
    const tones = {
        slate: "border-slate-200 bg-slate-50 text-slate-900",
        amber: "border-amber-200 bg-amber-50 text-amber-900",
        green: "border-emerald-200 bg-emerald-50 text-emerald-900",
    };
    return (
        <div className={`rounded-[var(--radius-lg)] border p-5 ${tones[tone]}`}>
            <p className="text-3xl font-black">{value}</p>
            <p className="mt-1 text-sm font-bold">{label}</p>
        </div>
    );
}

function ApplicabilitySkeleton() {
    return (
        <div aria-label="Cargando aspectos ambientales" role="status" className="rounded-[var(--radius-lg)] border border-emerald-100 bg-emerald-50/35 p-4">
            <div className="mb-4 h-4 w-52 animate-pulse rounded-full bg-emerald-100" />
            <div className="grid gap-3 md:grid-cols-2">
                {[0, 1, 2, 3].map((item) => (
                    <div key={item} className="flex min-h-24 animate-pulse items-center gap-3 rounded-[var(--radius-lg)] border border-slate-200 bg-white p-4">
                        <span className="h-11 w-11 rounded-xl bg-slate-100" />
                        <span className="h-4 w-40 rounded-full bg-slate-100" />
                    </div>
                ))}
            </div>
        </div>
    );
}

function Info({ label, value, icon: Icon, tone = "cyan", valueClassName = "text-[var(--text-primary)]", emphasis = false }) {
    const styles = TONE_STYLES[tone] || TONE_STYLES.cyan;
    return (
        <Card className={`${styles.card} overflow-hidden shadow-[0_14px_34px_rgba(15,23,42,0.07)]`}>
            <CardContent className="flex min-h-40 flex-col items-center justify-center text-center">
                {Icon && <span className={`mb-3 flex h-11 w-11 items-center justify-center rounded-2xl ${styles.icon}`}><Icon size={21} aria-hidden="true" /></span>}
                <p className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
                    {label}
                </p>

                <div className={`mt-2 text-xl font-black leading-tight ${valueClassName} ${emphasis ? "max-w-[18rem] text-amber-800" : ""}`}>
                    {value ??
                        "Sin datos"}
                </div>
            </CardContent>
        </Card>
    );
}
