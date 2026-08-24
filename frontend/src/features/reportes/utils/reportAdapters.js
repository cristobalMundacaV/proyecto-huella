const CATEGORY_ORDER = ["Materiales", "Energía", "Maquinaria", "Residuos", "Transporte", "Agua", "Otros"];

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
  const sourceRows = [...sources.values()].sort((a, b) => b.value - a.value).map((row) => ({ ...row, percentage: total > 0 ? (row.value / total) * 100 : 0 }));
  const timeline = [...months.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, value]) => ({ key, label: monthLabel(key), value }));
  const latest = timeline.at(-1) || null;
  const previous = timeline.at(-2) || null;
  const variation = latest && previous && previous.value !== 0 ? ((latest.value - previous.value) / previous.value) * 100 : null;
  const peak = timeline.reduce((best, row) => !best || row.value > best.value ? row : best, null);

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
    dominantSource: sourceRows[0] || null,
  };
}

export const REPORT_CATEGORY_COLORS = {
  Materiales: "#ea580c", Energía: "#7c3aed", Maquinaria: "#65a30d", Residuos: "#059669",
  Transporte: "#2563eb", Agua: "#0891b2", Otros: "#475569",
};
