import { isDieselEmission } from "@/shared/utils/emissionSemantics";

const clamp = (value, min = 0, max = 100) =>
  Math.min(max, Math.max(min, Number(value) || 0));

const SOURCE_LABEL_KEYS = [
  "fuente_emision",
  "source",
  "emissionSource",
  "nombreFuente",
  "nombre_fuente",
  "label",
];

const CATEGORY_LABEL_KEYS = ["categoria_visible", "categoria", "category", "label"];

const getEntryLabel = (item = {}, preferredKeys = SOURCE_LABEL_KEYS) => {
  for (const key of preferredKeys) {
    const value = item?.[key];

    if (String(value || "").trim()) {
      return String(value).trim();
    }
  }

  return "Sin datos";
};

const getEntryEmission = (item = {}) =>
  Number(
    item.emisiones_kg_co2e ??
      item.emisiones ??
      item.total_emisiones ??
      item.emisiones_totales ??
      item.co2e ??
      item.value ??
      item.pct ??
      0
  );

const normalizeEntries = (values = {}, preferredKeys = SOURCE_LABEL_KEYS) => {
  if (Array.isArray(values)) {
    return values.map((item) => ({
      label: getEntryLabel(item, preferredKeys),
      emissions: getEntryEmission(item),
    }));
  }

  if (!values || typeof values !== "object") {
    return [];
  }

  return Object.entries(values).map(([label, emissions]) => ({
    label: String(label || "Sin datos").trim() || "Sin datos",
    emissions: Number(emissions || 0),
  }));
};

const aggregateRows = (rows = [], preferredKeys = SOURCE_LABEL_KEYS) => {
  if (!Array.isArray(rows) || !rows.length) {
    return [];
  }

  const totals = rows.reduce((accumulator, row) => {
    const label = getEntryLabel(row, preferredKeys);

    accumulator[label] = (accumulator[label] || 0) + getEmissionValue(row);
    return accumulator;
  }, {});

  return Object.entries(totals).map(([label, emissions]) => ({
    label,
    emissions,
  }));
};

const getDominantSeries = (data = {}) => {
  const sourceSeries = normalizeEntries(data?.emisiones_por_fuente_emision, SOURCE_LABEL_KEYS).filter(
    (item) => Number(item.emissions || 0) > 0
  );

  if (sourceSeries.length) {
    return { mode: "source", series: sourceSeries };
  }

  const categorySeries = normalizeEntries(data?.categoryDistribution, CATEGORY_LABEL_KEYS).filter(
    (item) => Number(item.emissions || 0) > 0
  );

  if (categorySeries.length) {
    return { mode: "category", series: categorySeries };
  }

  const categoryRows = aggregateRows(data?.datos, CATEGORY_LABEL_KEYS).filter(
    (item) => Number(item.emissions || 0) > 0
  );

  if (categoryRows.length) {
    return { mode: "category", series: categoryRows };
  }

  const sourceRows = aggregateRows(data?.datos, SOURCE_LABEL_KEYS).filter(
    (item) => Number(item.emissions || 0) > 0
  );

  if (sourceRows.length) {
    return { mode: "source", series: sourceRows };
  }

  return { mode: "unknown", series: [] };
};

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

  const numericValues = normalizeEntries(values)
    .map((item) => Number(item.emissions || 0))
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
  const dominantSeries = getDominantSeries(data);
  const totalFromSeries = dominantSeries.series.reduce(
    (accumulator, item) => accumulator + Number(item.emissions || 0),
    0
  );
  const denominator = total > 0 ? total : totalFromSeries || 1;
  const dominantSource = dominantSeries.series.reduce((best, item) => {
    if (!best) {
      return item;
    }

    if ((Number(item.emissions) || 0) > (Number(best.emissions) || 0)) {
      return item;
    }

    return best;
  }, null);
  const sourceConcentration = dominantSource ? (Number(dominantSource.emissions || 0) / denominator) * 100 : 0;

  const stageSeries = normalizeEntries(data?.emisiones_por_etapa)
    .filter((item) => Number(item.emissions || 0) > 0)
    .length
    ? normalizeEntries(data?.emisiones_por_etapa)
    : aggregateRows(data?.datos, ["etapa_nombre", "etapa", "stage", "unidad", "label"]);

  const stageTotal = stageSeries.reduce((accumulator, item) => accumulator + Number(item.emissions || 0), 0);
  const stageConcentration = maxShare(stageSeries, stageTotal || total || 1);
  const dieselPresent =
    data?.datos?.some((row) => isDieselEmission(row) && getEmissionValue(row) > 0) ||
    normalizeEntries(data?.emisiones_por_fuente_emision || {}).some(
      ({ label: source, emissions }) =>
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
      dominantSourceLabel: dominantSource?.label || "Sin datos",
      dominantSourcePercentage: clamp(sourceConcentration, 0, 100),
      dominantSourceMode: dominantSeries.mode,
      stageConcentration,
      dieselPresent,
      potentialReduction,
    },
  };
}
