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

    const totalWorks = Array.isArray(data?.works) ? data.works.length : 0
    const worksWithAttention = Array.isArray(data?.attentionItems)
        ? data.attentionItems.filter((item) => item.kind === 'work').length
        : 0

    const openProblems = Number(data?.kpis?.openProblems ?? 0)
    const pendingEvidence = Number(data?.kpis?.pendingEvidence ?? 0)

    const executiveSummary = {
        worksWithAttention,
        openProblems,
        pendingEvidence,
    }

    const hasHealthyState =
        worksWithAttention === 0 &&
        openProblems === 0 &&
        pendingEvidence === 0

    const heroMessage = hasHealthyState
        ? 'Tu operación ambiental se encuentra estable. No hay señales urgentes en este momento.'
        : 'Hoy existen señales que requieren seguimiento para mantener la trazabilidad y el control ambiental.'

    const nextRecommendation = worksWithAttention > 0
        ? 'Revisar primero las unidades con atención para evitar que el seguimiento operacional quede desactualizado.'
        : pendingEvidence > 0
            ? 'Revisar primero las evidencias pendientes para sostener la trazabilidad documental.'
            : openProblems > 0
                ? 'Revisar primero los problemas abiertos para confirmar su siguiente acción.'
                : 'Todo está al día. Puedes continuar con seguimiento operativo o carga de nuevos datos.'
    return (
        <div className="inicio-page">
            <section className="inicio-hero">
                <div className="inicio-hero__main">
                    <div className="inicio-hero__eyebrow">Inicio</div>
                    <h1 className="inicio-hero__title">{organizationName}</h1>
                    <p className="inicio-hero__description">
                        {heroMessage}
                    </p>

                    <div className="inicio-hero__chips">
                        <span className="inicio-chip inicio-chip--soft">
                            {totalWorks} {totalWorks === 1 ? 'unidad activa' : 'unidades activas'}
                        </span>
                        <span className="inicio-chip inicio-chip--soft">
                            {worksWithAttention} con atención
                        </span>
                        <span className="inicio-chip inicio-chip--soft">
                            {pendingEvidence} evidencias pendientes
                        </span>
                    </div>
                </div>

                <aside className="inicio-hero__aside">
                    <div className="inicio-health">
                        <div className="inicio-health__label">Lectura rápida</div>
                        <div className="inicio-health__value">
                            {hasHealthyState ? 'Estable' : 'Requiere seguimiento'}
                        </div>
                        <p className="inicio-health__text">{nextRecommendation}</p>
                    </div>
                </aside>
            </section>

            <section className="inicio-kpis">
                <div className="inicio-kpi-card">
                    <div className="inicio-kpi-card__label">Obras con atención</div>
                    <div className="inicio-kpi-card__value">{worksWithAttention}</div>
                    <div className="inicio-kpi-card__meta">
                        {worksWithAttention === 0 ? 'Todas al día' : 'Revisar seguimiento'}
                    </div>
                </div>

                <div className="inicio-kpi-card">
                    <div className="inicio-kpi-card__label">Problemas abiertos</div>
                    <div className="inicio-kpi-card__value">{openProblems}</div>
                    <div className="inicio-kpi-card__meta">
                        {openProblems === 0 ? 'Sin problemas abiertos' : 'Acciones por revisar'}
                    </div>
                </div>

                <div className="inicio-kpi-card">
                    <div className="inicio-kpi-card__label">Evidencias pendientes</div>
                    <div className="inicio-kpi-card__value">{pendingEvidence}</div>
                    <div className="inicio-kpi-card__meta">
                        {pendingEvidence === 0 ? 'Sin pendientes documentales' : 'Documentos por revisar'}
                    </div>
                </div>
            </section>

            <section className="inicio-content-grid">
                <div className="inicio-main-column">
                    <div className="inicio-section-card">
                        <div className="inicio-section-card__header">
                            <div>
                                <div className="inicio-section-card__eyebrow">Prioridad</div>
                                <h2 className="inicio-section-card__title">Requiere tu atención</h2>
                                <p className="inicio-section-card__description">
                                    Señales prioritarias que deberías revisar hoy.
                                </p>
                            </div>
                        </div>

                        <AttentionList
                            items={data?.attentionItems ?? []}
                            partiallyUnavailable={Boolean(data?.workContextErrors?.length)}
                        />
                    </div>

                    <div className="inicio-section-card">
                        <div className="inicio-section-card__header inicio-section-card__header--between">
                            <div>
                                <div className="inicio-section-card__eyebrow">Operación</div>
                                <h2 className="inicio-section-card__title">Mis obras</h2>
                                <p className="inicio-section-card__description">
                                    Estado breve de tus unidades activas.
                                </p>
                            </div>

                            <a href="/obras" className="inicio-inline-link">
                                Ver todas
                            </a>
                        </div>

                        <div className="inicio-work-grid">
                            {(data?.works ?? []).slice(0, 4).map((work) => (
                                <CompactWorkCard
                                    key={work.id}
                                    work={work}
                                    contextError={Boolean((data?.workContextErrors ?? []).includes(work.id))}
                                />
                            ))}
                        </div>
                    </div>
                </div>

                <aside className="inicio-side-column">
                    <div className="inicio-side-panel">
                        <div className="inicio-side-panel__eyebrow">Seguimiento</div>
                        <h3 className="inicio-side-panel__title">Actividad reciente</h3>
                        <p className="inicio-side-panel__description">
                            Últimos movimientos relevantes cargados en la organización.
                        </p>

                        <div className="inicio-activity-list">
                            {(data?.recentActivity ?? []).slice(0, 3).map((item, index) => (
                                <div className="inicio-activity-item" key={item.id ?? index}>
                                    <div className="inicio-activity-item__date">
                                        {item.dateLabel}
                                    </div>
                                    <div className="inicio-activity-item__title">
                                        {item.title}
                                    </div>
                                    <div className="inicio-activity-item__type">
                                        {item.typeLabel}
                                    </div>
                                </div>
                            ))}

                            {(!data?.recentActivity || data.recentActivity.length === 0) && (
                                <div className="inicio-empty-inline">
                                    Aún no hay actividad reciente registrada.
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="inicio-side-panel inicio-side-panel--accent">
                        <div className="inicio-side-panel__eyebrow">Siguiente paso</div>
                        <h3 className="inicio-side-panel__title">Qué haría ahora</h3>
                        <p className="inicio-side-panel__description">
                            {nextRecommendation}
                        </p>

                        <div className="inicio-side-actions">
                            <a href="/datos/evidencias" className="inicio-cta inicio-cta--secondary">
                                Ver evidencias
                            </a>
                            <a href="/inteligencia/problemas" className="inicio-cta">
                                Revisar problemas
                            </a>
                        </div>
                    </div>
                </aside>
            </section>
        </div>
    )
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