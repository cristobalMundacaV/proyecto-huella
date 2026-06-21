import { CheckCircle2 } from "lucide-react";

function RecommendedActionsPanel({ matrix }) {
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="rounded-xl border border-emerald-200 bg-emerald-50 p-2 text-emerald-800">
          <CheckCircle2 size={18} />
        </span>
        <div>
          <h2 className="text-lg font-black text-[var(--text-main)]">Acciones recomendadas</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
            Siguientes pasos para convertir datos en evidencia y control operacional.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3">
        {matrix.recommendedActions.map((action) => (
          <div key={action} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">{action}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RecommendedActionsPanel;
