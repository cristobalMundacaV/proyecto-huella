function EnvironmentalRecommendationCard({ recommendation }) {
  const tone = {
    critica: "bg-red-50 text-red-800 border-red-200",
    alta: "bg-orange-50 text-orange-800 border-orange-200",
    media: "bg-amber-50 text-amber-800 border-amber-200",
    baja: "bg-slate-50 text-slate-700 border-slate-200",
  }[recommendation.severity] || "bg-slate-50 text-slate-700 border-slate-200";

  return (
    <article className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{recommendation.area}</p>
          <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">{recommendation.title}</h3>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${tone}`}>
          {recommendation.severity}
        </span>
      </div>

      <Section label="Diagnostico" value={recommendation.diagnosis} />
      {!!recommendation.evidence?.length && (
        <div className="mt-4">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Evidencia</p>
          <ul className="mt-2 space-y-2">
            {recommendation.evidence.map((item) => (
              <li key={item} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-muted)]">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
      <Section label="Causa probable" value={recommendation.probable_cause} />
      <Section label="Recomendacion tecnica" value={recommendation.technical_recommendation} />
      <Section label="Impacto esperado" value={recommendation.expected_impact} />
      <Section label="Decision sugerida" value={recommendation.decision_required} />

      <div className="mt-4 flex flex-wrap gap-2 text-xs font-black uppercase tracking-wide">
        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-800">
          Confianza {recommendation.confidence}
        </span>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700">
          No crea accion
        </span>
      </div>
    </article>
  );
}

function Section({ label, value }) {
  if (!value) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-main)]">{value}</p>
    </div>
  );
}

export default EnvironmentalRecommendationCard;
