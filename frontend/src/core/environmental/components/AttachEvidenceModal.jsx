import { Loader2, X } from "lucide-react";

const inputClass = "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100";

function AttachEvidenceModal({ documentOptions = [], draft, evidenceOptions = [], error, onClose, onSave, saving, setDraft }) {
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
      <form onSubmit={onSave} className="relative max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-[28px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)]">
        <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm" aria-label="Cerrar">
          <X size={18} />
        </button>
        <div className="pr-12">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Vincular evidencia</p>
          <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">Respaldo de accion ambiental</h3>
        </div>

        <div className="mt-5 grid gap-4">
          <Field label="Evidencia de obra">
            <select className={inputClass} value={draft.evidence_id} onChange={(event) => setDraft({ ...draft, evidence_id: event.target.value })}>
              <option value="">Sin evidencia seleccionada</option>
              {evidenceOptions.map((option) => <option key={`ev-${option.value}`} value={option.value}>{option.label}</option>)}
            </select>
          </Field>
          <Field label="Documento ambiental">
            <select className={inputClass} value={draft.document_id} onChange={(event) => setDraft({ ...draft, document_id: event.target.value })}>
              <option value="">Sin documento seleccionado</option>
              {documentOptions.map((option) => <option key={`doc-${option.value}`} value={option.value}>{option.label}</option>)}
            </select>
          </Field>
          <Field label="Nota manual">
            <textarea className={`${inputClass} min-h-24 resize-y`} value={draft.note} onChange={(event) => setDraft({ ...draft, note: event.target.value })} />
          </Field>
          <Field label="Referencia o URL">
            <input className={inputClass} value={draft.reference} onChange={(event) => setDraft({ ...draft, reference: event.target.value })} />
          </Field>
        </div>

        {error ? <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">{error}</p> : null}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-700">Cancelar</button>
          <button type="submit" disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white disabled:opacity-60">
            {saving ? <Loader2 className="animate-spin" size={17} /> : null}
            Vincular evidencia
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

export default AttachEvidenceModal;
