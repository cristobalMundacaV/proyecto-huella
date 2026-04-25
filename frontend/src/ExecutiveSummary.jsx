const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value));

function ExecutiveSummary({
  actividadCritica,
  empresaCritica,
  optimizedScenario,
  riskProfile,
}) {
  const recommendedDecision = optimizedScenario
    ? `Reducir diesel ${optimizedScenario.dieselReduction}%`
    : "Calcular optimizacion";
  const estimatedImpact = optimizedScenario
    ? `-${formatNumber(optimizedScenario.reductionPct, 1)}%`
    : "Sin calcular";

  return (
    <section className="rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-6 shadow-xl">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-emerald-300">
            Resumen ejecutivo
          </p>
          <h2 className="mt-1 text-3xl font-bold">
            Huella recomienda actuar sobre {actividadCritica}
          </h2>
          <p className="mt-3 text-sm leading-6 text-emerald-100">
            El principal foco de impacto se concentra en {actividadCritica}, con{" "}
            {empresaCritica} como empresa critica. La decision recomendada es{" "}
            {recommendedDecision.toLowerCase()} para capturar un impacto
            estimado de {estimatedImpact}.
          </p>
        </div>

        <div
          className={`min-w-48 rounded-2xl border p-5 ${riskProfile.background} ${riskProfile.border}`}
        >
          <p className="text-sm text-slate-400">Riesgo</p>
          <p className={`mt-1 text-4xl font-bold ${riskProfile.color}`}>
            {riskProfile.label}
          </p>
          <p className={`mt-2 text-sm font-semibold ${riskProfile.color}`}>
            Score Huella: {formatNumber(riskProfile.score, 0)} / 100
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-5">
        <SummaryItem label="Principal causa" value={actividadCritica} />
        <SummaryItem label="Empresa critica" value={empresaCritica} />
        <SummaryItem label="Decision recomendada" value={recommendedDecision} />
        <SummaryItem label="Impacto estimado" value={estimatedImpact} />
        <SummaryItem
          label="Diesel presente"
          value={riskProfile.factors.dieselPresent ? "Si" : "No"}
        />
      </div>

      <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Factores del score
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 text-sm text-slate-300 md:grid-cols-5">
          <span>
            Emisiones totales:{" "}
            <strong>{riskProfile.factors.totalEmissions.label}</strong>
          </span>
          <span>
            Concentracion actividad:{" "}
            <strong>
              {formatNumber(riskProfile.factors.activityConcentration, 0)}%
            </strong>
          </span>
          <span>
            Concentracion empresa:{" "}
            <strong>
              {formatNumber(riskProfile.factors.companyConcentration, 0)}%
            </strong>
          </span>
          <span>
            Diesel presente:{" "}
            <strong>{riskProfile.factors.dieselPresent ? "Si" : "No"}</strong>
          </span>
          <span>
            Potencial reduccion:{" "}
            <strong>
              {formatNumber(riskProfile.factors.potentialReduction, 1)}%
            </strong>
          </span>
        </div>
      </div>
    </section>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-slate-100">{value}</p>
    </div>
  );
}

export default ExecutiveSummary;
