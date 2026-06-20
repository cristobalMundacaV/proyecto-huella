import { useState } from "react";
import { CheckCircle2, ClipboardCopy, Download, FileJson, FileText, Printer } from "lucide-react";

function ReportExportActions({ executiveBriefText, exportPayload, report, reportConfig }) {
  const [copiedMode, setCopiedMode] = useState("");
  const improvementCycle = exportPayload?.ciclo_mejora || null;
  const priorityFollowUp = exportPayload?.seguimiento_prioritario || null;
  const cycleActions = Array.isArray(improvementCycle?.latestActions) ? improvementCycle.latestActions : [];
  const priorityItems = Array.isArray(priorityFollowUp?.items) ? priorityFollowUp.items : [];
  const hasOperationalSummary = Boolean(improvementCycle || priorityFollowUp || cycleActions.length || priorityItems.length);

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: "application/json" });
    downloadBlob(blob, "reporte-carbono-zero.json");
  };

  const downloadCsv = () => {
    const columns = reportConfig.tableColumns || [];
    const header = columns.map((column) => escapeCsv(column.label)).join(",");
    const rows = report.rows.map((row) => columns.map((column) => escapeCsv(column.resolver(row))).join(","));
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
    downloadBlob(blob, "reporte-carbono-zero.csv");
  };

  const downloadCycleCsv = () => {
    const headers = ["Origen", "Acción", "Estado", "Responsable", "Fecha objetivo", "Fuente", "KPI seguimiento"];
    const rows = cycleActions.map((action) => [
      originLabel(action),
      action.title || "Acción ambiental",
      statusLabel(action.status),
      action.responsible || "Equipo ambiental",
      action.dueDate || "Sin fecha",
      action.source || "Reporte ejecutivo",
      action.trackingKpi || "Sin KPI",
    ]);
    const header = headers.map(escapeCsv).join(",");
    const body = rows.map((row) => row.map(escapeCsv).join(","));
    const blob = new Blob([[header, ...body].join("\n")], { type: "text/csv;charset=utf-8" });
    downloadBlob(blob, "ciclo-mejora-carbono-zero.csv");
  };

  const downloadPriorityFollowUpCsv = () => {
    const headers = ["Prioridad", "Motivo", "Origen", "Acción", "Estado", "Responsable", "Fecha objetivo", "Fuente", "KPI seguimiento"];
    const rows = priorityItems.map((item) => [
      item.level || "Sin prioridad",
      item.reason || "Sin motivo",
      item.origin?.label || originLabel(item.action),
      item.action?.title || "Acción ambiental",
      statusLabel(item.action?.status),
      item.action?.responsible || "Equipo ambiental",
      item.action?.dueDate || "Sin fecha",
      item.action?.source || "Reporte ejecutivo",
      item.action?.trackingKpi || "Sin KPI",
    ]);
    const header = headers.map(escapeCsv).join(",");
    const body = rows.map((row) => row.map(escapeCsv).join(","));
    const blob = new Blob([[header, ...body].join("\n")], { type: "text/csv;charset=utf-8" });
    downloadBlob(blob, "seguimiento-prioritario-carbono-zero.csv");
  };

  const downloadExecutiveBrief = () => {
    const blob = new Blob([executiveBriefText || ""], { type: "text/plain;charset=utf-8" });
    downloadBlob(blob, "informe-ejecutivo-carbono-zero.txt");
  };

  const downloadExecutiveMarkdown = () => {
    const markdown = buildExecutiveMarkdown(executiveBriefText);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    downloadBlob(blob, "informe-ejecutivo-carbono-zero.md");
  };

  const downloadOperationalSummary = () => {
    const text = buildOperationalSummary({ improvementCycle, priorityFollowUp });
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    downloadBlob(blob, "seguimiento-operativo-carbono-zero.txt");
  };

  const downloadOperationalMarkdown = () => {
    const markdown = buildOperationalMarkdown({ improvementCycle, priorityFollowUp });
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    downloadBlob(blob, "seguimiento-operativo-carbono-zero.md");
  };

  const copyExecutiveBrief = async () => {
    const text = executiveBriefText || "";
    if (!text) return;
    await copyToClipboard(text);
    confirmCopy("text");
  };

  const copyExecutiveMarkdown = async () => {
    const markdown = buildExecutiveMarkdown(executiveBriefText);
    if (!markdown) return;
    await copyToClipboard(markdown);
    confirmCopy("markdown");
  };

  const copyOperationalSummary = async () => {
    const text = buildOperationalSummary({ improvementCycle, priorityFollowUp });
    if (!text) return;
    await copyToClipboard(text);
    confirmCopy("operational");
  };

  function confirmCopy(mode) {
    setCopiedMode(mode);
    window.setTimeout(() => setCopiedMode(""), 1800);
  }

  return (
    <div className="flex flex-wrap gap-3">
      <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-black text-slate-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
        <Printer size={18} />
        Imprimir reporte
      </button>
      {executiveBriefText ? (
        <>
          <button onClick={copyExecutiveBrief} className="inline-flex items-center gap-2 rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-black text-teal-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            {copiedMode === "text" ? <CheckCircle2 size={18} /> : <ClipboardCopy size={18} />}
            {copiedMode === "text" ? "Informe copiado" : "Copiar informe"}
          </button>
          <button onClick={copyExecutiveMarkdown} className="inline-flex items-center gap-2 rounded-2xl border border-violet-200 bg-white px-4 py-3 text-sm font-black text-violet-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            {copiedMode === "markdown" ? <CheckCircle2 size={18} /> : <ClipboardCopy size={18} />}
            {copiedMode === "markdown" ? "Markdown copiado" : "Copiar MD"}
          </button>
          <button onClick={downloadExecutiveBrief} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            <Download size={18} />
            Descargar informe TXT
          </button>
          <button onClick={downloadExecutiveMarkdown} className="inline-flex items-center gap-2 rounded-2xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm font-black text-violet-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            <FileText size={18} />
            Descargar informe MD
          </button>
        </>
      ) : null}
      <button onClick={downloadJson} className="inline-flex items-center gap-2 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-black text-sky-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
        <FileJson size={18} />
        Descargar JSON
      </button>
      <button onClick={downloadCsv} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
        <Download size={18} />
        Descargar CSV
      </button>
      {hasOperationalSummary ? (
        <>
          <button onClick={copyOperationalSummary} className="inline-flex items-center gap-2 rounded-2xl border border-cyan-200 bg-white px-4 py-3 text-sm font-black text-cyan-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            {copiedMode === "operational" ? <CheckCircle2 size={18} /> : <ClipboardCopy size={18} />}
            {copiedMode === "operational" ? "Seguimiento copiado" : "Copiar seguimiento"}
          </button>
          <button onClick={downloadOperationalSummary} className="inline-flex items-center gap-2 rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm font-black text-cyan-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            <Download size={18} />
            Seguimiento TXT
          </button>
          <button onClick={downloadOperationalMarkdown} className="inline-flex items-center gap-2 rounded-2xl border border-cyan-200 bg-white px-4 py-3 text-sm font-black text-cyan-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            <FileText size={18} />
            Seguimiento MD
          </button>
        </>
      ) : null}
      {cycleActions.length ? (
        <button onClick={downloadCycleCsv} className="inline-flex items-center gap-2 rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm font-black text-cyan-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
          <Download size={18} />
          Ciclo CSV
        </button>
      ) : null}
      {priorityItems.length ? (
        <button onClick={downloadPriorityFollowUpCsv} className="inline-flex items-center gap-2 rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm font-black text-orange-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
          <Download size={18} />
          Prioridades CSV
        </button>
      ) : null}
    </div>
  );
}

function buildOperationalSummary({ improvementCycle, priorityFollowUp }) {
  const cycle = improvementCycle || {};
  const followUp = priorityFollowUp || {};
  const priorityItems = Array.isArray(followUp.items) ? followUp.items : [];

  return [
    "SEGUIMIENTO OPERATIVO CARBONO ZERO",
    "",
    "Ciclo de mejora:",
    `${cycle.status || "Sin ciclo registrado"} · ${cycle.total || 0} acciones desde reportes · ${cycle.completed || 0} cerradas · ${cycle.open || 0} abiertas · ${cycle.completionPct || 0}% de cierre.`,
    `Próximo paso: ${cycle.nextStep || "Sin próximo paso definido."}`,
    "",
    "Seguimiento prioritario:",
    `${followUp.status || "Sin prioridades abiertas"} · ${followUp.totalOpen || 0} abiertas · ${followUp.overdue || 0} vencidas · ${followUp.dueSoon || 0} próximas a vencer · ${followUp.validation || 0} en validación.`,
    `Próximo paso: ${followUp.nextStep || "Sin próximo paso definido."}`,
    "",
    "Prioridades:",
    ...(priorityItems.length ? priorityItems.map(formatPriorityLine) : ["Sin acciones prioritarias abiertas."]),
  ].join("\n");
}

function buildOperationalMarkdown({ improvementCycle, priorityFollowUp }) {
  const cycle = improvementCycle || {};
  const followUp = priorityFollowUp || {};
  const priorityItems = Array.isArray(followUp.items) ? followUp.items : [];

  return [
    "# Seguimiento operativo Carbono Zero",
    "",
    "## Ciclo de mejora",
    `**Estado:** ${cycle.status || "Sin ciclo registrado"}`,
    `**Acciones desde reportes:** ${cycle.total || 0}`,
    `**Cerradas:** ${cycle.completed || 0}`,
    `**Abiertas:** ${cycle.open || 0}`,
    `**Cierre:** ${cycle.completionPct || 0}%`,
    `**Próximo paso:** ${cycle.nextStep || "Sin próximo paso definido."}`,
    "",
    "## Seguimiento prioritario",
    `**Estado:** ${followUp.status || "Sin prioridades abiertas"}`,
    `**Abiertas:** ${followUp.totalOpen || 0}`,
    `**Vencidas:** ${followUp.overdue || 0}`,
    `**Próximas a vencer:** ${followUp.dueSoon || 0}`,
    `**En validación:** ${followUp.validation || 0}`,
    `**Próximo paso:** ${followUp.nextStep || "Sin próximo paso definido."}`,
    "",
    "## Prioridades",
    ...(priorityItems.length ? priorityItems.map(formatPriorityMarkdownLine) : ["- Sin acciones prioritarias abiertas."]),
  ].join("\n");
}

function formatPriorityLine(item, index) {
  return `${index + 1}. [${item.level || "Sin prioridad"}] ${item.action?.title || "Acción ambiental"} · ${item.reason || "Sin motivo"} · Estado: ${statusLabel(item.action?.status)} · Fecha: ${item.action?.dueDate || "Sin fecha"}`;
}

function formatPriorityMarkdownLine(item) {
  return `- **[${item.level || "Sin prioridad"}]** ${item.action?.title || "Acción ambiental"} · ${item.reason || "Sin motivo"} · Estado: ${statusLabel(item.action?.status)} · Fecha: ${item.action?.dueDate || "Sin fecha"}`;
}

function buildExecutiveMarkdown(text = "") {
  const lines = String(text || "").split("\n");
  const title = lines[0] || "INFORME EJECUTIVO AMBIENTAL";
  const body = lines.slice(1);

  return body
    .reduce((markdownLines, line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        markdownLines.push("");
        return markdownLines;
      }

      if (trimmed.endsWith(":")) {
        markdownLines.push(`## ${trimmed.replace(/:$/, "")}`);
        return markdownLines;
      }

      if (trimmed.startsWith("- ")) {
        markdownLines.push(trimmed);
        return markdownLines;
      }

      if (/^\d+\./.test(trimmed)) {
        markdownLines.push(trimmed);
        return markdownLines;
      }

      markdownLines.push(trimmed);
      return markdownLines;
    }, [`# ${title}`, ""])
    .join("\n");
}

async function copyToClipboard(text) {
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

function originLabel(action = {}) {
  const origin = action?.metadata?.origin || "";
  const source = String(action?.source || "").toLowerCase();
  if (origin === "report_risk_gap") return "Brecha de reporte";
  if (origin === "report_decision_agenda") return "Decisión ejecutiva";
  if (source.includes("reporte ejecutivo")) return "Reporte ejecutivo";
  return action?.source || "Manual / operacional";
}

function statusLabel(status) {
  return {
    pendiente: "Pendiente",
    en_progreso: "En progreso",
    validacion: "En validación",
    completada: "Completada",
  }[status] || "Sin estado";
}

function escapeCsv(value) {
  const text = String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default ReportExportActions;
