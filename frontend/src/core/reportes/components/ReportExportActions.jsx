import { Download, FileJson, Printer } from "lucide-react";

function ReportExportActions({ executiveBriefText, exportPayload, report, reportConfig }) {
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

  return (
    <div className="flex flex-wrap gap-3">
      <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-black text-slate-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
        <Printer size={18} />
        Imprimir reporte
      </button>
      {executiveBriefText ? (
        <button onClick={downloadExecutiveBrief} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-700 shadow-[0_10px_20px_rgba(15,23,42,0.05)]">
          <Download size={18} />
          Descargar informe TXT
        </button>
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
