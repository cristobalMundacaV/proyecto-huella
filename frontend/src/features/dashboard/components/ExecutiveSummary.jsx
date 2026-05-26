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

const isValidExecutiveLabel = (value) => {
  const text = String(value ?? "").trim();
  const normalized = text.toLowerCase();

  return Boolean(
    text &&
      text !== "0" &&
      normalized !== "null" &&
      normalized !== "undefined" &&
      normalized !== "nan"
  );
};

const getExecutiveLabel = (value, fallback) =>
  isValidExecutiveLabel(value) ? String(value).trim() : fallback;

const hasValidScenario = (scenario) =>
  Boolean(
    scenario &&
      Number(scenario.currentTotal) > 0 &&
      Number(scenario.simulatedTotal) > 0 &&
      Number(scenario.reductionPct) > 0
  );

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

const buildStrategicPlan = (fuenteCritica, optimizedScenario) => {
  const activityLabel = fuenteCritica || "la fuente prioritaria";
  const sourceKey = normalizePlanText(activityLabel);
  const potentialReduction = Number(optimizedScenario?.reductionPct || 0);
  const optimalActivityReduction =
    sourceKey === "diesel"
      ? Number(optimizedScenario?.dieselReduction || 0)
      : Number(optimizedScenario?.activityReduction || 0);

  let viability = "Alta";
  if (sourceKey === "diesel" || potentialReduction > 40) {
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
      )}%; sin embargo, no corresponde a una acción inmediata, ya que requerirí­a cambios estructurales para su implementación.`
    : "El máximo potencial proyectado debe tratarse como referencia estratégica de largo plazo, no como acción inmediata.";

  const actionLevels = [
    {
      label: "Acciones rápidas",
      range: "5%-15%",
      tone: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--secondary)]",
      detail:
        "Control del consumo, mantenimiento preventivo y mejora de la operación diaria. Ideal para lograr avances visibles sin cambiar la estructura del negocio.",
    },
    {
      label: "Piloto recomendado",
      range: formatPercentRange(recommendedRange),
      tone: "border-[#F6D98B] bg-[var(--warning-bg)] text-[#8A5A00]",
      detail:
        "Ajustes operativos, rediseño parcial de procesos y seguimiento mediante indicadores. Es el mejor punto de partida para lograr una reducción realista y medible.",
    },
    {
      label: "Cambio estructural",
      range:
        potentialReduction > 0
          ? `${formatNumber(potentialReduction, 1)}% proyectado`
          : "35%+",
      tone: "border-[#F1C7C7] bg-[var(--danger-bg)] text-[#9A3412]",
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
  fuenteCritica,
  unidadCritica,
  optimizedScenario,
  reductionEquivalentKm,
  riskProfile,
}) {
  const fuenteCriticaLabel = getExecutiveLabel(
    fuenteCritica,
    "Fuente crítica sin datos suficientes"
  );
  const unidadCriticaLabel = getExecutiveLabel(
    unidadCritica,
    "Sin etapa suficiente"
  );
  const hasValidOptimizedScenario = hasValidScenario(optimizedScenario);
  const scenarioForPlan = hasValidOptimizedScenario ? optimizedScenario : null;
  const strategicPlan = buildStrategicPlan(fuenteCriticaLabel, scenarioForPlan);
  const recommendedDecision = hasValidOptimizedScenario
    ? strategicPlan.principalRecommendation
    : "Completar registros, asociar etapas y validar factores de emisión antes de definir un porcentaje de reducción. Luego priorizar la fuente crítica detectada con acciones progresivas y medibles.";
  const currentTotal = Number(optimizedScenario?.currentTotal || 0);
  const simulatedTotal = hasValidOptimizedScenario
    ? Number(optimizedScenario?.simulatedTotal || 0)
    : 0;
  const avoidedEmissions = Math.max(currentTotal - simulatedTotal, 0);
  const equivalentCarKm =
    reductionEquivalentKm != null ? reductionEquivalentKm : avoidedEmissions * 4;
  const mediumImpactReductionPct =
    (strategicPlan.recommendedRange.min + strategicPlan.recommendedRange.max) / 2;
  const mediumImpactEstimatedTotal = Math.max(
    currentTotal * (1 - mediumImpactReductionPct / 100),
    0
  );
  const estimatedImpact = hasValidOptimizedScenario
    ? `con un potencial proyectado de reducción del ${formatNumber(
        optimizedScenario.reductionPct,
        1
      )}% en las emisiones totales bajo el escenario máximo.`
    : "Aún no existe un escenario de reducción calculado con datos suficientes.";
  const riskTone =
    riskProfile.score > 70
      ? "border-[var(--kpi-danger-border)] bg-[var(--kpi-danger-bg)] text-[var(--kpi-danger-text)]"
      : riskProfile.score > 30
        ? "border-[var(--kpi-warning-border)] bg-[var(--kpi-warning-bg)] text-[var(--kpi-warning-text)]"
        : "border-[var(--kpi-success-border)] bg-[var(--kpi-success-bg)] text-[var(--kpi-success-text)]";

  return (
    <section className="group premium-card premium-card-interactive slide-up rounded-2xl border-emerald-200/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(236,253,243,0.92))] p-4 shadow-[var(--shadow-soft)] transition duration-300 hover:-translate-y-1 hover:border-emerald-200/90 hover:shadow-[0_24px_64px_rgba(15,23,42,0.12)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="inline-flex w-fit items-center gap-2 rounded-full border border-emerald-200/70 bg-emerald-50 px-3 py-1 text-sm font-bold text-[var(--primary-dark)] shadow-[0_8px_18px_rgba(14,124,102,0.08)] transition group-hover:border-emerald-300/80 group-hover:bg-emerald-100 group-hover:shadow-[0_12px_24px_rgba(14,124,102,0.14)]">
          <span className="h-2 w-2 rounded-full bg-[var(--primary)]" />
          Resumen ejecutivo
        </p>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-[2.05rem]">
            {hasValidOptimizedScenario
              ? `Potencial de reduccion del ${formatNumber(
                  optimizedScenario.reductionPct,
                  1
                )}% con una reduccion progresiva en ${formatTitleCase(
                  fuenteCriticaLabel
                )}`
              : `Priorizar intervención sobre ${fuenteCriticaLabel}`}
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
            El principal foco de impacto se concentra en{" "}
            {formatFocusForSentence(fuenteCriticaLabel)}, siendo {unidadCriticaLabel}{" "}
            la etapa prioritaria. El nivel de viabilidad es{" "}
            <strong>{formatViabilityForSentence(strategicPlan.viability)}</strong>,{" "}
            {optimizedScenario ? estimatedImpact : "sin calcular."}
          </p>
        </div>

        <div className={`premium-card-interactive min-w-48 rounded-2xl border p-5 shadow-[var(--shadow-card)] transition group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_40px_rgba(15,23,42,0.12)] ${riskTone}`}>
          <p className="text-sm text-[var(--text-muted)]">Riesgo</p>
          <p className="mt-1 text-4xl font-black tracking-tight">
            {riskProfile.label}
          </p>
          <p className="mt-2 text-sm font-semibold">
            Score Carbono Zero: {formatNumber(riskProfile.score, 0)} / 100
          </p>
        </div>
      </div>

      {hasValidOptimizedScenario && (
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
        <SummaryItem label="Foco principal" value={fuenteCriticaLabel} tone="warning" />
        <SummaryItem label="Etapa prioritaria" value={unidadCriticaLabel} tone="info" />
        <SummaryItem label="Esc. recomendado" value={formatPercentRange(strategicPlan.recommendedRange)} tone="info" />

        <SummaryItem
          label="Uso de diésel"
          value={riskProfile.factors.dieselPresent ? "Si" : "No"}
          tone={riskProfile.factors.dieselPresent ? "warning" : "neutral"}
        />

        <SummaryItem
          label="Reducción estimada"
          value={
            hasValidOptimizedScenario
              ? `${formatNumber(optimizedScenario.reductionPct, 1)}%`
              : "Pendiente"
          }
          tone="success"
        />
        <SummaryItem
          label="Viabilidad operativa"
          value={strategicPlan.viability}
          tone={strategicPlan.viability === "Alta" ? "success" : strategicPlan.viability === "Media" ? "warning" : "danger"}
        />
      </div>

      <div className="premium-card-interactive mt-5 rounded-2xl border border-cyan-100 bg-[linear-gradient(180deg,rgba(236,253,255,1),rgba(239,246,255,0.92))] p-4 transition group-hover:border-cyan-200 group-hover:shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--primary-dark)]">
          Recomendación principal
        </p>
        <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">{recommendedDecision}</p>
        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          {strategicPlan.optimalReference}
        </p>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {strategicPlan.actionLevels.map((level) => (
          <div key={level.label} className={`premium-card-interactive rounded-2xl border p-4 ${level.tone}`}>
            <div className="text-center">
              <p className="text-xs font-semibold uppercase tracking-wide">{level.label}</p>
              <p className="mt-1 text-2xl font-extrabold">{level.range}</p>
            </div>
            <p className="mt-2 text-sm leading-6">{level.detail}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[linear-gradient(180deg,rgba(255,255,255,1),rgba(248,250,252,0.96))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.06)] transition group-hover:border-[var(--primary)]/20 group-hover:shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--secondary)]">
          Factores del score
        </p>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <ScoreFactor
            label="Emisiones totales"
            value={riskProfile.factors.totalEmissions.label}
            tone="danger"
          />
          <ScoreFactor
            label="Concentracion fuente"
            value={`${formatNumber(riskProfile.factors.sourceConcentration, 0)}%`}
            tone="warning"
          />
          <ScoreFactor
            label="Concentracion etapa"
            value={`${formatNumber(riskProfile.factors.stageConcentration, 0)}%`}
            tone="info"
          />
          <ScoreFactor
            label="Diesel presente"
            value={riskProfile.factors.dieselPresent ? "Si" : "No"}
            tone={riskProfile.factors.dieselPresent ? "warning" : "neutral"}
          />
          <ScoreFactor
            label="Potencial reduccion"
            value={
              hasValidOptimizedScenario
                ? `${formatNumber(riskProfile.factors.potentialReduction, 1)}%`
                : "Pendiente"
            }
            tone="success"
          />
        </div>
      </div>

      <p className="mt-5 rounded-2xl border border-emerald-200/70 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(220,252,231,0.92))] px-4 py-3 text-sm leading-6 text-[var(--secondary)] shadow-[0_10px_22px_rgba(15,23,42,0.05)] transition group-hover:border-emerald-300/70 group-hover:shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
        Carbono Zero recomienda priorizar una intervencion progresiva en {unidadCriticaLabel} sobre {fuenteCritica}, empezando con quick wins y escalando por fases
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
    red: "border-[var(--kpi-danger-border)] bg-[var(--kpi-danger-bg)] text-[var(--kpi-danger-text)]",
    green: "border-[var(--kpi-success-border)] bg-[var(--kpi-success-bg)] text-[var(--kpi-success-text)]",
    cyan: "border-[var(--kpi-info-border)] bg-[var(--kpi-info-bg)] text-[var(--kpi-info-text)]",
  }[tone];

  return (
    <div className={`premium-card-interactive rounded-2xl border p-5 text-center shadow-[0_12px_24px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_30px_rgba(15,23,42,0.08)] ${toneClass}`}>
      <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{formatTitleCase(label)}</p>
      <p className="mt-1 text-2xl font-black tracking-tight">{value}</p>
    </div>
  );
}

function SummaryItem({ label, value, tone = "neutral" }) {
  const toneClass = {
    neutral: "border-[var(--kpi-neutral-border)] bg-[var(--kpi-neutral-bg)] text-[var(--kpi-dark-text)]",
    warning: "border-[var(--kpi-warning-border)] bg-[var(--kpi-warning-bg)] text-[var(--kpi-warning-text)]",
    info: "border-[var(--kpi-info-border)] bg-[var(--kpi-info-bg)] text-[var(--kpi-info-text)]",
    success: "border-[var(--kpi-success-border)] bg-[var(--kpi-success-bg)] text-[var(--kpi-success-text)]",
    danger: "border-[var(--kpi-danger-border)] bg-[var(--kpi-danger-bg)] text-[var(--kpi-danger-text)]",
  }[tone];

  return (
    <div className={`premium-card-interactive flex min-h-[6rem] flex-col items-center justify-center rounded-xl border px-4 py-3 text-center shadow-[0_10px_20px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_28px_rgba(15,23,42,0.08)] ${toneClass}`}>
      <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
        {formatTitleCase(label)}
      </p>
      <p className="mt-2 text-sm font-extrabold leading-snug text-current">{value}</p>
    </div>
  );
}

function ScoreFactor({ label, value, tone = "neutral" }) {
  const toneDot = {
    neutral: "bg-[var(--kpi-neutral-text)]",
    warning: "bg-[var(--kpi-warning-text)]",
    info: "bg-[var(--kpi-info-text)]",
    success: "bg-[var(--kpi-success-text)]",
    danger: "bg-[var(--kpi-danger-text)]",
  }[tone];

  return (
    <div className="premium-card-interactive rounded-xl border border-[var(--border)] bg-[linear-gradient(180deg,rgba(255,255,255,1),rgba(248,250,252,0.95))] px-4 py-3 text-center shadow-[0_10px_20px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:border-[var(--primary)]/20 hover:shadow-[0_14px_28px_rgba(15,23,42,0.08)]">
      <div className="flex items-center justify-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${toneDot}`} />
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      </div>
      <p className="mt-1 text-sm font-extrabold text-current">{value}</p>
    </div>
  );
}

export default ExecutiveSummary;
