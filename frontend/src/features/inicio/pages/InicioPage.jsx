import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import {
    AlertTriangle,
    FileCheck2,
    Plus,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getActivePreset } from "@/presets/registry";
import {
    EmptyState,
    ErrorState,
    KpiCard,
    LoadingState,
    PageHeader,
    SectionHeader,
    Timeline,
    TimelineItem,
} from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

import AttentionList from "../components/AttentionList";
import CompactWorkCard from "../components/CompactWorkCard";
import { getInicioOverview } from "../services/inicioApi";

const isOpen = problem =>
    !["cerrada", "resuelta"].includes(problem.estado);

const evidencePending = item =>
    ["pendiente", "observada", "en_revision"].includes(
        item.estado_documental ||
        item.estado_validacion ||
        item.estado_revision
    );

const needsAttention = value =>
    ["requiere_atencion", "cierre_pendiente"].includes(value);

const workId = work =>
    String(work?.id || work?.obra_id || "");

const referenceId = value =>
    String(
        typeof value === "object"
            ? value?.id || value?.obra_id || ""
            : value || ""
    );

const statusLabel = value =>
({
    requiere_atencion: "Requiere atención",
    cierre_pendiente: "Cierre pendiente",
    pendiente: "Pendiente",
    observada: "Observada",
    en_revision: "En revisión",
    detectada: "Detectado",
    en_gestion: "En gestión",
}[value] ||
    String(value || "Pendiente").replaceAll("_", " "));

export default function InicioPage() {
    const {
        activeOrganizacion,
        activeOrganizacionId,
    } = useOrganizacionActiva();

    const preset = getActivePreset(
        activeOrganizacion?.preset || "construccion"
    );

    const [state, setState] = useState({
        status: "loading",
        data: null,
    });

    const requestRef = useRef(0);

    const load = useCallback(() => {
        if (!activeOrganizacionId) return;

        const requestId = ++requestRef.current;

        setState({
            status: "loading",
            data: null,
        });

        getInicioOverview(activeOrganizacionId)
            .then(data => {
                if (requestRef.current === requestId) {
                    setState({
                        status: "ready",
                        data,
                    });
                }
            })
            .catch(() => {
                if (requestRef.current === requestId) {
                    setState({
                        status: "error",
                        data: null,
                    });
                }
            });
    }, [activeOrganizacionId]);

    useEffect(() => {
        load();

        return () => {
            requestRef.current += 1;
        };
    }, [load]);

    const data = state.data;

    const openProblems = useMemo(
        () => data?.problems.filter(isOpen) || [],
        [data]
    );

    const pendingEvidence = useMemo(
        () => data?.evidence.filter(evidencePending) || [],
        [data]
    );

    const contextByWork = useMemo(
        () =>
            new Map(
                (data?.workContexts || []).map(context => [
                    String(context.references?.work),
                    context,
                ])
            ),
        [data]
    );

    const contextErrorIds = useMemo(
        () => new Set(data?.workContextErrors || []),
        [data]
    );

    const workById = useMemo(
        () =>
            new Map(
                (data?.works || []).map(work => [
                    workId(work),
                    work,
                ])
            ),
        [data]
    );

    const unknownWorkIds = useMemo(
        () =>
            new Set(
                (data?.works || [])
                    .filter(
                        work =>
                            contextErrorIds.has(workId(work)) &&
                            !work.estado_ambiental
                    )
                    .map(workId)
            ),
        [contextErrorIds, data]
    );

    const attentionWorks = useMemo(
        () =>
            (data?.works || []).filter(work =>
                needsAttention(
                    contextByWork.get(workId(work))?.obra
                        ?.estado_ambiental || work.estado_ambiental
                )
            ),
        [contextByWork, data]
    );

    const priorities = useMemo(
        () =>
            buildPriorities({
                attentionWorks,
                contextByWork,
                openProblems,
                pendingEvidence,
                preset,
                workById,
            }),
        [
            attentionWorks,
            contextByWork,
            openProblems,
            pendingEvidence,
            preset,
            workById,
        ]
    );

    if (state.status === "loading") {
        return (
            <LoadingState label="Preparando tu resumen" />
        );
    }

    if (state.status === "error") {
        return (
            <ErrorState
                title="No pudimos cargar tu resumen"
                description="Intenta nuevamente para ver tus unidades y pendientes."
                onRetry={load}
            />
        );
    }

    if (!data.works.length) {
        return (
            <main className="space-y-6">
                <PageHeader
                    title={
                        activeOrganizacion?.nombre || "Resumen de hoy"
                    }
                    description="Comienza definiendo la unidad que quieres gestionar."
                />

                <EmptyState
                    title={`No hay ${preset.unitPluralLabel.toLowerCase()} todavía`}
                    description={`Crea tu primera ${preset.unitLabel.toLowerCase()} para comenzar el seguimiento ambiental.`}
                    primaryAction={
                        <Link
                            className="inline-flex items-center gap-2 font-bold text-[var(--brand-primary)]"
                            to="/obras"
                        >
                            <Plus
                                aria-hidden="true"
                                size={17}
                            />
                            Crear primera{" "}
                            {preset.unitLabel.toLowerCase()}
                        </Link>
                    }
                    secondaryAction={
                        <Link
                            className="font-bold text-[var(--text-secondary)]"
                            to="/datos/importaciones"
                        >
                            Importar datos
                        </Link>
                    }
                />
            </main>
        );
    }
    const evidenceByWork = countByWork(
        pendingEvidence
    );

    const orderedWorks = [...data.works]
        .sort(
            (a, b) =>
                Number(
                    attentionWorks.some(
                        work => workId(work) === workId(b)
                    )
                ) -
                Number(
                    attentionWorks.some(
                        work => workId(work) === workId(a)
                    )
                )
        )
        .slice(0, 4);

    const recentEvents = (data.workContexts || [])
        .flatMap(context => context.timeline || [])
        .sort((a, b) =>
            String(b.fecha).localeCompare(
                String(a.fecha)
            )
        )
        .slice(0, 3);

    const incompleteCount = unknownWorkIds.size;

    const attentionHelper = attentionWorks.length
        ? `${attentionWorks.length === 1 ? "Revisa su estado" : "Revisa sus estados"}${incompleteCount
            ? ` · ${incompleteCount} sin información`
            : ""
        }`
        : incompleteCount
            ? `${incompleteCount} ${incompleteCount === 1
                ? "unidad sin información"
                : "unidades sin información"
            }`
            : "Todas al día";
    return (
        <main className="space-y-7">
            <section className="rounded-3xl border border-emerald-100 bg-gradient-to-br from-emerald-50 via-white to-teal-50 p-6 shadow-sm">
                <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="max-w-3xl">
                        <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
                            Resumen ambiental
                        </p>

                        <h1 className="mt-2 text-3xl font-black text-[var(--text-primary)]">
                            {activeOrganizacion?.nombre || "Resumen de hoy"}
                        </h1>

                        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
                            Esto es lo que requiere tu atención hoy y el estado general de tu operación ambiental.
                        </p>

                        <div className="mt-4 flex flex-wrap gap-2">
                            <span className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1.5 text-xs font-bold text-emerald-800">
                                {data.works.length}{" "}
                                {data.works.length === 1
                                    ? preset.unitLabel.toLowerCase()
                                    : preset.unitPluralLabel.toLowerCase()}
                            </span>

                            <span className="rounded-full border border-amber-200 bg-white/80 px-3 py-1.5 text-xs font-bold text-amber-800">
                                {attentionWorks.length} con atención
                            </span>

                            <span className="rounded-full border border-sky-200 bg-white/80 px-3 py-1.5 text-xs font-bold text-sky-800">
                                {pendingEvidence.length} evidencias pendientes
                            </span>
                        </div>
                    </div>

                    <div className="w-full rounded-2xl border border-emerald-100 bg-white/80 p-4 lg:max-w-sm">
                        <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">
                            Lectura rápida
                        </p>

                        <p className="mt-2 text-xl font-black text-[var(--text-primary)]">
                            {attentionWorks.length ||
                                openProblems.length ||
                                pendingEvidence.length ||
                                incompleteCount
                                ? "Requiere seguimiento"
                                : "Operación estable"}
                        </p>

                        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                            {attentionWorks.length
                                ? "Revisa primero las unidades que presentan señales de atención."
                                : pendingEvidence.length
                                    ? "Revisa primero las evidencias pendientes para mantener la trazabilidad."
                                    : openProblems.length
                                        ? "Continúa con el seguimiento de los problemas abiertos."
                                        : incompleteCount
                                            ? "Parte de la información no pudo verificarse completamente."
                                            : "No hay pendientes detectados con la información disponible."}
                        </p>
                    </div>
                </div>
            </section>

            <section
                aria-label="Resumen"
                className="grid gap-3 md:grid-cols-3"
            >
                <KpiCard
                    icon={AlertTriangle}
                    label={`${preset.unitPluralLabel} con atención`}
                    value={attentionWorks.length}
                    helper={attentionHelper}
                    status={
                        attentionWorks.length
                            ? "warning"
                            : incompleteCount
                                ? "info"
                                : "success"
                    }
                />

                <KpiCard
                    icon={AlertTriangle}
                    label="Problemas abiertos"
                    value={
                        data.resourceErrors.problems
                            ? "No disponible"
                            : openProblems.length
                    }
                    helper={
                        data.resourceErrors.problems
                            ? "No fue posible consultarlos"
                            : openProblems.length
                                ? "Requieren seguimiento"
                                : "Sin problemas abiertos"
                    }
                    status={
                        openProblems.length
                            ? "danger"
                            : "success"
                    }
                />

                <KpiCard
                    icon={FileCheck2}
                    label="Evidencias pendientes"
                    value={
                        data.resourceErrors.evidence
                            ? "No disponible"
                            : pendingEvidence.length
                    }
                    helper={
                        data.resourceErrors.evidence
                            ? "No fue posible consultarlas"
                            : pendingEvidence.length
                                ? "Requieren revisión"
                                : "Sin pendientes documentales"
                    }
                    status={
                        pendingEvidence.length
                            ? "warning"
                            : "success"
                    }
                />
            </section>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.7fr)]">
                <div className="space-y-6">
                    <section
                        id="priorities"
                        className="rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-sm"
                    >
                        <SectionHeader
                            title="Requiere tu atención"
                            description={
                                priorities.length
                                    ? "Los pendientes más importantes y su siguiente paso."
                                    : incompleteCount
                                        ? "No hay pendientes detectados en la información disponible."
                                        : "No hay pendientes disponibles."
                            }
                        />

                        <AttentionList
                            contextIncomplete={incompleteCount > 0}
                            items={priorities}
                            unitPluralLabel={preset.unitPluralLabel}
                        />
                    </section>

                    <section className="rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-sm">
                        <SectionHeader
                            title={`Mis ${preset.unitPluralLabel.toLowerCase()}`}
                            description={`Estado breve de tus ${preset.unitPluralLabel.toLowerCase()}.`}
                            action={
                                <Link
                                    className="text-sm font-bold text-[var(--brand-primary)]"
                                    to="/obras"
                                >
                                    Ver todas
                                </Link>
                            }
                        />

                        <div
                            className={`grid gap-3 ${orderedWorks.length === 1
                                ? "max-w-2xl"
                                : "md:grid-cols-2"
                                }`}
                        >
                            {orderedWorks.map(work => (
                                <CompactWorkCard
                                    context={
                                        contextByWork.get(workId(work))
                                    }
                                    contextError={contextErrorIds.has(
                                        workId(work)
                                    )}
                                    evidenceCount={
                                        evidenceByWork.get(workId(work)) || 0
                                    }
                                    key={
                                        workId(work) || work.codigo_obra
                                    }
                                    unitLabel={preset.unitLabel}
                                    work={work}
                                />
                            ))}
                        </div>
                    </section>
                </div>

                <aside className="space-y-6">
                    {recentEvents.length > 0 && (
                        <section className="rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-sm">
                            <SectionHeader
                                title="Actividad reciente"
                                description="Últimos movimientos registrados."
                            />

                            <Timeline>
                                {recentEvents.map(
                                    (event, index) => (
                                        <TimelineItem
                                            key={`${event.tipo}-${event.referencia_id}-${index}`}
                                            timestamp={formatDateTime(
                                                event.fecha
                                            )}
                                            title={
                                                event.titulo ||
                                                "Actividad registrada"
                                            }
                                            description={String(
                                                event.tipo || ""
                                            ).replaceAll("_", " ")}
                                        />
                                    )
                                )}
                            </Timeline>
                        </section>
                    )}

                    <section className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-5">
                        <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
                            Siguiente paso
                        </p>

                        <h2 className="mt-2 text-lg font-black text-[var(--text-primary)]">
                            Mantén el control ambiental al día
                        </h2>

                        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                            {attentionWorks.length
                                ? "Revisa las unidades con atención antes de continuar con nuevas cargas."
                                : pendingEvidence.length
                                    ? "Completa la revisión documental pendiente."
                                    : openProblems.length
                                        ? "Continúa el seguimiento de los problemas ambientales abiertos."
                                        : "Puedes continuar con nuevas evidencias, importaciones o seguimiento operacional."}
                        </p>

                        <div className="mt-4 flex flex-wrap gap-2">
                            <Link
                                className="rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm font-bold text-emerald-800"
                                to="/datos/evidencias"
                            >
                                Ver evidencias
                            </Link>

                            <Link
                                className="rounded-xl bg-emerald-700 px-3 py-2 text-sm font-bold text-white"
                                to="/inteligencia/problemas"
                            >
                                Revisar problemas
                            </Link>
                        </div>
                    </section>
                </aside>
            </div>
        </main>
    );
}

function buildPriorities({
    attentionWorks,
    contextByWork,
    openProblems,
    pendingEvidence,
    preset,
    workById,
}) {
    const items = [];
    const representedWorks = new Set();

    attentionWorks.forEach(work => {
        if (items.length >= 5) return;

        const id = workId(work);

        const status =
            contextByWork.get(id)?.obra
                ?.estado_ambiental ||
            work.estado_ambiental;

        representedWorks.add(id);

        items.push({
            key: `work-${id}`,
            title: `${work.nombre ||
                work.codigo_obra ||
                preset.unitLabel
                } requiere atención`,
            location:
                work.nombre ||
                work.codigo_obra ||
                preset.unitLabel,
            reason: statusLabel(status),
            status: statusLabel(status),
            tone: "warning",
            path: `/obras/${id}/resumen`,
            action: `Ver ${preset.unitLabel.toLowerCase()}`,
        });
    });

    openProblems.forEach(problem => {
        if (items.length >= 5) return;

        const id = referenceId(problem.obra);

        if (
            id &&
            representedWorks.has(id)
        ) {
            return;
        }

        const work = workById.get(id);

        items.push({
            key: `problem-${problem.id}`,
            title: problem.titulo,
            location:
                work?.nombre ||
                problem.area_operacional ||
                "Alcance organizacional",
            reason: `Problema ambiental · ${problem.categoria || "Sin categoría"
                }`,
            status: statusLabel(problem.estado),
            tone: "warning",
            path: id
                ? `/obras/${id}/problemas/${problem.id}`
                : `/inteligencia/problemas/${problem.id}`,
            action: "Ver problema",
        });
    });

    pendingEvidence.forEach(evidence => {
        if (items.length >= 5) return;

        const id = referenceId(evidence.obra);

        items.push({
            key: `evidence-${evidence.id}`,
            title:
                evidence.nombre ||
                evidence.tipo_evidencia ||
                "Evidencia pendiente",
            location:
                evidence.obra_nombre ||
                workById.get(id)?.nombre ||
                "Sin unidad asociada",
            reason: `Documento ${statusLabel(
                evidence.estado_documental ||
                evidence.estado_validacion ||
                evidence.estado_revision
            ).toLowerCase()}`,
            status: statusLabel(
                evidence.estado_documental ||
                evidence.estado_validacion ||
                evidence.estado_revision
            ),
            tone: "info",
            path: `/datos/evidencias/${evidence.id}`,
            action: "Revisar evidencia",
        });
    });

    return items;
}

function countByWork(evidence) {
    const counts = new Map();

    evidence.forEach(item => {
        const id = referenceId(item.obra);

        if (id) {
            counts.set(
                id,
                (counts.get(id) || 0) + 1
            );
        }
    });

    return counts;
}