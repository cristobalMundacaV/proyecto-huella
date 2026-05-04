import { isDieselActivity } from "@/shared/utils/activitySemantics";

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
  const totalFromActivities =
    sumValues(data?.emisiones_por_actividad) || total || 1;
  const activityConcentration = maxShare(
    data?.emisiones_por_actividad,
    totalFromActivities
  );
  const companyConcentration = maxShare(
    data?.emisiones_por_empresa,
    sumValues(data?.emisiones_por_empresa) || total || 1
  );
  const unitConcentration = maxShare(
    data?.emisiones_por_unidad_operativa,
    sumValues(data?.emisiones_por_unidad_operativa) || total || 1
  );
  const dieselPresent =
    data?.datos?.some((row) => isDieselActivity(row) && Number(row.emisiones || 0) > 0) ||
    Object.entries(data?.emisiones_por_actividad || {}).some(
      ([activity, emissions]) =>
        isDieselActivity({ actividad: activity }) && Number(emissions) > 0
    );
  const dieselComponent = dieselPresent ? 100 : 0;
  const totalComponent = clamp(total / 50);
  const potentialReduction = clamp(optimizedScenario?.reductionPct || 0);

  const score = clamp(
      totalComponent * 0.3 +
      activityConcentration * 0.25 +
      companyConcentration * 0.15 +
      unitConcentration * 0.2 +
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
      activityConcentration,
      companyConcentration,
      unitConcentration,
      dieselPresent,
      potentialReduction,
    },
  };
}
