import { formatNumber } from "@/shared/utils/formatters";

function PendingFactorRecords({ factors, onApply, pendingRecords = [], suggestFactor }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-premium)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">Registros pendientes de factor</h2>
      <p className="mt-1 text-sm text-[var(--text-muted)]">{pendingRecords.length} registros sin calculo ambiental cerrado.</p>
      <div className="mt-5 overflow-x-auto rounded-2xl border border-[var(--border)]">
        <table className="min-w-[1100px] w-full text-sm">
          <thead className="bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
            <tr><th className="px-4 py-3 text-left">Fecha</th><th className="px-4 py-3 text-left">Modulo</th><th className="px-4 py-3 text-left">Categoria</th><th className="px-4 py-3 text-left">Fuente</th><th className="px-4 py-3 text-left">Lote</th><th className="px-4 py-3 text-right">Cantidad</th><th className="px-4 py-3 text-left">Unidad</th><th className="px-4 py-3 text-left">Sugerencia</th><th className="px-4 py-3 text-left">Accion</th></tr>
          </thead>
          <tbody>
            {pendingRecords.map((record) => {
              const suggestion = suggestFactor(record, factors);
              return (
                <tr key={record.id} className="border-t border-[var(--border)]">
                  <td className="px-4 py-3">{record.fecha || "-"}</td>
                  <td className="px-4 py-3">{record.metadata?.module || "-"}</td>
                  <td className="px-4 py-3">{record.metadata?.aserradero_category || record.categoria || "Otros"}</td>
                  <td className="px-4 py-3 font-semibold">{record.fuente_emision}</td>
                  <td className="px-4 py-3">{record.metadata?.lote || "-"}</td>
                  <td className="px-4 py-3 text-right">{formatNumber(record.cantidad, 2)}</td>
                  <td className="px-4 py-3">{record.unidad}</td>
                  <td className="px-4 py-3">{suggestion.factor?.actividad || "Sin sugerencia directa"}</td>
                  <td className="px-4 py-3"><button onClick={() => onApply(record, suggestion)} className="rounded-full bg-[var(--primary)] px-3 py-1 text-xs font-black text-white">Aplicar</button></td>
                </tr>
              );
            })}
            {!pendingRecords.length && <tr><td colSpan={9} className="px-4 py-8 text-center text-[var(--text-muted)]">No hay registros pendientes de factor.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default PendingFactorRecords;
