const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value));

const formatTitleCase = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .trim()
    .split(/\s+/)
    .map((word) =>
      word ? `${word.charAt(0).toUpperCase()}${word.slice(1).toLowerCase()}` : ""
    )
    .join(" ");

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const normalizePlanText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

const formatFocusForSentence = (value) => {
  const normalizedValue = normalizePlanText(value);

  if (
    normalizedValue.includes("diesel") &&
    normalizedValue.includes("combustion") &&
    normalizedValue.includes("movil")
  ) {
    return "la combustión móvil de diésel";
  }

  return value;
};

const formatViabilityForSentence = (value) =>
  String(value || "").trim().toLowerCase();

const capRangeToPotential = (range, potentialReduction) => {
  if (!potentialReduction || potentialReduction <= 0) {
    return range;
  }

  const cappedMax = Math.max(1, Math.min(range.max, potentialReduction));
  const cappedMin = Math.min(range.min, cappedMax);

  return {
    min: Math.round(cappedMin),
    max: Math.round(cappedMax),
  };
};

const formatPercentRange = ({ min, max }) =>
  min === max ? `${min}%` : `${min}%-${max}%`;

const buildStrategicPlan = (actividadCritica, optimizedScenario) => {
  const activityLabel = actividadCritica || "la actividad prioritaria";
  const activityKey = normalizePlanText(activityLabel);
  const potentialReduction = Number(optimizedScenario?.reductionPct || 0);
  const optimalActivityReduction =
    activityKey === "diesel"
      ? Number(optimizedScenario?.dieselReduction || 0)
      : Number(optimizedScenario?.activityReduction || 0);

  let viability = "Alta";
  if (activityKey === "diesel" || potentialReduction > 40) {
    viability = "Media";
  }
  if (potentialReduction > 50 || optimalActivityReduction >= 70) {
    viability = "Baja";
  }

  const baseRecommendedRange =
    viability === "Baja"
      ? { min: 10, max: 20 }
      : { min: 20, max: 25 };
  const recommendedRange = capRangeToPotential(
    baseRecommendedRange,
    potentialReduction
  );

  const initialTarget = clamp(
    Math.round(potentialReduction > 0 ? potentialReduction * 0.4 : 20),
    recommendedRange.min,
    recommendedRange.max
  );

  const principalRecommendation = `Apuntar a reducir gradualmente el consumo de ${activityLabel} entre un ${formatPercentRange(recommendedRange)}, iniciando con un objetivo priorizado cercano al ${initialTarget}%.`;

  const optimalReference = potentialReduction > 0
    ? `El escenario máximo proyectado contempla una reducción total de hasta un ${formatNumber(
        potentialReduction,
        1
      )}%; sin embargo, no corresponde a una acción inmediata, ya que requeriría cambios estructurales para su implementación.`
    : "El máximo potencial proyectado debe tratarse como referencia estratégica de largo plazo, no como acción inmediata.";

  const actionLevels = [
    {
      label: "Acciones rápidas",
      range: "5%-15%",
      tone: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
      detail:
        "Control del consumo, mantenimiento preventivo y mejora de la operación diaria. Ideal para lograr avances visibles sin cambiar la estructura del negocio.",
    },
    {
      label: "Piloto recomendado",
      range: formatPercentRange(recommendedRange),
      tone: "border-yellow-400/20 bg-yellow-400/10 text-yellow-200",
      detail:
        "Ajustes operativos, rediseño parcial de procesos y seguimiento mediante indicadores. Es el mejor punto de partida para lograr una reducción realista y medible.",
    },
    {
      label: "Cambio estructural",
      range:
        potentialReduction > 0
          ? `${formatNumber(potentialReduction, 1)}% proyectado`
          : "35%+",
      tone: "border-rose-400/20 bg-rose-400/10 text-rose-200",
      detail:
        "Requiere inversión, planificación a mediano y largo plazo, y transición tecnológica. Es útil como visión futura, pero no como primera acción inmediata.",
    },
  ];

  return {
    viability,
    recommendedRange,
    initialTarget,
    principalRecommendation,
    optimalReference,
    actionLevels,
  };
};

function ExecutiveSummary({
  actividadCritica,
  unidadCritica,
  optimizedScenario,
  reductionEquivalentKm,
  riskProfile,
  validationSummary,
}) {
  const unidadCriticaLabel = unidadCritica || "Sin datos";
  const strategicPlan = buildStrategicPlan(actividadCritica, optimizedScenario);
  const recommendedDecision = optimizedScenario
    ? strategicPlan.principalRecommendation
    : "Definir un plan progresivo con metas por fases";
  const currentTotal = optimizedScenario?.currentTotal || 0;
  const simulatedTotal = optimizedScenario?.simulatedTotal || 0;
  const avoidedEmissions = Math.max(currentTotal - simulatedTotal, 0);
  const equivalentCarKm =
    reductionEquivalentKm != null ? reductionEquivalentKm : avoidedEmissions * 4;
  const mediumImpactReductionPct =
    (strategicPlan.recommendedRange.min + strategicPlan.recommendedRange.max) / 2;
  const mediumImpactEstimatedTotal = Math.max(
    currentTotal * (1 - mediumImpactReductionPct / 100),
    0
  );
  const estimatedImpact = optimizedScenario
    ? `con un potencial proyectado de reducción del ${formatNumber(
        optimizedScenario.reductionPct,
        1
      )}% en las emisiones totales bajo el escenario máximo.`
    : "Sin calcular";
  const riskFrameClass =
    riskProfile.score > 70
      ? "border-red-400/30 bg-red-400/5"
      : riskProfile.score > 30
        ? "border-yellow-400/30 bg-yellow-400/5"
        : "border-emerald-400/30 bg-emerald-400/5";

  return (
    <section className={`rounded-3xl border p-4 sm:p-6 shadow-xl ${riskFrameClass}`}>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-lg font-semibold text-emerald-300">
          Resumen ejecutivo
        </p>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold">
            {optimizedScenario
              ? `Potencial de reduccion del ${formatNumber(
                  optimizedScenario.reductionPct,
                  1
                )}% con una reduccion progresiva en ${formatTitleCase(
                  actividadCritica
                )}`
              : `Carbono Zero recomienda un plan gradual sobre ${actividadCritica}`}
          </h2>
          <p className="mt-3 text-sm leading-6 text-emerald-100">
            El principal foco de impacto se concentra en{" "}
            {formatFocusForSentence(actividadCritica)}, siendo {unidadCriticaLabel}{" "}
            la unidad prioritaria. El nivel de viabilidad es{" "}
            <strong>{formatViabilityForSentence(strategicPlan.viability)}</strong>,{" "}
            {optimizedScenario ? estimatedImpact : "sin calcular."}
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
            Score Carbono Zero: {formatNumber(riskProfile.score, 0)} / 100
          </p>
        </div>
      </div>

      {optimizedScenario && (
        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
          <BeforeAfterCard
            label="Emisiones actuales"
            tone="red"
            value={`${formatNumber(currentTotal, 1)} kg CO2e`}
          />
          <BeforeAfterCard
            label="Escenario recomendado"
            tone="cyan"
            value={`${formatNumber(mediumImpactEstimatedTotal, 1)} kg CO2e`}
          />
          <BeforeAfterCard
            label="Máximo potencial proyectado"
            tone="green"
            value={`${formatNumber(simulatedTotal, 1)} kg CO2e`}
          />
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <SummaryItem label="Foco principal" value={actividadCritica} />
        <SummaryItem label="Unidad prioritaria" value={unidadCriticaLabel} />
        <SummaryItem
          label="Escenario recomendado"
          value={formatPercentRange(strategicPlan.recommendedRange)}
        />

        <SummaryItem
          label="Uso de diésel"
          value={riskProfile.factors.dieselPresent ? "Si" : "No"}
        />

        <SummaryItem
          label="Reducción estimada"
          value={
            optimizedScenario
              ? `${formatNumber(optimizedScenario.reductionPct, 1)}%`
              : estimatedImpact
          }
        />
        <SummaryItem label="Viabilidad operativa" value={strategicPlan.viability} />
      </div>

      <div className="mt-5 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan-200">
          Recomendación principal
        </p>
        <p className="mt-2 text-sm leading-6 text-cyan-100">{recommendedDecision}</p>
        <p className="mt-2 text-sm leading-6 text-cyan-200">
          {strategicPlan.optimalReference}
        </p>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {strategicPlan.actionLevels.map((level) => (
          <div key={level.label} className={`rounded-2xl border p-4 ${level.tone}`}>
            <div className="text-center">
              <p className="text-xs font-semibold uppercase tracking-wide">{level.label}</p>
              <p className="mt-1 text-2xl font-extrabold">{level.range}</p>
            </div>
            <p className="mt-2 text-sm leading-6">{level.detail}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Factores del score
        </p>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <ScoreFactor
            label="Emisiones totales"
            value={riskProfile.factors.totalEmissions.label}
          />
          <ScoreFactor
            label="Concentracion actividad"
            value={`${formatNumber(riskProfile.factors.activityConcentration, 0)}%`}
          />
          <ScoreFactor
            label="Concentracion unidad"
            value={`${formatNumber(riskProfile.factors.companyConcentration, 0)}%`}
          />
          <ScoreFactor
            label="Diesel presente"
            value={riskProfile.factors.dieselPresent ? "Si" : "No"}
          />
          <ScoreFactor
            label="Potencial reduccion"
            value={`${formatNumber(riskProfile.factors.potentialReduction, 1)}%`}
          />
        </div>
      </div>

      <p className="mt-5 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm leading-6 text-emerald-100">
        Carbono Zero recomienda priorizar una intervencion progresiva en {unidadCriticaLabel} sobre {actividadCritica}, empezando con quick wins y escalando por fases
        segun resultados medidos.
        {(optimizedScenario || reductionEquivalentKm != null) &&
          ` Si la hoja de ruta se consolida por etapas, la reducción operativa estimada equivale a aproximadamente ${formatNumber(
            equivalentCarKm,
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
      <p className="text-xs text-slate-400">{formatTitleCase(label)}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {formatTitleCase(label)}
      </p>
      <p className="mt-1 text-sm font-extrabold leading-snug text-slate-100">{value}</p>
    </div>
  );
}

function ScoreFactor({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-sm font-extrabold text-slate-100">{value}</p>
    </div>
  );
}

export default ExecutiveSummary;
