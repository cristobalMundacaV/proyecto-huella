import { useState } from "react";
import { formatNumber } from "@/shared/utils/formatters";
import FactorSuggestionPanel from "./FactorSuggestionPanel";

function FactorApplyModal({ factors, onApply, onClose, record, suggestion }) {
  const [factorId, setFactorId] = useState(suggestion?.factor?.id || "");
  const selected = factors.find((factor) => String(factor.id) === String(factorId));
  const estimated = selected ? Number(record.cantidad || 0) * Number(selected.factor_emision || 0) : 0;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl">
        <h2 className="text-2xl font-black text-[var(--text-main)]">Aplicar factor</h2>
        <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm">
          <p><strong>Registro:</strong> {record.fuente_emision}</p>
          <p><strong>Cantidad:</strong> {formatNumber(record.cantidad, 2)} {record.unidad}</p>
        </div>
        <div className="mt-4"><FactorSuggestionPanel suggestion={suggestion} /></div>
        <select className="mt-4 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3" value={factorId} onChange={(e) => setFactorId(e.target.value)}>
          <option value="">Seleccionar factor alternativo</option>
          {factors.map((factor) => <option key={factor.id} value={factor.id}>{factor.actividad} | {factor.unidad} | {factor.factor_emision}</option>)}
        </select>
        <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800">Impacto estimado: {formatNumber(estimated, 3)} kg CO2e</p>
        <div className="mt-5 flex justify-end gap-3"><button onClick={onClose} className="rounded-xl border px-4 py-3 font-bold">Cancelar</button><button disabled={!selected} onClick={() => onApply(selected)} className="rounded-xl bg-[var(--primary)] px-4 py-3 font-black text-white disabled:opacity-50">Aplicar factor</button></div>
      </div>
    </div>
  );
}

export default FactorApplyModal;
