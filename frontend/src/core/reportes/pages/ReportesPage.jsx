import { useEffect, useMemo, useState } from "react";
import { BarChart3, CheckCircle2, Clock3, Database, RefreshCcw } from "lucide-react";

import PlatformLoader from "@/shared/components/PlatformLoader";
import { createTraceableAction, getTraceableActionsSummary } from "@/features/intelligence/services/traceableActionsApi";
import { getConstructoraDashboard, getEmpresaRegistrosAmbientales } from "@/shared/services/api";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";
import { construccionReport } from "@/presets/construccion/report";
import { aserraderoReport } from "@/presets/aserradero/report";
import { transporteReport } from "@/presets/transporte/report";
import { industrialReport } from "@/presets/industrial/report";
import { normalizeReportRows } from "@/presets/shared/reportConfig";

import ReportCharts from "../components/ReportCharts";
import ReportExportActions from "../components/ReportExportActions";
import ReportFiltersModal from "../components/ReportFiltersModal";
import ReportHero from "../components/ReportHero";
import ReportKpiGrid from "../components/ReportKpiGrid";
import ReportTable from "../components/ReportTable";

const reportByPreset = {
  construccion: construccionReport,
  aserradero: aserraderoReport,
  transporte: transporteReport,
  industrial: industrialReport,
};

const defaultFilters = {
  fecha_inicio: "",
  fecha_fin: "",
  agrupacion: "mes",
};

function todayPlus(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function findKpi(report, includes) {
  const needle = includes.toLowerCase();
  return report?.kpis?.find((kpi) => String(kpi.label || "").toLowerCase().includes(needle));
}

function statusLabel(status) {
  return {
    pendiente: "Pendiente",
    en_progreso: "En progreso",
    validacion: "En validación",
    completada: "Completada",
  }[status] || "Sin estado";
}

function linkTypeLabel(type) {
  return {
    obra: "Obra",
    lote_forestal: "Lote forestal",
    registro_emision: "Registro crítico",
    evidencia: "Evidencia",
  }[type] || "Vínculo";
}

function actionLinkLabel(action) {
  if (!action?.linkedTo) return "Sin vínculo operacional";
  return `${linkTypeLabel(action.linkedTo.type)}: ${action.linkedTo.label || action.linkedTo.id || "sin detalle"}`;
}

function formatActionLine(action, index) {
  return `${index + 1}. ${action.title || "Acción ambiental"} · Estado: ${statusLabel(action.status)} · Responsable: ${action.responsible || "Equipo ambiental"} · Fecha: ${action.dueDate || "Sin fecha"} · ${actionLinkLabel(action)}`;
}

function buildRiskActionPayload(risk) {
  const isHighPriority = risk.level === "Alta";
  return {
    title: `Cerrar brecha: ${risk.title}`,
    description: `${risk.description}\n\nAcción sugerida: ${risk.action}`,
    responsible: "Equipo ambiental",
    dueDate: todayPlus(isHighPriority ? 7 : 14),
    status: "pendiente",
    source: "Reporte ejecutivo · Riesgos y brechas",
    evidence: "Evidencia requerida para cerrar brecha detectada en reporte.",
    trackingKpi: risk.title,
    sourceCardId: `report_risk_${risk.key}`,
    metadata: {
      origin: "report_risk_gap",
      riskKey: risk.key,
      riskLevel: risk.level,
      riskTitle: risk.title,
      suggestedAction: risk.action,
    },
  };
}

function buildDecisionAgenda({ actionsSummary, criticalSource, records }) {
  const traceabilityPct = Number(actionsSummary?.traceabilityPct || 0);
  const completionPct = Number(actionsSummary?.completionPct || 0);
  const overdue = Number(actionsSummary?.overdue || 0);
  const active = Number(actionsSummary?.active || 0);
  const unlinked = Number(actionsSummary?.unlinked || 0);
  const agenda = [];

  if (records) {
    agenda.push({
      priority: "Alta",
      decision: `Priorizar foco crítico: ${criticalSource}`,
      reason: "Es el principal punto de concentración de huella del periodo analizado.",
      expected: "Reducir impacto donde existe mayor potencial de mejora.",
    });
  } else {
    agenda.push({
      priority: "Alta",
      decision: "Completar base de datos ambiental del periodo",
      reason: "Sin registros suficientes no existe diagnóstico confiable para gerencia.",
      expected: "Activar medición, comparación y trazabilidad ejecutiva.",
    });
  }

  if (overdue > 0) {
    agenda.push({
      priority: "Alta",
      decision: `Resolver ${overdue} acciones vencidas`,
      reason: "Las acciones vencidas debilitan el seguimiento ambiental y la credibilidad del plan.",
      expected: "Recuperar control operativo y fechas realistas de ejecución.",
    });
  } else if (active > 0) {
    agenda.push({
      priority: "Media",
      decision: `Revisar avance de ${active} acciones activas`,
      reason: "Hay compromisos abiertos que deben mantenerse visibles hasta su cierre.",
      expected: "Evitar retrasos y convertir acciones abiertas en evidencia verificable.",
    });
  }

  if (traceabilityPct < 80 && (actionsSummary?.total || 0) > 0) {
    agenda.push({
      priority: "Media",
      decision: `Vincular ${unlinked} acciones sin trazabilidad directa`,
      reason: "Una acción sin vínculo a obra, lote, registro o evidencia es más difícil de auditar.",
      expected: "Elevar trazabilidad operacional y preparar mejores reportes para clientes o licitaciones.",
    });
  }

  if (completionPct < 50 && (actionsSummary?.total || 0) > 0) {
    agenda.push({
      priority: "Media",
      decision: "Definir meta de cierre de acciones para el próximo periodo",
      reason: "El avance de cierre aún está bajo para demostrar gestión ambiental continua.",
      expected: "Aumentar porcentaje de acciones completadas y respaldadas.",
    });
  }

  return agenda.slice(0, 4);
}

function buildReportReadiness({ actionsSummary, records, totalEmissions }) {
  const actionsTotal = Number(actionsSummary?.total || 0);
  const traceabilityPct = Number(actionsSummary?.traceabilityPct || 0);
  const overdue = Number(actionsSummary?.overdue || 0);
  const completionPct = Number(actionsSummary?.completionPct || 0);

  const checks = [
    { key: "records", label: "Datos ambientales cargados", passed: records > 0, detail: records > 0 ? `${records} registros analizados` : "Faltan registros ambientales para sustentar el reporte." },
    { key: "footprint", label: "Huella calculada", passed: totalEmissions !== "Sin datos", detail: totalEmissions !== "Sin datos" ? `Huella disponible: ${totalEmissions}` : "No hay huella total calculada para el periodo." },
    { key: "actions", label: "Acciones ambientales registradas", passed: actionsTotal > 0, detail: actionsTotal > 0 ? `${actionsTotal} acciones disponibles para seguimiento` : "Falta crear acciones para cerrar el ciclo de gestión." },
    { key: "traceability", label: "Trazabilidad operacional suficiente", passed: actionsTotal > 0 && traceabilityPct >= 80, detail: actionsTotal > 0 ? `${traceabilityPct}% de acciones con vínculo` : "Sin acciones para evaluar trazabilidad." },
    { key: "overdue", label: "Sin acciones vencidas críticas", passed: overdue === 0, detail: overdue === 0 ? "No hay acciones vencidas" : `${overdue} acciones vencidas requieren revisión` },
    { key: "closure", label: "Avance de cierre visible", passed: actionsTotal === 0 ? false : completionPct >= 30, detail: actionsTotal > 0 ? `${completionPct}% de cierre` : "Sin acciones cerradas para demostrar avance." },
  ];

  const passed = checks.filter((check) => check.passed).length;
  const score = Math.round((passed / checks.length) * 100);
  const status = score >= 85 ? "Listo para presentar" : score >= 60 ? "Presentable con observaciones" : "Requiere completar información";

  return { checks, passed, score, status, total: checks.length };
}

function buildReportRisks({ actionsSummary, readiness }) {
  const risks = readiness.checks
    .filter((check) => !check.passed)
    .map((check) => ({ key: check.key, level: ["records", "footprint", "overdue"].includes(check.key) ? "Alta" : "Media", title: check.label, description: check.detail, action: riskAction(check.key) }));

  if ((actionsSummary?.overdue || 0) > 0 && !risks.some((risk) => risk.key === "overdue")) {
    risks.push({ key: "overdue_extra", level: "Alta", title: "Acciones vencidas detectadas", description: `${actionsSummary.overdue} acciones están fuera de plazo.`, action: "Reasignar responsable, nueva fecha objetivo y evidencia esperada." });
  }

  return risks.length
    ? risks.slice(0, 6)
    : [{ key: "sin_brechas", level: "Baja", title: "Sin brechas críticas", description: "El reporte no muestra brechas relevantes para presentación ejecutiva.", action: "Mantener seguimiento y actualizar datos del próximo periodo." }];
}

function riskAction(key) {
  return {
    records: "Cargar o importar registros ambientales del periodo.",
    footprint: "Revisar factores de emisión y registros faltantes.",
    actions: "Crear acciones ambientales asociadas a los focos críticos.",
    traceability: "Vincular acciones a obra, lote, registro o evidencia.",
    overdue: "Regularizar plazos y responsables antes de presentar.",
    closure: "Cerrar acciones completadas con respaldo verificable.",
  }[key] || "Revisar esta brecha antes de compartir el reporte.";
}

function buildClientSummary({ empresa, criticalSource, readiness, records, totalEmissions }) {
  const intro = records ? `${empresa} ya cuenta con una lectura ambiental activa para el periodo analizado.` : `${empresa} todavía requiere completar su base de datos ambiental para generar una lectura confiable.`;
  const focus = records ? `La huella disponible es ${totalEmissions} y el foco principal detectado es ${criticalSource}.` : "El primer paso recomendado es cargar registros ambientales suficientes para activar diagnóstico, reportabilidad y seguimiento.";
  const status = `El reporte está en estado: ${readiness.status} (${readiness.score}% de preparación).`;
  const nextStep = readiness.score >= 85 ? "Se recomienda presentar el reporte y usar la agenda de decisión para acordar próximos responsables y fechas." : readiness.score >= 60 ? "Se puede presentar con observaciones, priorizando el cierre de brechas antes de una entrega formal al cliente." : "Se recomienda completar información, acciones y trazabilidad antes de presentarlo como reporte final.";

  return { intro, focus, status, nextStep, text: `${intro}\n${focus}\n${status}\n${nextStep}` };
}

function buildExecutiveBrief({ activeConstructora, activePreset, actionsSummary, filters, report }) {
  const empresa = activeConstructora?.nombre || "La empresa";
  const preset = activePreset?.name || "ambiental";
  const totalEmissions = findKpi(report, "emisiones")?.value || "Sin datos";
  const criticalSource = findKpi(report, "fuente")?.value || "Sin datos";
  const criticalStage = findKpi(report, "etapa")?.value || findKpi(report, "proceso")?.value || "Sin datos";
  const criticalCategory = findKpi(report, "categoria")?.value || "Sin datos";
  const records = report?.rows?.length || 0;
  const activeActions = actionsSummary?.active || 0;
  const completedActions = actionsSummary?.completed || 0;
  const overdueActions = actionsSummary?.overdue || 0;
  const traceabilityPct = actionsSummary?.traceabilityPct || 0;
  const completionPct = actionsSummary?.completionPct || 0;
  const actionPlan = Array.isArray(actionsSummary?.latestActions) ? actionsSummary.latestActions.slice(0, 5) : [];
  const decisionAgenda = buildDecisionAgenda({ actionsSummary, criticalSource, records });
  const readiness = buildReportReadiness({ actionsSummary, records, totalEmissions });
  const risks = buildReportRisks({ actionsSummary, readiness });
  const clientSummary = buildClientSummary({ empresa, criticalSource, readiness, records, totalEmissions });
  const hasPeriod = filters?.fecha_inicio || filters?.fecha_fin;
  const period = hasPeriod ? `${filters.fecha_inicio || "inicio"} a ${filters.fecha_fin || "hoy"}` : "periodo disponible";

  const headline = `${empresa} presenta una lectura ambiental ${records ? "activa" : "pendiente de datos"} para el preset ${preset}.`;
  const diagnosis = records ? `En el ${periodoClean(period)}, se analizaron ${records} registros y se observó una huella total de ${totalEmissions}. El foco principal se concentra en ${criticalSource}, asociado a ${criticalStage} y a la categoría ${criticalCategory}.` : `En el ${periodoClean(period)}, todavía no existen registros suficientes para construir una lectura ambiental completa.`;
  const management = actionsSummary?.total ? `La gestión accionable registra ${actionsSummary.total} acciones: ${activeActions} activas, ${completedActions} completadas y ${overdueActions} vencidas. El avance de cierre es ${completionPct}% y la trazabilidad operacional alcanza ${traceabilityPct}%.` : "Todavía no existen acciones ambientales registradas para cerrar el ciclo entre medición, gestión y seguimiento.";
  const priority = records ? `Priorizar acciones sobre ${criticalSource}, reforzar evidencia operacional y revisar el avance de acciones activas. Un nivel de trazabilidad bajo debe corregirse vinculando acciones a obras, lotes, registros o evidencias.` : "Priorizar carga o importación de registros ambientales para activar diagnóstico, acciones y reportabilidad ejecutiva.";

  const bullets = [`Huella total: ${totalEmissions}`, `Fuente crítica: ${criticalSource}`, `Etapa/proceso crítico: ${criticalStage}`, `Categoría dominante: ${criticalCategory}`, `Acciones activas: ${activeActions}`, `Trazabilidad de acciones: ${traceabilityPct}%`];

  const text = [
    "INFORME EJECUTIVO AMBIENTAL",
    `Empresa: ${empresa}`,
    `Preset: ${preset}`,
    `Periodo: ${periodoClean(period)}`,
    "",
    headline,
    "",
    "Resumen para cliente:",
    clientSummary.text,
    "",
    "Riesgos y brechas:",
    ...risks.map((risk, index) => `${index + 1}. [${risk.level}] ${risk.title} · ${risk.description} Acción sugerida: ${risk.action}`),
    "",
    "Estado de preparación del reporte:",
    `${readiness.status} · ${readiness.score}% (${readiness.passed}/${readiness.total} criterios cumplidos)`,
    ...readiness.checks.map((check) => `- ${check.passed ? "OK" : "Pendiente"}: ${check.label} · ${check.detail}`),
    "",
    "Diagnóstico:",
    diagnosis,
    "",
    "Gestión accionable:",
    management,
    "",
    "Prioridad sugerida:",
    priority,
    "",
    "Agenda de decisión ejecutiva:",
    ...(decisionAgenda.length ? decisionAgenda.map((item, index) => `${index + 1}. [${item.priority}] ${item.decision} · ${item.reason} Resultado esperado: ${item.expected}`) : ["Sin decisiones sugeridas para este periodo."]),
    "",
    "Indicadores clave:",
    ...bullets.map((item) => `- ${item}`),
    "",
    "Plan de acción ambiental:",
    ...(actionPlan.length ? actionPlan.map(formatActionLine) : ["Sin acciones recientes para listar en el plan."]),
  ].join("\n");

  return { actionPlan, bullets, clientSummary, decisionAgenda, diagnosis, headline, management, priority, readiness, risks, text };
}

function periodoClean(value) {
  return String(value || "periodo disponible").replace(/\s+/g, " ").trim();
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function ReportesPage({ activeConstructora: propActiveConstructora, activeConstructoraId: propActiveConstructoraId, onSetActiveView }) {
  const context = useConstructoraActiva();
  const activeConstructora = propActiveConstructora || context.activeConstructora;
  const activeConstructoraId = propActiveConstructoraId || context.activeConstructoraId;
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const reportConfig = reportByPreset[activePreset.key] || construccionReport;
  const [allRows, setAllRows] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [actionsSummary, setActionsSummary] = useState(null);
  const [filters, setFilters] = useState(defaultFilters);
  const [draftFilters, setDraftFilters] = useState(defaultFilters);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState("");
  const [creatingRiskKey, setCreatingRiskKey] = useState("");
  const [riskActionFeedback, setRiskActionFeedback] = useState("");

  const loadReport = async (showLoading = true) => {
    if (!activeConstructoraId) return;
    try {
      if (showLoading) setLoading(true);
      setError("");
      const [recordsResult, dashboardResult, actionsSummaryResult] = await Promise.allSettled([getEmpresaRegistrosAmbientales(activeConstructoraId), getConstructoraDashboard(activeConstructoraId, { light: "1" }), getTraceableActionsSummary(activeConstructoraId)]);

      if (recordsResult.status === "fulfilled") setAllRows(normalizeReportRows(recordsResult.value));
      else setAllRows([]);

      if (dashboardResult.status === "fulfilled") setDashboardData(dashboardResult.value);
      else setDashboardData(null);

      if (actionsSummaryResult.status === "fulfilled") setActionsSummary(actionsSummaryResult.value);
      else setActionsSummary(null);

      if (recordsResult.status === "rejected" && dashboardResult.status === "rejected") throw recordsResult.reason || dashboardResult.reason;
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudieron cargar los registros para construir el reporte.");
    } finally {
      if (showLoading) setLoading(false);
      setHasLoaded(true);
    }
  };

  useEffect(() => {
    setAllRows([]);
    setDashboardData(null);
    setActionsSummary(null);
    setFilters(defaultFilters);
    setDraftFilters(defaultFilters);
    setHasLoaded(false);
    if (!activeConstructoraId) return undefined;
    loadReport(true);
    const intervalId = window.setInterval(() => loadReport(false), 10000);
    return () => window.clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConstructoraId, activePreset.key]);

  const report = useMemo(() => reportConfig.buildReport(allRows, filters, { activeConstructora, activePreset, dashboardData, filters }), [activeConstructora, activePreset, allRows, dashboardData, filters, reportConfig]);

  const executiveBrief = useMemo(() => buildExecutiveBrief({ activeConstructora, activePreset, actionsSummary, filters, report }), [activeConstructora, activePreset, actionsSummary, filters, report]);

  const exportPayload = useMemo(
    () => ({ ...reportConfig.buildExportPayload(report, { activeConstructora, activePreset, filters }), informe_ejecutivo: executiveBrief, resumen_cliente: executiveBrief.clientSummary, riesgos_brechas: executiveBrief.risks, acciones_resumen: actionsSummary, agenda_decision: executiveBrief.decisionAgenda, estado_preparacion: executiveBrief.readiness, plan_accion: executiveBrief.actionPlan }),
    [activeConstructora, activePreset, actionsSummary, executiveBrief, filters, report, reportConfig]
  );

  async function handleCreateRiskAction(risk) {
    if (!activeConstructoraId || risk.key === "sin_brechas") return;
    try {
      setCreatingRiskKey(risk.key);
      setRiskActionFeedback("");
      await createTraceableAction(activeConstructoraId, buildRiskActionPayload(risk));
      setRiskActionFeedback(`Acción creada desde brecha: ${risk.title}`);
      await loadReport(false);
      window.setTimeout(() => setRiskActionFeedback(""), 2600);
    } catch (requestError) {
      setRiskActionFeedback(requestError.response?.data?.error || "No se pudo crear la acción desde la brecha.");
    } finally {
      setCreatingRiskKey("");
    }
  }

  function openFiltersModal() {
    setDraftFilters(filters);
    setIsFiltersModalOpen(true);
  }

  function applyFilters() {
    setFilters({ fecha_inicio: draftFilters.fecha_inicio || "", fecha_fin: draftFilters.fecha_fin || "", agrupacion: draftFilters.agrupacion || "mes" });
    setIsFiltersModalOpen(false);
  }

  function clearFilters() {
    setDraftFilters(defaultFilters);
    setFilters(defaultFilters);
    setIsFiltersModalOpen(false);
  }

  if (!activeConstructoraId) {
    return <main className="mx-auto max-w-7xl text-[var(--text-main)]"><h1 className="text-4xl font-black">Reportes</h1><div className="mt-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center text-[var(--text-muted)]">Selecciona o crea una empresa para revisar reportes temporales.</div></main>;
  }

  if (loading && !hasLoaded) return <PlatformLoader title="Cargando reportes" description="Estamos preparando tendencias, KPIs del periodo y tablas ambientales del preset activo." />;

  return (
    <main className="mx-auto max-w-7xl space-y-8 text-[var(--text-main)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--secondary)]">Reporte adaptativo</p>
          <h1 className="mt-2 text-3xl font-black sm:text-4xl">Reportes</h1>
          <p className="mt-2 text-[var(--text-muted)]">Analiza tendencias, fuentes criticas, acciones y trazabilidad con lenguaje del preset activo.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ReportExportActions executiveBriefText={executiveBrief.text} exportPayload={exportPayload} report={report} reportConfig={reportConfig} />
          <button onClick={() => loadReport(true)} className="inline-flex items-center gap-2 rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-bold text-[#075985] shadow-[0_12px_24px_rgba(15,23,42,0.05)]"><RefreshCcw size={18} />Actualizar</button>
        </div>
      </div>

      {isFiltersModalOpen && <ReportFiltersModal draftFilters={draftFilters} groupingOptions={reportConfig.groupingOptions} onApply={applyFilters} onChange={setDraftFilters} onClear={clearFilters} onClose={() => setIsFiltersModalOpen(false)} />}
      {error && <div className="rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-6 text-[#B42318]">{error}</div>}
      {riskActionFeedback && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-black text-emerald-800">{riskActionFeedback}</div>}

      <ReportHero activeConstructora={activeConstructora} filters={filters} onOpenFilters={openFiltersModal} preset={activePreset} report={report} reportConfig={reportConfig} />
      <ClientSummaryCard summary={executiveBrief.clientSummary} />
      <ReportReadinessCard readiness={executiveBrief.readiness} />
      <ReportRisksCard creatingRiskKey={creatingRiskKey} onCreateAction={handleCreateRiskAction} risks={executiveBrief.risks} />
      <ExecutiveBriefCard brief={executiveBrief} />
      <DecisionAgendaCard agenda={executiveBrief.decisionAgenda} />
      <ReportActionPlan onOpenActions={() => onSetActiveView?.("acciones")} actions={executiveBrief.actionPlan} />
      <ReportActionsSummary onOpenActions={() => onSetActiveView?.("acciones")} summary={actionsSummary} />

      {!loading && !report.rows.length ? <EmptyReportState message={report.emptyMessage} onImport={() => onSetActiveView?.("importaciones")} onPrimary={() => onSetActiveView?.(report.primaryModuleView || "emisiones")} preset={activePreset} /> : <><ReportKpiGrid kpis={report.kpis} /><ReportCharts report={report} reportConfig={reportConfig} /><ReportTable report={report} reportConfig={reportConfig} /></>}
    </main>
  );
}

function ClientSummaryCard({ summary }) {
  const [copied, setCopied] = useState(false);
  if (!summary) return null;
  async function handleCopy() {
    await copyText(summary.text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  return <section className="rounded-3xl border border-emerald-200 bg-emerald-50/70 p-5 shadow-[var(--shadow-card)]"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Resumen para cliente</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Versión corta para reunión o correo</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-900">Mensaje breve para explicar el estado ambiental sin entrar en todo el detalle técnico del reporte.</p></div><button type="button" onClick={handleCopy} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-800 shadow-sm hover:bg-emerald-50"><CheckCircle2 size={17} />{copied ? "Resumen copiado" : "Copiar resumen"}</button></div><div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">{[summary.intro, summary.focus, summary.status, summary.nextStep].map((paragraph, index) => <div key={`${paragraph}-${index}`} className="rounded-2xl border border-emerald-100 bg-white px-4 py-3 text-sm font-semibold leading-6 text-slate-700">{paragraph}</div>)}</div></section>;
}

function ReportReadinessCard({ readiness }) {
  if (!readiness) return null;
  return <section className="rounded-3xl border border-sky-200 bg-sky-50/70 p-5 shadow-[var(--shadow-card)]"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-sky-700">Estado de preparación</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">{readiness.status}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-sky-900">El reporte cumple {readiness.passed} de {readiness.total} criterios mínimos para presentación ejecutiva.</p></div><div className="rounded-3xl border border-sky-200 bg-white px-5 py-4 text-center shadow-sm"><p className="text-[10px] font-black uppercase tracking-wide text-sky-700">Preparación</p><p className="mt-1 text-3xl font-black text-sky-950">{readiness.score}%</p></div></div><div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">{readiness.checks.map((check) => <div key={check.key} className="rounded-2xl border border-sky-100 bg-white px-4 py-3"><div className="flex items-center gap-2"><span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-black ${check.passed ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{check.passed ? "✓" : "!"}</span><p className="text-sm font-black text-slate-800">{check.label}</p></div><p className="mt-2 text-xs font-semibold leading-5 text-slate-500">{check.detail}</p></div>)}</div></section>;
}

function ReportRisksCard({ creatingRiskKey = "", onCreateAction, risks = [] }) {
  return <section className="rounded-3xl border border-rose-200 bg-rose-50/60 p-5 shadow-[var(--shadow-card)]"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-rose-700">Riesgos y brechas</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Puntos que pueden debilitar el reporte</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-rose-900">Brechas detectadas antes de presentar el informe a cliente, gerencia o licitación.</p></div><div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">{risks.map((risk, index) => <article key={`${risk.key}-${index}`} className="rounded-3xl border border-rose-100 bg-white p-4 shadow-[0_10px_22px_rgba(15,23,42,0.04)]"><div className="flex items-center justify-between gap-3"><span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-black text-rose-800">{risk.level}</span><span className="text-xs font-black uppercase tracking-wide text-slate-400">Brecha {index + 1}</span></div><h3 className="mt-3 text-base font-black text-[var(--text-main)]">{risk.title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{risk.description}</p><p className="mt-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-600"><strong>Acción sugerida:</strong> {risk.action}</p>{risk.key !== "sin_brechas" ? <button type="button" disabled={creatingRiskKey === risk.key} onClick={() => onCreateAction?.(risk)} className="mt-3 inline-flex items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-black text-rose-800 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"><CheckCircle2 size={15} />{creatingRiskKey === risk.key ? "Creando acción..." : "Crear acción desde brecha"}</button> : null}</article>)}</div></section>;
}

function ExecutiveBriefCard({ brief }) {
  if (!brief) return null;
  return <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-[var(--shadow-card)]"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Informe ejecutivo</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Lectura ambiental para gerencia</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--text-muted)]">{brief.headline}</p></div><div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-center"><p className="text-[10px] font-black uppercase tracking-wide text-emerald-700">Salida</p><p className="mt-1 text-sm font-black text-emerald-950">TXT + JSON</p></div></div><div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_0.8fr]"><div className="space-y-4"><BriefBlock title="Diagnóstico" text={brief.diagnosis} /><BriefBlock title="Gestión accionable" text={brief.management} /><BriefBlock title="Prioridad sugerida" text={brief.priority} /></div><div className="rounded-3xl border border-slate-100 bg-slate-50 p-4"><p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Indicadores clave</p><div className="mt-3 space-y-2">{brief.bullets.map((bullet) => <div key={bullet} className="rounded-2xl border border-slate-100 bg-white px-3 py-2 text-sm font-bold text-slate-700">{bullet}</div>)}</div></div></div></section>;
}

function BriefBlock({ text, title }) {
  return <div className="rounded-3xl border border-slate-100 bg-slate-50 p-4"><p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">{title}</p><p className="mt-2 text-sm leading-6 text-slate-700">{text}</p></div>;
}

function DecisionAgendaCard({ agenda = [] }) {
  return <section className="rounded-3xl border border-amber-200 bg-amber-50/70 p-5 shadow-[var(--shadow-card)]"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-amber-700">Agenda de decisión ejecutiva</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Decisiones sugeridas para gerencia</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-amber-900">Prioridades concretas para transformar la lectura ambiental en acuerdos, responsables y seguimiento.</p></div><div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">{agenda.length ? agenda.map((item, index) => <article key={`${item.decision}-${index}`} className="rounded-3xl border border-amber-100 bg-white p-4 shadow-[0_10px_22px_rgba(15,23,42,0.04)]"><div className="flex items-center justify-between gap-3"><span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-black text-amber-800">{item.priority}</span><span className="text-xs font-black uppercase tracking-wide text-slate-400">Decisión {index + 1}</span></div><h3 className="mt-3 text-base font-black text-[var(--text-main)]">{item.decision}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{item.reason}</p><p className="mt-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-600"><strong>Resultado esperado:</strong> {item.expected}</p></article>) : <div className="rounded-3xl border border-dashed border-amber-200 bg-white/70 p-6 text-center text-sm font-bold text-amber-900">Sin decisiones sugeridas para este periodo.</div>}</div></section>;
}

function ReportActionPlan({ actions = [], onOpenActions }) {
  return <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[var(--shadow-card)]"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Plan de acción ambiental</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Acciones priorizadas para seguimiento</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">Lista de acciones recientes para revisar responsables, vencimientos y trazabilidad operacional desde el reporte.</p></div><button type="button" onClick={onOpenActions} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-800 shadow-sm hover:bg-emerald-100"><CheckCircle2 size={17} />Abrir tablero</button></div>{actions.length ? <div className="mt-5 space-y-3">{actions.map((action, index) => <article key={action.id || `${action.title}-${index}`} className="grid gap-3 rounded-3xl border border-slate-100 bg-slate-50 p-4 lg:grid-cols-[1fr_170px_170px] lg:items-center"><div><p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">Acción {index + 1}</p><h3 className="mt-1 text-base font-black text-[var(--text-main)]">{action.title || "Acción ambiental"}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{action.description || "Sin descripción registrada."}</p><p className="mt-2 text-xs font-bold text-slate-500">{actionLinkLabel(action)}</p></div><div className="rounded-2xl border border-slate-100 bg-white px-3 py-2 text-sm"><p className="text-[10px] font-black uppercase tracking-wide text-slate-500">Responsable</p><p className="mt-1 font-black text-slate-800">{action.responsible || "Equipo ambiental"}</p></div><div className="rounded-2xl border border-slate-100 bg-white px-3 py-2 text-sm"><p className="text-[10px] font-black uppercase tracking-wide text-slate-500">Estado / fecha</p><p className="mt-1 font-black text-slate-800">{statusLabel(action.status)}</p><p className="text-xs font-bold text-slate-500">{action.dueDate || "Sin fecha"}</p></div></article>)}</div> : <div className="mt-5 rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm font-bold text-[var(--text-muted)]">No hay acciones recientes para listar en este reporte.</div>}</section>;
}

function ReportActionsSummary({ onOpenActions, summary }) {
  if (!summary) return null;
  return <section className="rounded-3xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-[var(--shadow-card)]"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Gestión accionable</p><h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Acciones ambientales del periodo</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-900">{summary.total ? `${summary.active} acciones siguen activas, ${summary.completed} están cerradas y ${summary.traceabilityPct || 0}% tiene vínculo operacional.` : "Aún no hay acciones ambientales trazables para incorporar al reporte."}</p></div><button type="button" onClick={onOpenActions} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-800 shadow-sm hover:bg-emerald-50"><CheckCircle2 size={17} />Revisar acciones</button></div><div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5"><ReportActionMetric icon={<CheckCircle2 size={16} />} label="Total" value={summary.total || 0} /><ReportActionMetric icon={<Clock3 size={16} />} label="Activas" value={summary.active || 0} /><ReportActionMetric icon={<Clock3 size={16} />} label="Vencidas" value={summary.overdue || 0} /><ReportActionMetric icon={<CheckCircle2 size={16} />} label="Cierre" value={`${summary.completionPct || 0}%`} /><ReportActionMetric icon={<CheckCircle2 size={16} />} label="Trazabilidad" value={`${summary.traceabilityPct || 0}%`} /></div></section>;
}

function ReportActionMetric({ icon, label, value }) {
  return <div className="rounded-2xl border border-emerald-200 bg-white/85 px-4 py-3 text-center"><div className="mx-auto flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">{icon}</div><p className="mt-2 text-[10px] font-black uppercase tracking-wide text-emerald-700">{label}</p><p className="mt-1 text-xl font-black text-emerald-950">{value}</p></div>;
}

function EmptyReportState({ message, onImport, onPrimary, preset }) {
  return <section className="rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_45%,#ECFDF5_100%)] p-8 text-center shadow-[var(--shadow-card)]"><div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-[#A7F3D0] bg-[#ECFDF5] text-[#047857]"><BarChart3 size={28} /></div><p className="mt-5 text-xs font-black uppercase tracking-[0.16em] text-[var(--primary-dark)]">Sin datos para {preset.name}</p><h2 className="mt-2 text-2xl font-black text-[var(--text-main)]">No hay registros en el periodo seleccionado</h2><p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-7 text-[var(--text-muted)]">{message}</p><div className="mt-6 flex flex-wrap justify-center gap-3"><button onClick={onImport} className="inline-flex items-center gap-2 rounded-2xl border border-[#A7F3D0] bg-[#ECFDF5] px-5 py-3 text-sm font-black text-[#047857] shadow-[0_12px_24px_rgba(15,23,42,0.06)]"><Database size={17} />Ir a Importacion de datos</button><button onClick={onPrimary} className="inline-flex items-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_12px_24px_rgba(14,124,102,0.18)]">Activar modulo operativo</button></div></section>;
}

export default ReportesPage;
