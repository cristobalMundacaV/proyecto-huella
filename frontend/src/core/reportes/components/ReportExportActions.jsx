import { useState } from "react";
import { CheckCircle2, ClipboardCopy, Download, Printer } from "lucide-react";

function ReportExportActions({ executiveBriefText, report, reportConfig }) {
  const [copied, setCopied] = useState(false);

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
        Imprimir
      </button>

      {executiveBriefText ? (
        <>
          <button onClick={copyExecutiveBrief} className="inline-flex items-center gap-2 rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-black text-teal-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            {copied ? <CheckCircle2 size={18} /> : <ClipboardCopy size={18} />}
            {copied ? "Informe copiado" : "Copiar informe"}
          </button>
          <button onClick={downloadExecutiveBrief} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
            <Download size={18} />
            Descargar informe
          </button>
        </>
      ) : null}

      <button onClick={downloadCsv} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
        <Download size={18} />
        Descargar CSV
      </button>
    </div>
  );
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
