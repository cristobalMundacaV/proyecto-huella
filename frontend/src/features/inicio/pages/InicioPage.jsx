import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import {
    AlertTriangle,
    ArrowRight,
    CheckCircle2,
    FileCheck2,
    ShieldAlert,
    Plus,
} from "lucide-react";
import { Link } from "react-router-dom";
import ContextContentSkeleton from "@/shared/components/ContextContentSkeleton";
import { hasIncompleteConfiguration } from "@/app/onboardingGate";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getActivePreset } from "@/presets/registry";
import {
    CZAlertBanner,
    CZInsightCard,
    CZMetricCard,
    CZPageHero,
    EmptyState,
    ErrorState,
    PageHeader,
    SectionHeader,
    StatusBadge,
} from "@/shared/ui";
import { formatNumber } from "@/shared/utils/formatters";
import ChartCard from "@/shared/charts/ChartCard";
import EnvironmentalBarChart from "@/shared/charts/EnvironmentalBarChart";
import EnvironmentalDonutChart, { DonutLegend } from "@/shared/charts/EnvironmentalDonutChart";

import AttentionList from "../components/AttentionList";
import { getInicioOverview } from "../services/inicioApi";
import { getOrganizationDashboard } from "@/features/organizaciones/services/organizationDashboardApi";
import { mapPortfolioDashboard } from "../utils/portfolioSelectors";

const ESTADO_TONE = { estable: "success", atencion: "warning", critica: "danger", periodo_incompleto: "warning", lista_para_reporte: "success" };

const isOpen = problem =>
    !["cerrada", "resuelta"].includes(problem.estado);

const evidencePending = item =>
    ["compatible_incompleta", "contradiccion", "no_pertinente", "indeterminada"].includes(
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
    compatible_incompleta: "Compatible incompleta",
    contradiccion: "Contradicción",
    no_pertinente: "No pertinente",
    indeterminada: "Indeterminada",
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

        Promise.allSettled([
            getInicioOverview(activeOrganizacionId),
            getOrganizationDashboard(activeOrganizacionId, { relative_months: 3 }),
        ])
            .then(([overviewResult, portfolioResult]) => {
                if (requestRef.current !== requestId) return;
                if (overviewResult.status !== "fulfilled") {
                    setState({ status: "error", data: null });
                    return;
                }
                setState({
                    status: "ready",
                    data: {
                        ...overviewResult.value,
                        portfolioDashboard: portfolioResult.status === "fulfilled" ? portfolioResult.value : null,
                        portfolioUnavailable: portfolioResult.status !== "fulfilled",
                    },
                });
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
        return <ContextContentSkeleton charts={4} kpis={8} />;
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
    const incompleteCount = unknownWorkIds.size;
    const portfolio = mapPortfolioDashboard(data.portfolioDashboard);
    const { readyPeriods } = portfolio;

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
        <main className="space-y-3 pb-4">
            <CZPageHero>
                <div className="flex flex-col gap-6 lg:min-h-[205px] lg:flex-row lg:items-center lg:justify-between">
                <div className="max-w-3xl">
                    <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
                        Estado ambiental del portafolio
                    </p>

                    <h1 className="mt-2 text-3xl font-black text-white">
                        {activeOrganizacion?.nombre || "Resumen de hoy"}
                    </h1>

                    <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/80">
                        Esto es lo que requiere tu atención hoy y el estado general de tu operación ambiental.
                    </p>

                    <div className="mt-4 flex flex-wrap gap-2">
                        <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-white backdrop-blur">
                            {data.works.length}{" "}
                            {data.works.length === 1
                                ? preset.unitLabel.toLowerCase()
                                : preset.unitPluralLabel.toLowerCase()}
                        </span>

                        <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                            {attentionWorks.length} con atención
                        </span>

                        <span className="rounded-full border border-teal-200/30 bg-teal-200/10 px-3 py-1.5 text-xs font-bold text-teal-50">
                            {pendingEvidence.length} evidencias pendientes
                        </span>
                    </div>
                </div>

                <div className="w-full rounded-2xl border border-white/15 bg-black/10 p-4 backdrop-blur-sm lg:max-w-sm">
                    <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-100/70">
                        Lectura rápida
                    </p>

                    <p className="mt-2 text-xl font-black text-white">
                        {attentionWorks.length ||
                            openProblems.length ||
                            pendingEvidence.length ||
                            incompleteCount
                            ? "Requiere seguimiento"
                            : "Operación estable"}
                    </p>

                    <div className="mt-4 grid grid-cols-2 gap-3 border-t border-white/10 pt-4">
                        <div><p className="text-[10px] font-bold uppercase tracking-wider text-emerald-100/70">Huella consolidada</p><p className="mt-1 text-2xl font-black">{formatNumber(portfolio.total)} <span className="text-xs">tCO2e</span></p></div>
                        <div><p className="text-[10px] font-bold uppercase tracking-wider text-emerald-100/70">Readiness promedio</p><p className="mt-1 text-2xl font-black">{portfolio.readiness === null ? "—" : `${formatNumber(portfolio.readiness)}%`}</p></div>
                    </div>

                    <p className="mt-2 text-sm leading-6 text-emerald-50/80">
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
            </CZPageHero>

            {hasIncompleteConfiguration(activeOrganizacion) && (
                <CZAlertBanner
                    action={
                        <Link className="shrink-0 rounded-lg bg-amber-800 px-3 py-1.5 text-xs font-black text-white" to="/onboarding">
                            Completar configuración
                        </Link>
                    }
                >
                    <b>Configuración incompleta.</b> Algunos flujos ambientales todavía no están habilitados. Completa la configuración para acceder a todas las capacidades.
                </CZAlertBanner>
            )}

            <section className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" aria-label="Indicadores ejecutivos del portafolio">
                <CZMetricCard icon={ShieldAlert} label="Huella consolidada" value={portfolio.total} unit="tCO2e" supportingText="Impacto total del portafolio" tone="blue" />
                <CZMetricCard icon={AlertTriangle} label={`${preset.unitPluralLabel} con atención`} value={attentionWorks.length} supportingText={attentionHelper} tone={attentionWorks.length ? "amber" : "emerald"} />
                <CZMetricCard icon={AlertTriangle} label="Problemas abiertos" value={data.resourceErrors.problems ? null : openProblems.length} supportingText={data.resourceErrors.problems ? "Información no disponible" : openProblems.length ? "Requieren seguimiento" : "Sin problemas abiertos"} tone={openProblems.length ? "rose" : "emerald"} />
                <CZMetricCard icon={FileCheck2} label="Evidencias pendientes" value={data.resourceErrors.evidence ? null : pendingEvidence.length} supportingText={data.resourceErrors.evidence ? "Información no disponible" : pendingEvidence.length ? "Requieren revisión" : "Sin pendientes documentales"} tone={pendingEvidence.length ? "amber" : "emerald"} />
                <CZMetricCard icon={CheckCircle2} label="Readiness promedio" value={portfolio.readiness} unit="%" supportingText={`${readyPeriods} de ${data.works.length} períodos listos`} tone="emerald" progress={portfolio.readiness} />
            </section>

            {data.portfolioUnavailable && (
                <CZAlertBanner tone="info">
                    Las métricas ambientales consolidadas (huella, alcance, riesgo, readiness) no están disponibles en este momento. El resto del resumen sigue siendo real.
                </CZAlertBanner>
            )}

            <section className="grid gap-3 xl:grid-cols-2">
                <ChartCard title="Emisiones por obra" description="Huella calculada por el motor ambiental para cada obra." empty={!portfolio.works.length}><EnvironmentalBarChart data={portfolio.works} height={250} valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /></ChartCard>
                <ChartCard title="GEI por alcance" description="Distribución consolidada del portafolio." empty={!portfolio.scopes.length}><PortfolioDonut data={portfolio.scopes} total={portfolio.total} /></ChartCard>
                <ChartCard title="Distribución por flujo" description="Impacto consolidado de los flujos reportados por obra." empty={!portfolio.flows.length}><PortfolioDonut data={portfolio.flows} total={portfolio.total} /></ChartCard>
                <ChartCard title="Readiness por obra" description="Cobertura de registros del período por obra." empty={!portfolio.readinessByWork.length}><EnvironmentalBarChart data={portfolio.readinessByWork} height={250} valueFormatter={(value) => `${formatNumber(value)}%`} color="#059669" /></ChartCard>
            </section>

            {portfolio.insights.length > 0 && (
                <section className="rounded-[22px] border border-slate-200 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
                    <SectionHeader title="Insights y recomendaciones IA" description="Prioridades del portafolio según impacto, evidencia y riesgo ambiental." />
                    <div className="grid auto-rows-fr items-stretch gap-3 lg:grid-cols-3">
                        {portfolio.insights.map((insight) => (
                            <CZInsightCard key={insight.code} priority={insight.priority} title={insight.title} description={insight.description} />
                        ))}
                    </div>
                </section>
            )}

            {portfolio.topWorks.length > 0 && (
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
                    <SectionHeader title="Obras prioritarias" description="Ordenadas por riesgo, hallazgos críticos y brecha de readiness." />
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {portfolio.topWorks.map((work) => (
                            <Link key={work.obra_id} to={`/obras/${work.obra_id}/resumen`} className="group rounded-[18px] border border-slate-200 bg-slate-50/60 p-4 transition hover:border-emerald-300 hover:shadow-md">
                                <div className="flex items-center justify-between gap-2">
                                    <h3 className="truncate font-black text-[var(--text-primary)]">{work.obra_nombre}</h3>
                                    <StatusBadge tone={ESTADO_TONE[work.estado_ejecutivo?.codigo] || "neutral"}>{work.estado_ejecutivo?.label}</StatusBadge>
                                </div>
                                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                                    <div><dt className="font-bold uppercase tracking-wide text-[var(--text-muted)]">Emisiones</dt><dd className="mt-0.5 font-black text-[var(--text-primary)]">{work.huella_total_tco2e ?? "—"} tCO2e</dd></div>
                                    <div><dt className="font-bold uppercase tracking-wide text-[var(--text-muted)]">Readiness</dt><dd className="mt-0.5 font-black text-[var(--text-primary)]">{work.readiness_pct ?? "—"}%</dd></div>
                                    <div><dt className="font-bold uppercase tracking-wide text-[var(--text-muted)]">Riesgo</dt><dd className="mt-0.5 font-black capitalize text-[var(--text-primary)]">{work.risk?.nivel || "—"}</dd></div>
                                    <div><dt className="font-bold uppercase tracking-wide text-[var(--text-muted)]">Hallazgos</dt><dd className="mt-0.5 font-black text-[var(--text-primary)]">{work.hallazgos_altos}</dd></div>
                                </dl>
                                <span className="mt-3 flex items-center justify-end gap-1 text-xs font-black text-emerald-700 group-hover:text-emerald-900">Abrir obra <ArrowRight aria-hidden="true" size={13} /></span>
                            </Link>
                        ))}
                    </div>
                </section>
            )}

            <section
                id="priorities"
                className="rounded-[22px] border border-slate-200 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]"
            >
                <SectionHeader
                    title="Requiere tu atención"
                    description={
                        priorities.length
                            ? "Pendientes priorizados según riesgo, seguimiento y necesidad de intervención."
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
        </main >
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

    attentionWorks.forEach(work => {
        const id = workId(work);

        const status =
            contextByWork.get(id)?.obra
                ?.estado_ambiental ||
            work.estado_ambiental;

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
            severity: "medio",
            path: `/obras/${id}/resumen`,
            action: `Ver ${preset.unitLabel.toLowerCase()}`,
        });
    });

    openProblems.forEach(problem => {
        const id = referenceId(problem.obra);

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
            description: problem.descripcion || "",
            category: problem.categoria || "",
            risk: problem.nivel_riesgo || "",
            status: statusLabel(problem.estado),
            tone: "warning",
            severity: problem.nivel_riesgo || (problem.estado === "en_seguimiento" ? "seguimiento" : "neutral"),
            path: id
                ? `/obras/${id}/problemas/${problem.id}`
                : `/inteligencia/problemas/${problem.id}`,
            action: "Ver problema",
        });
    });

    pendingEvidence.forEach(evidence => {
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
            description: evidence.obra_nombre || workById.get(id)?.nombre || "",
            status: statusLabel(
                evidence.estado_documental ||
                evidence.estado_validacion ||
                evidence.estado_revision
            ),
            tone: "info",
            severity: "seguimiento",
            path: `/datos/evidencias/${evidence.id}`,
            action: "Revisar evidencia",
        });
    });

    const rank = value => {
        if (["critico", "alto"].includes(value)) return 1;
        if (value === "medio") return 2;
        if (["seguimiento", "en_seguimiento", "en_implementacion"].includes(value)) return 3;
        return 4;
    };

    return items
        .map((item, index) => ({ item, index }))
        .sort((left, right) => rank(left.item.severity) - rank(right.item.severity) || left.index - right.index)
        .slice(0, 3)
        .map(({ item }) => item);
}


function PortfolioDonut({ data, total }) {
    return <div className="grid gap-3 sm:grid-cols-[200px_1fr] sm:items-center"><EnvironmentalDonutChart data={data} height={205} innerRadius={66} outerRadius={94} centerLabel="Total" centerValue={formatNumber(total)} centerUnit="tCO2e" valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /><DonutLegend data={data} valueFormatter={(value) => `${formatNumber(value)} tCO2e`} /></div>;
}
