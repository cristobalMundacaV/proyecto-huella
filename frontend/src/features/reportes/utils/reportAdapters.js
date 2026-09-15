import { getFlowChartColor } from "../../../shared/config/environmentalDomains.js";

const CATEGORY_ORDER = ["Materiales", "Energía", "Maquinaria", "Residuos", "Transporte", "Agua", "Otros"];
const CATEGORY_DOMAIN_KEYS = { Materiales: "materiales", Energía: "energia", Maquinaria: "maquinaria", Residuos: "residuos", Transporte: "transporte", Agua: "agua", Otros: "otros" };

const CATEGORY_ALIASES = {
  materiales: "Materiales", material: "Materiales", energia: "Energía", energía: "Energía",
  combustible: "Energía", combustibles: "Energía", maquinaria: "Maquinaria", residuos: "Residuos",
  residuo: "Residuos", transporte: "Transporte", agua: "Agua",
};

const normalize = (value) => String(value || "").trim().toLocaleLowerCase("es-CL").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const emissionUnit = (unit) => normalize(unit).includes("co2e");
const monthKey = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
};
const monthLabel = (key) => {
  if (!key) return "Sin periodo";
  const [year, month] = key.split("-");
  return new Intl.DateTimeFormat("es-CL", { month: "short", year: "2-digit" }).format(new Date(Number(year), Number(month) - 1, 1)).replace(" de ", " ");
};

export function buildEnvironmentalReport(impacts = [], filters = {}) {
  const valid = impacts.filter((item) => emissionUnit(item.unidad) && Number.isFinite(Number(item.valor)));
  const filtered = valid.filter((item) => {
    const time = new Date(item.timestamp || item.created_at).getTime();
    if (filters.from && time < new Date(`${filters.from}T00:00:00`).getTime()) return false;
    if (filters.to && time > new Date(`${filters.to}T23:59:59`).getTime()) return false;
    return true;
  });
  const total = filtered.reduce((sum, item) => sum + Number(item.valor), 0);
  const categories = new Map(CATEGORY_ORDER.map((name) => [name, 0]));
  const sources = new Map();
  const months = new Map();

  filtered.forEach((item) => {
    const normalizedCategory = normalize(item.categoria);
    const category = CATEGORY_ALIASES[normalizedCategory] || CATEGORY_ORDER.find((name) => normalize(name) === normalizedCategory) || "Otros";
    const value = Number(item.valor);
    categories.set(category, (categories.get(category) || 0) + value);
    const source = item.actividad_nombre || "Fuente sin nombre";
    const sourceRow = sources.get(source) || { name: source, category, value: 0 };
    sourceRow.value += value;
    sources.set(source, sourceRow);
    const key = monthKey(item.timestamp || item.created_at);
    if (key) months.set(key, (months.get(key) || 0) + value);
  });

  const categoryRows = CATEGORY_ORDER.map((name) => ({ name, value: categories.get(name) || 0, percentage: total > 0 ? ((categories.get(name) || 0) / total) * 100 : 0 }));
  const timeline = [...months.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, value]) => ({ key, label: monthLabel(key), value }));
  const latest = timeline.at(-1) || null;
  const previous = timeline.at(-2) || null;
  const variation = latest && previous && previous.value !== 0 ? ((latest.value - previous.value) / previous.value) * 100 : null;
  const peak = timeline.reduce((best, row) => !best || row.value > best.value ? row : best, null);

  // Per-source comparison: reuses the exact same filtered records, sliced by
  // the same two adjacent months `latest`/`previous` already computed above
  // — no new endpoint, no new grouping rule, just the existing month bucket
  // applied a second time per source instead of only in aggregate.
  const bySourceInMonth = (monthEntry) => {
    const map = new Map();
    if (!monthEntry) return map;
    filtered.filter((item) => monthKey(item.timestamp || item.created_at) === monthEntry.key).forEach((item) => {
      const name = item.actividad_nombre || "Fuente sin nombre";
      map.set(name, (map.get(name) || 0) + Number(item.valor));
    });
    return map;
  };
  const latestBySource = bySourceInMonth(latest);
  const previousBySource = bySourceInMonth(previous);
  const hasComparison = Boolean(latest && previous);

  const sourceRows = [...sources.values()].sort((a, b) => b.value - a.value).map((row) => {
    const percentage = total > 0 ? (row.value / total) * 100 : 0;
    if (!hasComparison) return { ...row, percentage, delta: null };
    const current = latestBySource.get(row.name) || 0;
    const before = previousBySource.get(row.name) || 0;
    return { ...row, percentage, delta: before !== 0 ? ((current - before) / before) * 100 : current > 0 ? null : 0 };
  });

  let topMover = null;
  if (hasComparison) {
    const names = new Set([...latestBySource.keys(), ...previousBySource.keys()]);
    names.forEach((name) => {
      const current = latestBySource.get(name) || 0;
      const before = previousBySource.get(name) || 0;
      const change = current - before;
      if (!topMover || Math.abs(change) > Math.abs(topMover.change)) {
        topMover = { name, current, previous: before, change, category: sources.get(name)?.category || "Otros" };
      }
    });
  }

  const dominantSource = sourceRows[0] || null;
  const comparison = {
    available: hasComparison,
    latestLabel: latest?.label || null,
    previousLabel: previous?.label || null,
    totalVariation: variation,
    topMover,
    coverage: !latest ? "none" : !previous ? "single" : "full",
  };

  return {
    total,
    records: filtered.length,
    excludedRecords: impacts.length - valid.length,
    categories: categoryRows,
    sources: sourceRows,
    timeline,
    variation,
    latest,
    previous,
    peak,
    average: timeline.length ? total / timeline.length : null,
    dominantCategory: categoryRows.filter((row) => row.value > 0).sort((a, b) => b.value - a.value)[0] || null,
    dominantSource,
    comparison,
  };
}

/** Up to 3 short, evidence-backed comparative insights — never fabricated:
 * each one only appears when the underlying comparison data supports it. */
export function buildComparativeInsights(report) {
  const insights = [];
  const { comparison } = report;

  if (comparison.available && comparison.topMover && comparison.topMover.change > 0) {
    insights.push({
      id: "principal-alza",
      priority: Math.abs(comparison.totalVariation ?? 0) > 20 ? "alta" : "media",
      title: `${comparison.topMover.name} concentra el principal aumento`,
      description: `Pasó de ${emissionText(comparison.topMover.previous)} a ${emissionText(comparison.topMover.current)} entre ${comparison.previousLabel} y ${comparison.latestLabel}.`,
    });
  }

  if (comparison.available && report.dominantSource) {
    const wasAlsoTop = comparison.topMover?.name === report.dominantSource.name;
    if (wasAlsoTop && comparison.topMover.previous > 0) {
      insights.push({
        id: "foco-persistente",
        priority: "media",
        title: `${report.dominantSource.name} se mantiene como foco principal`,
        description: `Concentra la mayor contribución en ${comparison.latestLabel} y ya lo era en ${comparison.previousLabel}.`,
      });
    }
  }

  if (report.excludedRecords > 0) {
    insights.push({
      id: "cobertura-insuficiente",
      priority: "baja",
      title: "Cobertura parcial del set analizado",
      description: `${report.excludedRecords} resultado(s) con otras unidades quedaron fuera de la comparación para no mezclar magnitudes.`,
    });
  }

  if (comparison.available && comparison.totalVariation !== null && Math.abs(comparison.totalVariation) < 5 && !insights.length) {
    insights.push({
      id: "sin-variacion",
      priority: "baja",
      title: "Sin variación relevante entre períodos",
      description: `${comparison.previousLabel} y ${comparison.latestLabel} muestran una huella prácticamente equivalente.`,
    });
  }

  return insights.slice(0, 3);
}

function emissionText(value) {
  return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(Number(value) || 0)} kg CO2e`;
}

export const REPORT_CATEGORY_COLORS = Object.fromEntries(
  CATEGORY_ORDER.map((name) => [name, getFlowChartColor(CATEGORY_DOMAIN_KEYS[name] || name)]),
);
