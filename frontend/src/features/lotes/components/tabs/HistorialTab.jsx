function HistorialTab({
  history,
  historyLoading,
  historyPageInfo,
  onRejectHistoryExtraction,
  onValidateHistoryExtraction,
  validatingExtraction,
}) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Historial de obra</h2>
        <div className="text-sm text-slate-400">
          Registros: {historyPageInfo?.count ?? 0}
        </div>
      </div>

      {historyLoading && <p className="text-slate-400">Cargando historial...</p>}

      {!historyLoading && history.length === 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-[760px] w-full text-sm">
            <tbody>
              <tr className="border-y border-slate-800/60">
                <td className="py-8 text-center text-slate-400">
                  Sin movimientos registrados para esta obra.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {!historyLoading && history.length > 0 && (
        <div className="space-y-3">
          {history.map((entry) => (
            <div
              key={entry.id}
              className="rounded-2xl border border-slate-800 bg-slate-950 p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-100">
                    {entry.tipo}
                  </p>
                  <p className="text-xs text-slate-400">
                    {entry.fuente} - {entry.usuario || "sistema"}
                  </p>
                </div>
                <div className="text-xs text-slate-400">
                  {new Date(entry.created_at).toLocaleString()}
                </div>
              </div>

              <div className="mt-3 text-sm text-slate-300">
                {entry.changes?.length ? (
                  <table className="w-full text-sm">
                    <thead className="text-slate-400">
                      <tr>
                        <th className="text-left">Campo</th>
                        <th className="text-left">Anterior</th>
                        <th className="text-left">Nuevo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entry.changes.map((change) => (
                        <tr key={`${entry.id}-${change.field}`}>
                          <td className="py-1 pr-4">{change.field}</td>
                          <td className="py-1 text-slate-400">
                            {String(change.previous ?? "")}
                          </td>
                          <td className="py-1 font-semibold text-slate-100">
                            {String(change.new ?? "")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <pre className="whitespace-pre-wrap text-xs text-slate-400">
                    {JSON.stringify(
                      entry.raw_payload || entry.normalized_payload || {},
                      null,
                      2
                    )}
                  </pre>
                )}
              </div>

              {entry.tipo === "extraido" && entry.extraccion_id && (
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      onValidateHistoryExtraction(
                        entry.extraccion_id,
                        entry.normalized_payload || entry.raw_payload
                      )
                    }
                    disabled={validatingExtraction}
                    className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm font-bold text-emerald-200"
                  >
                    Validar y aplicar
                  </button>
                  <button
                    type="button"
                    onClick={() => onRejectHistoryExtraction(entry.extraccion_id)}
                    disabled={validatingExtraction}
                    className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-2 text-sm font-bold text-slate-200"
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

export default HistorialTab;
