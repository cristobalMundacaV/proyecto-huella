import { Clock3, Inbox } from "lucide-react";

function HistorialTab({
  history,
  historyLoading,
  historyPageInfo,
  onRejectHistoryExtraction,
  onValidateHistoryExtraction,
  validatingExtraction,
}) {
  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
            Historial de obra
          </p>
          <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">Movimientos y trazabilidad</h2>
          <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
            Cambios, validaciones y movimientos asociados a la obra.
          </p>
        </div>
        <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
          Registros: {historyPageInfo?.count ?? 0}
        </div>
      </div>

      {historyLoading && (
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-8 text-center text-sm font-semibold text-[var(--text-muted)]">
          Cargando historial...
        </div>
      )}

      {!historyLoading && history.length === 0 && (
        <EmptyHistoryState />
      )}

      {!historyLoading && history.length > 0 && (
        <div className="space-y-3">
          {history.map((entry) => (
            <div
              key={entry.id}
              className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)]"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]">
                    <Clock3 size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-black text-[var(--text-main)]">{entry.tipo}</p>
                    <p className="text-xs font-medium text-[var(--text-muted)]">
                      {entry.fuente} · {entry.usuario || "sistema"}
                    </p>
                  </div>
                </div>
                <div className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-xs font-bold text-[var(--text-muted)]">
                  {new Date(entry.created_at).toLocaleString("es-CL")}
                </div>
              </div>

              <div className="mt-4 text-sm text-[var(--text-muted)]">
                {entry.changes?.length ? (
                  <div className="premium-table-wrapper overflow-x-auto">
                    <table className="premium-table w-full min-w-[640px] text-sm">
                      <thead className="border-b border-[var(--border)] text-[var(--text-muted)]">
                        <tr>
                          <th className="px-4 py-3 text-center">Campo</th>
                          <th className="px-4 py-3 text-center">Anterior</th>
                          <th className="px-4 py-3 text-center">Nuevo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entry.changes.map((change) => (
                          <tr key={`${entry.id}-${change.field}`} className="border-b border-[#E2E8F0]">
                            <td className="px-4 py-3 text-center font-semibold text-[var(--text-main)]">{change.field}</td>
                            <td className="px-4 py-3 text-center text-[var(--text-muted)]">{String(change.previous ?? "")}</td>
                            <td className="px-4 py-3 text-center font-bold text-[var(--primary-dark)]">{String(change.new ?? "")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <pre className="rounded-2xl border border-[var(--border)] bg-white p-4 text-xs text-[var(--text-muted)]">
                    {JSON.stringify(entry.raw_payload || entry.normalized_payload || {}, null, 2)}
                  </pre>
                )}
              </div>

              {entry.tipo === "extraido" && entry.extraccion_id && (
                <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    onClick={() =>
                      onValidateHistoryExtraction(
                        entry.extraccion_id,
                        entry.normalized_payload || entry.raw_payload
                      )
                    }
                    disabled={validatingExtraction}
                    className="premium-button-primary rounded-2xl px-4 py-2 text-sm font-bold"
                  >
                    Validar y aplicar
                  </button>
                  <button
                    type="button"
                    onClick={() => onRejectHistoryExtraction(entry.extraccion_id)}
                    disabled={validatingExtraction}
                    className="premium-button-secondary rounded-2xl px-4 py-2 text-sm font-bold"
                  >
                    Rechazar dato
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function EmptyHistoryState() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] px-6 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]">
        <Inbox size={22} />
      </div>
      <h3 className="mt-4 text-lg font-black text-[var(--text-main)]">Sin movimientos registrados</h3>
      <p className="mt-2 text-sm font-medium leading-6 text-[var(--text-muted)]">
        Cuando se validen evidencias, se creen registros o se apliquen cambios importantes, el historial aparecerá aquí con trazabilidad clara.
      </p>
    </div>
  );
}

export default HistorialTab;
