import { useState } from "react";
import { CheckCircle2, ClipboardCopy, Download, FileJson, FileText, Printer } from "lucide-react";

function ReportExportActions({ executiveBriefText, exportPayload, report, reportConfig }) {
  const [copied, setCopied] = useState(false);

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

  const downloadExecutiveBrief = () => {
    const blob = new Blob([executiveBriefText || ""], { type: "text/plain;charset=utf-8" });
    downloadBlob(blob, "informe-ejecutivo-carbono-zero.txt");
  };

  const downloadExecutiveMarkdown = () => {
    const markdown = buildExecutiveMarkdown(executiveBriefText);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    downloadBlob(blob, "informe-ejecutivo-carbono-zero.md");
  };

  const copyExecutiveBrief = async () => {
    const text = executiveBriefText || "";
    if (!text) return;
    await copyToClipboard(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="flex flex-wrap gap-3">
      <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-black text-slate-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
        <Printer size={18} />
        Imprimir reporte
      </button>
      {executiveBriefText ? (
        <>
          <button onClick={copyExecutiveBrief} className="inline-flex items-center gap-2 rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-black text-teal-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            {copied ? <CheckCircle2 size={18} /> : <ClipboardCopy size={18} />}
            {copied ? "Informe copiado" : "Copiar informe"}
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
    </div>
  );
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
