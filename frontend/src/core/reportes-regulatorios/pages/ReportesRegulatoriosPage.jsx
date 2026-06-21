import { useEffect, useState } from "react";
import { AlertTriangle, ClipboardCheck, FileCheck2, FileText, ShieldCheck } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalExecutiveReportCard from "@/core/environmental/components/EnvironmentalExecutiveReportCard";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import RegulatoryReadinessPanel from "@/core/environmental/components/RegulatoryReadinessPanel";
import RiskSignalsPanel from "@/core/environmental/components/RiskSignalsPanel";
import { getTraceableActionsSummary } from "@/features/intelligence/services/traceableActionsApi";
import {
  getComplianceAlerts,
  getEnvironmentalComplianceSummary,
  getEnvironmentalDocuments,
  getEnvironmentalVariables,
} from "@/features/environmental/services/environmentalComplianceApi";
import { getEnvironmentalExecutiveReport } from "@/features/environmental/services/environmentalExecutiveReportApi";

function ReportesRegulatoriosPage() {
  const { activeCompany, matrix } = useEnvironmentalContext();
  const [summary, setSummary] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [variables, setVariables] = useState([]);
  const [alerts, setAlerts] = useState([]);
<<<<<<< HEAD
  const [actionsSummary, setActionsSummary] = useState(null);
=======
  const [executiveReport, setExecutiveReport] = useState(null);
>>>>>>> a8ece32d88d69ca164574ee69c83f9b55f8b5b14

  useEffect(() => {
    if (!activeCompany?.constructora_id) return;
    Promise.all([
      getEnvironmentalComplianceSummary(activeCompany.constructora_id),
      getEnvironmentalDocuments(activeCompany.constructora_id),
      getEnvironmentalVariables(activeCompany.constructora_id),
      getComplianceAlerts(activeCompany.constructora_id),
<<<<<<< HEAD
      getTraceableActionsSummary(activeCompany.constructora_id),
    ])
      .then(([summaryData, documentData, variableData, alertData, actionsData]) => {
=======
      getEnvironmentalExecutiveReport(activeCompany.constructora_id),
    ])
      .then(([summaryData, documentData, variableData, alertData, executiveReportData]) => {
>>>>>>> a8ece32d88d69ca164574ee69c83f9b55f8b5b14
        setSummary(summaryData);
        setDocuments(documentData);
        setVariables(variableData);
        setAlerts(alertData);
<<<<<<< HEAD
        setActionsSummary(actionsData);
=======
        setExecutiveReport(executiveReportData);
>>>>>>> a8ece32d88d69ca164574ee69c83f9b55f8b5b14
      })
      .catch(() => {
        setSummary(null);
        setDocuments([]);
        setVariables([]);
        setAlerts([]);
<<<<<<< HEAD
        setActionsSummary(null);
=======
        setExecutiveReport(null);
>>>>>>> a8ece32d88d69ca164574ee69c83f9b55f8b5b14
      });
  }, [activeCompany?.constructora_id]);

  const readiness = buildReadiness({ actionsSummary, alerts, documents, summary, variables });
  const isConstruction = activeCompany?.preset === "construccion";
  const blocks = buildReportBlocks({ actionsSummary, alerts, documents, isConstruction, summary, variables });

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Reportes Regulatorios"
      description="Vista de preparacion para reportes ambientales. Muestra salidas esperadas y brechas, sin generar exportaciones."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />
      <EnvironmentalExecutiveReportCard report={executiveReport} />

      <ReportReadinessHero activeCompany={activeCompany} readiness={readiness} />

      <section className="grid gap-4 xl:grid-cols-4">
        {blocks.map((block) => (
          <ExecutiveReportBlock key={block.title} {...block} />
        ))}
      </section>

      <section className="rounded-[24px] border border-amber-200 bg-amber-50/70 p-5">
        <div className="flex items-start gap-3">
          <span className="rounded-2xl border border-amber-200 bg-white p-2 text-amber-800">
            <AlertTriangle size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-amber-950">Brechas antes de presentar</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {readiness.gaps.map((gap) => (
                <p key={gap} className="rounded-2xl border border-amber-100 bg-white/80 p-3 text-sm font-bold text-amber-900">{gap}</p>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.85fr]">
        <RegulatoryReadinessPanel matrix={matrix} />
        <RiskSignalsPanel matrix={matrix} />
      </div>

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="rounded-xl border border-emerald-200 bg-emerald-50 p-2 text-emerald-800">
            <ClipboardCheck size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-[var(--text-main)]">Criterio de preparacion</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              Un reporte esta listo cuando cada salida regulatoria tiene documentos validados, variables calculables y alertas abiertas bajo control.
            </p>
            <p className="mt-3 text-sm font-bold text-[var(--text-main)]">
              Estado actual: {summary?.documentos_validados ?? 0} documentos validados, {summary?.total_variables ?? 0} variables y {summary?.alertas_abiertas ?? 0} alertas abiertas.
            </p>
          </div>
        </div>
      </section>
    </EnvironmentalShell>
  );
}

function ReportReadinessHero({ activeCompany, readiness }) {
  const tone = readiness.score >= 80 ? "emerald" : readiness.score >= 55 ? "amber" : "rose";
  const toneClass = {
    emerald: "border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.95))] text-emerald-900",
    amber: "border-amber-200 bg-[linear-gradient(135deg,rgba(255,251,235,0.98),rgba(255,255,255,0.95))] text-amber-900",
    rose: "border-rose-200 bg-[linear-gradient(135deg,rgba(255,241,242,0.98),rgba(255,255,255,0.95))] text-rose-900",
  }[tone];

  return (
    <section className={`rounded-[28px] border p-6 shadow-[0_24px_70px_rgba(15,23,42,0.10)] ${toneClass}`}>
      <div className="grid gap-6 lg:grid-cols-[1fr_220px] lg:items-center">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] opacity-75">Estado del reporte</p>
          <h1 className="mt-3 text-3xl font-black leading-tight text-slate-950 sm:text-4xl">{readiness.status}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
            {activeCompany?.nombre || "La empresa"} tiene {readiness.summary}. Proximo paso: {readiness.nextStep}
          </p>
        </div>
        <div className="rounded-3xl border border-white/70 bg-white/75 p-5 text-center shadow-sm">
          <p className="text-xs font-black uppercase tracking-wide text-slate-500">Preparacion</p>
          <p className="mt-2 text-5xl font-black text-slate-950">{readiness.score}%</p>
        </div>
      </div>
    </section>
  );
}

function ExecutiveReportBlock({ detail, icon: Icon, title, value, tone }) {
  const toneClass = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-900",
    cyan: "border-cyan-200 bg-cyan-50 text-cyan-900",
    violet: "border-violet-200 bg-violet-50 text-violet-900",
    rose: "border-rose-200 bg-rose-50 text-rose-900",
  }[tone];

  return (
    <article className={`rounded-2xl border p-5 ${toneClass}`}>
      <Icon size={20} />
      <h2 className="mt-3 text-base font-black">{title}</h2>
      <p className="mt-2 text-2xl font-black">{value}</p>
      <p className="mt-2 line-clamp-3 text-sm font-semibold leading-6 opacity-80">{detail}</p>
    </article>
  );
}

function buildReadiness({ actionsSummary, alerts, documents, summary, variables }) {
  const openAlerts = alerts.filter((item) => item.estado === "abierta" || item.estado === "en_revision").length;
  const validatedDocs = summary?.documentos_validados || documents.filter((item) => item.estado_validacion === "valido").length;
  const totalDocs = documents.length;
  const hasDocuments = totalDocs > 0;
  const hasVariables = variables.length > 0;
  const hasActions = (actionsSummary?.total || 0) > 0;
  const traceabilityOk = Number(actionsSummary?.traceabilityPct || 0) >= 60;
  const checks = [hasDocuments, hasVariables, openAlerts === 0, hasActions, traceabilityOk];
  const score = Math.round((checks.filter(Boolean).length / checks.length) * 100);
  const status = score >= 80 ? "Listo para presentar" : score >= 55 ? "Presentable con observaciones" : "Requiere completar gestion";
  const gaps = [];
  if (!hasDocuments) gaps.push("Faltan documentos ambientales de respaldo.");
  if (validatedDocs < totalDocs) gaps.push("Hay documentos pendientes u observados.");
  if (!hasVariables) gaps.push("Faltan variables ambientales calculables.");
  if (openAlerts > 0) gaps.push(`${openAlerts} alertas abiertas requieren control.`);
  if (!hasActions) gaps.push("Faltan acciones ambientales para seguimiento.");
  if (hasActions && !traceabilityOk) gaps.push("Hay acciones con trazabilidad insuficiente.");
  return {
    score,
    status,
    gaps: gaps.length ? gaps : ["Sin brechas criticas antes de presentar."],
    summary: `${validatedDocs} documentos validados, ${variables.length} variables y ${openAlerts} alertas abiertas`,
    nextStep: gaps[0] || "Presentar informe y mantener seguimiento de evidencia.",
  };
}

function buildReportBlocks({ actionsSummary, alerts, documents, isConstruction, summary, variables }) {
  const openAlerts = alerts.filter((item) => item.estado === "abierta" || item.estado === "en_revision").length;
  const rcdDocs = documents.filter((item) => /rcd|resid|pesaje|dispos/i.test(`${item.nombre} ${item.tipo_documento}`)).length;
  const materialDocs = documents.filter((item) => /factura|guia|material|hormigon|acero/i.test(`${item.nombre} ${item.tipo_documento}`)).length;
  return [
    {
      icon: FileText,
      title: isConstruction ? "Huella y hallazgos de obra" : "Huella y hallazgos",
      value: `${summary?.total_variables || variables.length} variables`,
      detail: isConstruction ? `${materialDocs} respaldos de materiales y ${rcdDocs} documentos RCD detectados.` : `${documents.length} documentos y ${variables.length} variables para sustentar el informe.`,
      tone: "cyan",
    },
    {
      icon: ClipboardCheck,
      title: "Decisiones recomendadas",
      value: openAlerts ? `${openAlerts} alertas` : "Sin alerta critica",
      detail: openAlerts ? "Controlar alertas abiertas antes de presentar el informe." : "Mantener evidencia y decisiones trazables para el periodo.",
      tone: openAlerts ? "rose" : "emerald",
    },
    {
      icon: ShieldCheck,
      title: "Acciones y evidencia",
      value: `${actionsSummary?.active || 0} activas`,
      detail: `${actionsSummary?.completed || 0} cerradas; trazabilidad ${actionsSummary?.traceabilityPct || 0}%.`,
      tone: "emerald",
    },
    {
      icon: FileCheck2,
      title: "Respaldo documental",
      value: `${summary?.documentos_validados || 0}/${documents.length}`,
      detail: isConstruction ? "Guias, vales de pesaje, disposicion autorizada y facturas deben sostener el reporte." : "Documentos validados versus total disponible.",
      tone: "violet",
    },
  ];
}

export default ReportesRegulatoriosPage;
