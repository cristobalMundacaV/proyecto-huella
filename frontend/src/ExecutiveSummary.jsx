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
  validationSummary,
}) {
  const recommendedDecision = optimizedScenario
    ? `Reducir diesel ${optimizedScenario.dieselReduction}%`
    : "Calcular optimizacion";
  const currentTotal = optimizedScenario?.currentTotal || 0;
  const simulatedTotal = optimizedScenario?.simulatedTotal || 0;
  const avoidedEmissions = Math.max(currentTotal - simulatedTotal, 0);
  const avoidedCarKm = avoidedEmissions * 4;
  const estimatedImpact = optimizedScenario
    ? `Reduccion proyectada del ${formatNumber(
        optimizedScenario.reductionPct,
        1
      )}% en emisiones totales bajo el escenario optimo.`
    : "Sin calcular";
  const riskFrameClass =
    riskProfile.score > 70
      ? "border-red-400/30 bg-red-400/5"
      : riskProfile.score > 30
        ? "border-yellow-400/30 bg-yellow-400/5"
        : "border-emerald-400/30 bg-emerald-400/5";

  return (
    <section className={`rounded-3xl border p-6 shadow-xl ${riskFrameClass}`}>
      <div className="mb-5 flex flex-wrap items-center gap-2 text-xs font-semibold text-emerald-300">
        <span>Dataset validado</span>
        <span className="text-emerald-400">OK</span>
        <span className="text-slate-600">|</span>
        <span>{validationSummary.records} registros</span>
        <span className="text-slate-600">|</span>
        <span>{validationSummary.errors} errores</span>
        <span className="text-slate-600">|</span>
        <span>{validationSummary.activities} actividades reconocidas</span>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-emerald-300">
            Resumen ejecutivo
          </p>
          <h2 className="mt-1 text-3xl font-bold">
            {optimizedScenario
              ? `Tu operacion puede reducir un ${formatNumber(
                  optimizedScenario.reductionPct,
                  1
                )}% sus emisiones hoy`
              : `Huella recomienda actuar sobre ${actividadCritica}`}
          </h2>
          <p className="mt-3 text-sm leading-6 text-emerald-100">
            El principal foco de impacto se concentra en {actividadCritica}, con{" "}
            {empresaCritica} como empresa critica. La decision recomendada es{" "}
            {recommendedDecision.toLowerCase()}. {estimatedImpact}
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

      {optimizedScenario && (
        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
          <BeforeAfterCard
            label="Antes"
            tone="red"
            value={`${formatNumber(currentTotal, 1)} kg CO2e`}
          />
          <BeforeAfterCard
            label="Despues"
            tone="green"
            value={`${formatNumber(simulatedTotal, 1)} kg CO2e`}
          />
          <BeforeAfterCard
            label="Impacto"
            tone="cyan"
            value={`-${formatNumber(optimizedScenario.reductionPct, 1)}%`}
          />
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-5">
        <SummaryItem label="Principal causa" value={actividadCritica} />
        <SummaryItem label="Empresa critica" value={empresaCritica} />
        <SummaryItem label="Decision recomendada" value={recommendedDecision} />
        <SummaryItem
          label="Impacto estimado"
          value={
            optimizedScenario
              ? `-${formatNumber(optimizedScenario.reductionPct, 1)}%`
              : estimatedImpact
          }
        />
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

      <p className="mt-5 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm leading-6 text-emerald-100">
        Huella recomienda priorizar intervencion en {empresaCritica} y reducir
        el uso de {actividadCritica}, lo que podria generar una mejora inmediata
        en el desempeno ambiental.
        {optimizedScenario &&
          ` Si implementas esta decision, evitarias aproximadamente ${formatNumber(
            avoidedCarKm,
            0
          )} km recorridos en auto.`}
      </p>
    </section>
  );
}

function BeforeAfterCard({ label, tone, value }) {
  const toneClass = {
    red: "border-red-400/20 bg-red-400/10 text-red-200",
    green: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
    cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200",
  }[tone];

  return (
    <div className={`rounded-2xl border p-5 ${toneClass}`}>
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
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
