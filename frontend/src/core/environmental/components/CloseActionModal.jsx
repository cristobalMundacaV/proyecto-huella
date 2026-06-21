import { Loader2, X } from "lucide-react";

const inputClass = "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100";

function CloseActionModal({ draft, error, onClose, onSave, saving, setDraft, status }) {
  const missing = status?.closure_readiness?.missing_items || [];

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
      <form onSubmit={onSave} className="relative max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-[28px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)]">
        <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm" aria-label="Cerrar">
          <X size={18} />
        </button>
        <div className="pr-12">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Cerrar accion ambiental</p>
          <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">{status?.title || "Resultado de cierre"}</h3>
        </div>

        {missing.length ? (
          <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-black text-amber-900">Faltan elementos para cierre sin advertencia</p>
            <ul className="mt-2 list-disc pl-5 text-sm text-amber-900">
              {missing.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        ) : null}

        <div className="mt-5 grid gap-4">
          <Field label="Resultado de cierre">
            <textarea className={`${inputClass} min-h-24 resize-y`} value={draft.closure_result} onChange={(event) => setDraft({ ...draft, closure_result: event.target.value })} />
          </Field>
          <Field label="Impacto observado">
            <textarea className={`${inputClass} min-h-20 resize-y`} value={draft.impact_observed} onChange={(event) => setDraft({ ...draft, impact_observed: event.target.value })} />
          </Field>
          <Field label="Resumen de evidencia usada">
            <textarea className={`${inputClass} min-h-20 resize-y`} value={draft.evidence_summary} onChange={(event) => setDraft({ ...draft, evidence_summary: event.target.value })} />
          </Field>
          <label className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-bold text-amber-900">
            <input type="checkbox" checked={draft.close_with_warning} onChange={(event) => setDraft({ ...draft, close_with_warning: event.target.checked })} className="mt-1" />
            Cerrar con advertencia y registrar justificacion aunque falte evidencia vinculada.
          </label>
        </div>

        {error ? <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">{error}</p> : null}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-700">Cancelar</button>
          <button type="submit" disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white disabled:opacity-60">
            {saving ? <Loader2 className="animate-spin" size={17} /> : null}
            Cerrar accion
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

export default CloseActionModal;
