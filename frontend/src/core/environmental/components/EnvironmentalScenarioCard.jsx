function EnvironmentalScenarioCard({ scenario }) {
  const tone = {
    available: "bg-emerald-50 text-emerald-800 border-emerald-200",
    partial: "bg-amber-50 text-amber-800 border-amber-200",
    missing: "bg-slate-50 text-slate-700 border-slate-200",
  }[scenario.status] || "bg-slate-50 text-slate-700 border-slate-200";

  return (
    <article className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{scenario.area}</p>
          <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">{scenario.title}</h3>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${tone}`}>
          {scenario.status}
        </span>
      </div>

      <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">{scenario.description}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Metric label="Reduccion kgCO2e" value={formatValue(scenario.estimated_reduction_kg_co2e, "kg")} />
        <Metric label="Reduccion tCO2e" value={formatValue(scenario.estimated_reduction_tco2e, "t")} />
        <Metric label="Reduccion %" value={formatValue(scenario.estimated_reduction_pct, "%")} />
      </div>

      {!!scenario.evidence?.length && (
        <div className="mt-4">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Evidencia</p>
          <ul className="mt-2 space-y-2">
            {scenario.evidence.map((item) => (
              <li key={item} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-muted)]">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Decision sugerida</p>
        <p className="mt-1 text-sm leading-6 text-[var(--text-main)]">{scenario.decision_hint}</p>
      </div>
      <p className="mt-3 text-sm text-[var(--text-muted)]">{scenario.reason}</p>
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-3">
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-lg font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

function formatValue(value, unit) {
  if (value === null || value === undefined) return "Requiere datos";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 2 }).format(number)} ${unit}`;
}

export default EnvironmentalScenarioCard;
