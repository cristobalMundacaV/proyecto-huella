import { AlertTriangle } from "lucide-react";

function RiskSignalsPanel({ matrix }) {
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="rounded-xl border border-red-200 bg-red-50 p-2 text-red-800">
          <AlertTriangle size={18} />
        </span>
        <div>
          <h2 className="text-lg font-black text-[var(--text-main)]">Senales de riesgo</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
            Condiciones que pueden bloquear calculo, trazabilidad o cumplimiento.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3">
        {matrix.riskSignals.map((risk, index) => (
          <div key={risk} className="rounded-xl border border-red-100 bg-red-50/70 p-4">
            <p className="text-xs font-black uppercase tracking-wide text-red-700">Riesgo {index + 1}</p>
            <p className="mt-1 text-sm font-bold text-[var(--text-main)]">{risk}</p>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Accion: {matrix.recommendedActions[index % matrix.recommendedActions.length]}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RiskSignalsPanel;
