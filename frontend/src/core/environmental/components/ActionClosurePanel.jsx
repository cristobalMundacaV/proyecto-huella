import { useEffect, useState } from "react";
import { CheckCircle2, FileCheck2, Loader2, Paperclip } from "lucide-react";

import { attachEvidenceToAction, closeEnvironmentalAction, getActionClosureStatus } from "@/features/environmental/services/environmentalActionClosureApi";
import AttachEvidenceModal from "./AttachEvidenceModal";
import CloseActionModal from "./CloseActionModal";

function ActionClosurePanel({ action, documentOptions = [], evidenceOptions = [], onUpdated }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [attachDraft, setAttachDraft] = useState(null);
  const [closeDraft, setCloseDraft] = useState(null);

  async function loadStatus() {
    if (!action?.id) return;
    try {
      setLoading(true);
      setError("");
      setStatus(await getActionClosureStatus(action.id));
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo cargar el cierre.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action?.id, action?.updatedAt, action?.status]);

  async function saveEvidence(event) {
    event.preventDefault();
    try {
      setSaving(true);
      setError("");
      const result = await attachEvidenceToAction(action.id, attachDraft);
      setStatus(result.closure_status);
      setAttachDraft(null);
      onUpdated?.(result.action);
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo vincular evidencia.");
    } finally {
      setSaving(false);
    }
  }

  async function saveClosure(event) {
    event.preventDefault();
    try {
      setSaving(true);
      setError("");
      const result = await closeEnvironmentalAction(action.id, closeDraft);
      setStatus(result.closure_status);
      setCloseDraft(null);
      onUpdated?.(result.action);
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo cerrar la accion.");
    } finally {
      setSaving(false);
    }
  }

  const canClose = status?.closure_readiness?.can_close;
  const missing = status?.closure_readiness?.missing_items || [];
  const linkedEvidence = status?.linked_evidence || [];
  const linkedDocuments = status?.linked_documents || [];

  return (
    <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-wide text-emerald-800">
          {loading ? <Loader2 className="animate-spin" size={14} /> : <FileCheck2 size={14} />}
          Cierre ambiental
        </p>
        <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-black text-emerald-800">
          {status?.status || "pendiente"}
        </span>
      </div>

      <p className="mt-2 text-xs leading-5 text-emerald-900">
        <strong>Evidencia requerida:</strong> {status?.required_evidence || action.evidence || "Evidencia ambiental trazable"}
      </p>

      <div className="mt-3 space-y-2">
        {[...linkedEvidence, ...linkedDocuments].map((item) => (
          <p key={`${item.type}-${item.id}`} className="rounded-xl border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-emerald-900">
            {item.type}: {item.label}
          </p>
        ))}
        {!linkedEvidence.length && !linkedDocuments.length ? (
          <p className="rounded-xl border border-dashed border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900">Sin evidencia/documento vinculado.</p>
        ) : null}
      </div>

      {missing.length ? (
        <ul className="mt-3 list-disc pl-5 text-xs font-semibold text-amber-900">
          {missing.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : null}
      {error ? <p className="mt-3 text-xs font-bold text-rose-700">{error}</p> : null}

      <div className="mt-3 grid gap-2">
        <button type="button" onClick={() => setAttachDraft({ evidence_id: "", document_id: "", note: "", reference: "" })} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-3 py-2 text-xs font-black text-emerald-800">
          <Paperclip size={14} /> Vincular evidencia
        </button>
        <button
          type="button"
          onClick={() => setCloseDraft({ closure_result: "", impact_observed: "", evidence_summary: "", close_with_warning: false })}
          disabled={!canClose && action.status !== "completada"}
          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-700 px-3 py-2 text-xs font-black text-white disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <CheckCircle2 size={14} /> Cerrar accion
        </button>
      </div>

      {attachDraft ? (
        <AttachEvidenceModal
          documentOptions={documentOptions}
          draft={attachDraft}
          evidenceOptions={evidenceOptions}
          error={error}
          onClose={() => setAttachDraft(null)}
          onSave={saveEvidence}
          saving={saving}
          setDraft={setAttachDraft}
        />
      ) : null}
      {closeDraft ? (
        <CloseActionModal
          draft={closeDraft}
          error={error}
          onClose={() => setCloseDraft(null)}
          onSave={saveClosure}
          saving={saving}
          setDraft={setCloseDraft}
          status={status}
        />
      ) : null}
    </div>
  );
}

export default ActionClosurePanel;
