import { isDieselEmission } from "@/shared/utils/emissionSemantics";

const clamp = (value, min = 0, max = 100) =>
  Math.min(max, Math.max(min, Number(value) || 0));

const normalizeSeries = (values = {}) => {
  if (Array.isArray(values)) {
    return values.reduce((accumulator, item) => {
      if (!item || typeof item !== "object") {
        return accumulator;
      }

      const key = item.fuente_emision || item.source || item.etapa || item.category || item.label || "Sin datos";
      const numericValue = Number(item.emisiones_kg_co2e ?? item.emisiones ?? item.pct ?? item.value ?? 0);
      accumulator[key] = Number.isFinite(numericValue) ? numericValue : 0;
      return accumulator;
    }, {});
  }

  if (!values || typeof values !== "object") {
    return {};
  }

  return values;
};

const sumValues = (values = {}) =>
  Object.values(normalizeSeries(values)).reduce((total, value) => total + Number(value || 0), 0);

const getEmissionValue = (row = {}) =>
  Number(
    row.emisiones_kg_co2e ??
      row.emisiones ??
      row.total_emisiones ??
      row.emisiones_totales ??
      row.co2e ??
      0
  );

const maxShare = (values = {}, total) => {
  if (!total) {
    return 0;
  }

  const numericValues = Object.values(normalizeSeries(values))
    .map((value) => Number(value || 0))
    .filter((value) => Number.isFinite(value));
  const maxValue = numericValues.length ? Math.max(0, ...numericValues) : 0;
  return (maxValue / total) * 100;
};

const getLevel = (score) => {
  if (score >= 70) {
    return "Alto";
  }

  if (score >= 35) {
    return "Medio";
  }

  return "Bajo";
};

const getTone = (score) => {
  if (score >= 70) {
    return {
      color: "text-red-300",
      border: "border-red-400/20",
      background: "bg-red-400/10",
    };
  }

  if (score >= 35) {
    return {
      color: "text-yellow-300",
      border: "border-yellow-400/20",
      background: "bg-yellow-400/10",
    };
  }

  return {
    color: "text-emerald-300",
    border: "border-emerald-400/20",
    background: "bg-emerald-400/10",
  };
};

export function calculateRiskProfile(data, optimizedScenario) {
  const total = Number(data?.total_emisiones || 0);
  const totalFromSources =
    sumValues(data?.emisiones_por_fuente_emision) || total || 1;
  const sourceConcentration = maxShare(
    data?.emisiones_por_fuente_emision,
    totalFromSources
  );
  const stageConcentration = maxShare(
    data?.emisiones_por_etapa,
    sumValues(data?.emisiones_por_etapa) || total || 1
  );
  const dieselPresent =
    data?.datos?.some((row) => isDieselEmission(row) && getEmissionValue(row) > 0) ||
    Object.entries(normalizeSeries(data?.emisiones_por_fuente_emision || {})).some(
      ([source, emissions]) =>
        isDieselEmission({ fuente_emision: source }) && Number(emissions) > 0
    );
  const dieselComponent = dieselPresent ? 100 : 0;
  const totalComponent = clamp(total / 50);
  const potentialReduction = clamp(optimizedScenario?.reductionPct || 0);

  const score = clamp(
      totalComponent * 0.3 +
      sourceConcentration * 0.25 +
      stageConcentration * 0.35 +
      dieselComponent * 0.15 +
      potentialReduction * 0.1
  );

  return {
    ...getTone(score),
    score,
    label: getLevel(score),
    factors: {
      totalEmissions: {
        label: getLevel(totalComponent),
        score: totalComponent,
      },
      sourceConcentration,
      stageConcentration,
      dieselPresent,
      potentialReduction,
    },
  };
}
