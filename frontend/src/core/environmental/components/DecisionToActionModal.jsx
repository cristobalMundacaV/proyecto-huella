import { CheckCircle2, Loader2, X } from "lucide-react";

const inputClass = "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100";

function DecisionToActionModal({ draft, error, loading, onClose, onConfirm, saving, setDraft }) {
  const payload = draft?.payload || {};
  const metadata = payload.metadata || {};

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
      <form onSubmit={onConfirm} className="relative max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
        <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50" aria-label="Cerrar modal">
          <X size={18} />
        </button>

        <div className="mb-5 pr-12">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Convertir en accion ambiental</p>
          <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">{payload.title || "Accion ambiental sugerida"}</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">Revisa la decision, ajusta responsable, fecha y evidencia, y envia la accion al tablero de seguimiento.</p>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm font-bold text-slate-700">Cargando propuesta de accion...</div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <Fact label="Prioridad" value={metadata.priority} />
              <Fact label="Area" value={metadata.area} />
              <Fact label="Tipo" value={metadata.decision_type} />
            </div>

            <ReadOnlyBlock label="Decision recomendada" value={draft?.sourcePriority?.recommended_decision} />
            <ReadOnlyBlock label="Base tecnica" value={draft?.sourcePriority?.technical_basis} />
            <ReadOnlyBlock label="Impacto esperado" value={formatImpact(metadata.expected_impact)} />

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Responsable">
                <input className={inputClass} value={draft.responsible} onChange={(event) => setDraft({ ...draft, responsible: event.target.value })} />
              </Field>
              <Field label="Fecha objetivo">
                <input className={inputClass} type="date" value={draft.dueDate} onChange={(event) => setDraft({ ...draft, dueDate: event.target.value })} />
              </Field>
            </div>

            <Field label="Evidencia requerida">
              <textarea className={`${inputClass} min-h-24 resize-y`} value={draft.requiredEvidence} onChange={(event) => setDraft({ ...draft, requiredEvidence: event.target.value })} />
            </Field>

            <Field label="Observaciones">
              <textarea className={`${inputClass} min-h-24 resize-y`} value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
            </Field>
          </div>
        )}

        {error ? <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-800">{error}</p> : null}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-700 hover:bg-slate-50">
            Cancelar
          </button>
          <button type="submit" disabled={loading || saving} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60">
            {saving ? <Loader2 className="animate-spin" size={17} /> : <CheckCircle2 size={17} />}
            {saving ? "Creando..." : "Crear accion ambiental"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ children, label }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-black uppercase tracking-[0.16em] text-slate-500">{label}</span>
      {children}
    </label>
  );
}

function Fact({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-black text-slate-800">{value || "Requiere datos"}</p>
    </div>
  );
}

function ReadOnlyBlock({ label, value }) {
  return (
    <div>
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-main)]">{value || "Requiere datos"}</p>
    </div>
  );
}

function formatImpact(impact = {}) {
  const parts = [
    impact.kg_co2e !== null && impact.kg_co2e !== undefined ? `${impact.kg_co2e} kgCO2e` : "",
    impact.tco2e !== null && impact.tco2e !== undefined ? `${impact.tco2e} tCO2e` : "",
    impact.pct !== null && impact.pct !== undefined ? `${impact.pct}%` : "",
    impact.risk_reduction ? `riesgo ${impact.risk_reduction}` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Requiere datos para cuantificar impacto.";
}

export default DecisionToActionModal;
