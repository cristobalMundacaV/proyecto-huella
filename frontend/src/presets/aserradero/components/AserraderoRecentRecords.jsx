import { formatNumber } from "@/shared/utils/formatters";

function AserraderoRecentRecords({ records = [] }) {
  const recentRecords = [...records]
    .sort((left, right) => new Date(right.fecha || 0) - new Date(left.fecha || 0))
    .slice(0, 8);

  return (
    <section className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-2 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
            Historial operativo
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Registros recientes</h2>
        </div>
        <span className="rounded-full border border-[var(--border)] bg-[var(--bg-main)] px-3 py-1 text-xs font-bold text-[var(--text-muted)]">
          {records.length} registros del modulo
        </span>
      </div>

      {recentRecords.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-xs font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">
                <th className="py-3 pr-4">Fecha</th>
                <th className="py-3 pr-4">Fuente</th>
                <th className="py-3 pr-4">Cantidad</th>
                <th className="py-3 pr-4">Factor</th>
                <th className="py-3 pr-4">Emisiones</th>
                <th className="py-3 pr-4">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {recentRecords.map((record) => (
                <tr key={record.id || `${record.fecha}-${record.fuente_emision}`} className="border-b border-[var(--border)] last:border-b-0">
                  <td className="py-3 pr-4 font-semibold text-[var(--text-main)]">{record.fecha || "-"}</td>
                  <td className="py-3 pr-4 text-[var(--text-main)]">{record.fuente_emision || "-"}</td>
                  <td className="py-3 pr-4 text-[var(--text-muted)]">
                    {formatNumber(record.cantidad || 0, 2)} {record.unidad || ""}
                  </td>
                  <td className="py-3 pr-4">
                    {Number(record.factor_emision || 0) ? (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
                        {formatNumber(record.factor_emision, 4)}
                      </span>
                    ) : (
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700">
                        Sin factor
                      </span>
                    )}
                  </td>
                  <td className="py-3 pr-4 font-bold text-[var(--text-main)]">
                    {formatNumber(record.emisiones_kg_co2e ?? record.emisiones ?? 0, 2)} kg CO2e
                  </td>
                  <td className="max-w-xs truncate py-3 pr-4 text-[var(--text-muted)]">
                    {buildMetadataSummary(record.metadata)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mt-4 rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-main)] p-6 text-sm font-semibold text-[var(--text-muted)]">
          Aun no hay registros en este modulo. Crea la primera operacion para activar sus KPIs.
        </div>
      )}
    </section>
  );
}

function buildMetadataSummary(metadata = {}) {
  const ignored = new Set(["preset", "module", "operation_type", "aserradero_category"]);
  return (
    Object.entries(metadata)
      .filter(([key, value]) => !ignored.has(key) && value !== undefined && value !== null && value !== "")
      .slice(0, 3)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" | ") || "Sin detalle"
  );
}

export default AserraderoRecentRecords;
