import { isDieselEmission } from "@/shared/utils/emissionSemantics";

const clamp = (value, min = 0, max = 100) =>
  Math.min(max, Math.max(min, Number(value) || 0));

const sumValues = (values = {}) =>
  Object.values(values).reduce((total, value) => total + Number(value || 0), 0);

const maxShare = (values = {}, total) => {
  if (!total) {
    return 0;
  }

  const maxValue = Math.max(0, ...Object.values(values).map(Number));
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
  const unitConcentration = maxShare(
    data?.emisiones_por_etapa,
    sumValues(data?.emisiones_por_etapa) || total || 1
  );
  const companyConcentration = unitConcentration;
  const dieselPresent =
    data?.datos?.some((row) => isDieselEmission(row) && Number(row.emisiones || 0) > 0) ||
    Object.entries(data?.emisiones_por_fuente_emision || {}).some(
      ([source, emissions]) =>
        isDieselEmission({ fuente_emision: source }) && Number(emissions) > 0
    );
  const dieselComponent = dieselPresent ? 100 : 0;
  const totalComponent = clamp(total / 50);
  const potentialReduction = clamp(optimizedScenario?.reductionPct || 0);

  const score = clamp(
      totalComponent * 0.3 +
      sourceConcentration * 0.25 +
      unitConcentration * 0.35 +
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
      companyConcentration,
      unitConcentration,
      dieselPresent,
      potentialReduction,
    },
  };
}
