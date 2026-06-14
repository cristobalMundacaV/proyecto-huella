import { getImportErrors, getImportRowStatus } from "@/presets/shared/importConfig";

function ImportPreviewTable({ columns = [], rows = [] }) {
  if (!rows.length) return null;
  return (
    <section className="overflow-x-auto rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] shadow-[var(--shadow-card)]">
      <table className="min-w-[1000px] w-full text-sm">
        <thead className="bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
          <tr>
            <th className="px-4 py-3 text-left">Fila</th>
            <th className="px-4 py-3 text-left">Estado</th>
            {columns.map((column) => <th key={column} className="px-4 py-3 text-left">{column}</th>)}
            <th className="px-4 py-3 text-left">Mensajes</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 50).map((row) => {
            const status = getImportRowStatus(row);
            return (
              <tr key={row.row_number} className="border-t border-[var(--border)]">
                <td className="px-4 py-3">{row.row_number}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${status.tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>{status.label}</span>
                </td>
                {columns.map((column) => <td key={column} className="px-4 py-3">{row.data?.[column] || "-"}</td>)}
                <td className="px-4 py-3 text-rose-700">{getImportErrors(row).join("; ")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

export default ImportPreviewTable;
